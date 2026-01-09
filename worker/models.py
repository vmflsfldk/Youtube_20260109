"""Shared dataclasses for the pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    duration_sec: int
    is_live: bool = False


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


@dataclass(frozen=True)
class TimestampedComment:
    timestamp_sec: float
    song_title: str
    original_artist: str
    raw_text: str


@dataclass(frozen=True)
class TrainingSample:
    timestamp_sec: float
    expected_title: str
    expected_artist: str
    matched_title: str
    matched_artist: str
    match_score: float
    is_match: bool
