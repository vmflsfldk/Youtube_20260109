"""ASR transcription helper."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile



@dataclass(frozen=True)
class Transcript:
    start_sec: float
    end_sec: float
    text: str


logger = logging.getLogger(__name__)


def transcribe_segment(audio_path: str | Path, start_sec: float, end_sec: float) -> Transcript:
    path = Path(audio_path)
    if not path.exists() or end_sec <= start_sec or end_sec <= 0:
        return Transcript(start_sec=start_sec, end_sec=end_sec, text="")
    if _has_whisper():
        text = _transcribe_with_whisper(path, start_sec, end_sec)
        return Transcript(start_sec=start_sec, end_sec=end_sec, text=text)
    if _is_demo_mode():
        logger.warning("ASR is not installed; demo mode enabled, returning sample text.")
        return Transcript(start_sec=start_sec, end_sec=end_sec, text="샘플 가사 텍스트")
    logger.warning("ASR is not installed; returning empty transcript.")
    return Transcript(start_sec=start_sec, end_sec=end_sec, text="")


def _has_whisper() -> bool:
    return importlib_util.find_spec("faster_whisper") is not None


def _is_demo_mode() -> bool:
    return os.getenv("ASR_DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def _transcribe_with_whisper(audio_path: Path, start_sec: float, end_sec: float) -> str:
    import importlib

    faster_whisper = importlib.import_module("faster_whisper")
    model = faster_whisper.WhisperModel("tiny", device="cpu", compute_type="int8")
    segment_path = _extract_audio_segment(audio_path, start_sec, end_sec)
    if segment_path is None:
        return ""
    try:
        segments, _info = model.transcribe(str(segment_path))
    finally:
        segment_path.unlink(missing_ok=True)
    texts = [chunk.text.strip() for chunk in segments if chunk.text.strip()]
    return " ".join(texts)


def _extract_audio_segment(audio_path: Path, start_sec: float, end_sec: float) -> Path | None:
    if end_sec <= start_sec:
        return None
    if shutil.which("ffmpeg") is None:
        return None
    duration = end_sec - start_sec
    if duration <= 0:
        return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        output_path = Path(temp_file.name)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_sec}",
        "-t",
        f"{duration}",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-y",
        str(output_path),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        return None
    return output_path
