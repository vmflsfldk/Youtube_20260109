"""Shared dataclasses for the pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    duration_sec: int


@dataclass(frozen=True)
class SongSegment:
    start_sec: float
    end_sec: float
    confidence: float

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


@dataclass(frozen=True)
class SongCandidate:
    song_id: str
    title: str
    original_artist: str
    match_score: float
    method: str


@dataclass(frozen=True)
class SongMatch:
    start_time: float
    end_time: float
    song_title: str
    original_artist: str
    confidence: float
