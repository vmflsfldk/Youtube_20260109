"""Audio extraction and normalization stubs."""

from __future__ import annotations

from dataclasses import dataclass

from worker.models import Video


@dataclass(frozen=True)
class AudioAsset:
    path: str
    sample_rate: int


def extract_audio(video: Video, target_rate: int = 44100) -> AudioAsset:
    return AudioAsset(path=f"audio/{video.video_id}.wav", sample_rate=target_rate)
