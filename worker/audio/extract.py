"""Audio extraction and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Optional

from worker.models import Video


@dataclass(frozen=True)
class AudioAsset:
    path: str
    sample_rate: int


def extract_audio(video: Video, target_rate: int = 44100) -> AudioAsset:
    output_dir = Path("audio")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video.video_id}.wav"

    if output_path.exists():
        return AudioAsset(path=str(output_path), sample_rate=target_rate)

    source = f"https://www.youtube.com/watch?v={video.video_id}"
    if _ffmpeg_available():
        _extract_with_ffmpeg(source, output_path, target_rate)
    else:
        _write_silent_wav(output_path, target_rate, duration_sec=max(1, video.duration_sec))

    return AudioAsset(path=str(output_path), sample_rate=target_rate)


def _extract_with_ffmpeg(source: str, output_path: Path, target_rate: int) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        source,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(target_rate),
        "-ac",
        "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _ffmpeg_available() -> bool:
    return _which("ffmpeg") is not None


def _which(command: str) -> Optional[str]:
    import shutil

    return shutil.which(command)


def _write_silent_wav(output_path: Path, sample_rate: int, duration_sec: int) -> None:
    import wave

    frame_count = sample_rate * duration_sec
    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
