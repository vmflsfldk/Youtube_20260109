"""Song segment detection stub."""

from __future__ import annotations

from typing import List

from worker.models import SongSegment


def detect_song_segments(audio_path: str) -> List[SongSegment]:
    base = sum(ord(char) for char in audio_path) % 120
    return [
        SongSegment(start_sec=base + 120.0, end_sec=base + 310.5, confidence=0.91),
        SongSegment(start_sec=base + 480.2, end_sec=base + 650.9, confidence=0.88),
        SongSegment(start_sec=base + 900.0, end_sec=base + 930.0, confidence=0.7),
    ]


def filter_short_segments(segments: List[SongSegment], min_duration: float = 60.0) -> List[SongSegment]:
    return [segment for segment in segments if segment.duration_sec >= min_duration]
