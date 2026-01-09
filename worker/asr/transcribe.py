"""ASR transcription helper."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
from pathlib import Path

from worker.models import SongSegment


@dataclass(frozen=True)
class Transcript:
    segment: SongSegment
    text: str


def transcribe_segment(segment: SongSegment) -> Transcript:
    if _has_whisper():
        text = _transcribe_with_whisper(segment)
        return Transcript(segment=segment, text=text)
    return Transcript(segment=segment, text="샘플 가사 텍스트")


def _has_whisper() -> bool:
    return importlib_util.find_spec("faster_whisper") is not None


def _transcribe_with_whisper(segment: SongSegment) -> str:
    import importlib

    faster_whisper = importlib.import_module("faster_whisper")
    model = faster_whisper.WhisperModel("tiny", device="cpu", compute_type="int8")
    audio_path = Path("audio")
    if not audio_path.exists():
        return ""
    target_files = list(audio_path.glob("*.wav"))
    if not target_files:
        return ""
    segments, _info = model.transcribe(str(target_files[0]))
    texts = [chunk.text.strip() for chunk in segments if chunk.text.strip()]
    return " ".join(texts)
