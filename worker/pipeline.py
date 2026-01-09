"""Minimal pipeline implementation for YouTube singing segment detection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List


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


class ResultStore:
    """In-memory result collector mimicking a persistence layer."""

    def __init__(self) -> None:
        self._entries: list[dict[str, object]] = []

    def add(self, channel_id: str, video_id: str, matches: Iterable[SongMatch]) -> None:
        self._entries.append(
            {
                "channel_id": channel_id,
                "video_id": video_id,
                "results": [
                    {
                        "start_time": match.start_time,
                        "end_time": match.end_time,
                        "song_title": match.song_title,
                        "original_artist": match.original_artist,
                        "confidence": match.confidence,
                    }
                    for match in matches
                ],
            }
        )

    def dump(self) -> list[dict[str, object]]:
        return list(self._entries)


def fetch_channel_id(channel_url: str) -> str:
    match = re.search(r"(UC[\w-]{5,})", channel_url)
    if match:
        return match.group(1)
    safe = re.sub(r"[^a-zA-Z0-9]", "", channel_url)[-10:]
    return f"UC{safe or 'UNKNOWN'}"


def fetch_videos(channel_id: str) -> list[Video]:
    seed = sum(ord(char) for char in channel_id) % 3 + 1
    return [
        Video(
            video_id=f"vid{index + 1:02d}",
            title=f"Sample Video {index + 1}",
            duration_sec=3600 + index * 600,
        )
        for index in range(seed)
    ]


def extract_audio(video: Video) -> str:
    return f"audio/{video.video_id}.wav"


def detect_song_segments(audio_path: str) -> list[SongSegment]:
    base = sum(ord(char) for char in audio_path) % 120
    segments = [
        SongSegment(start_sec=base + 120.0, end_sec=base + 310.5, confidence=0.91),
        SongSegment(start_sec=base + 480.2, end_sec=base + 650.9, confidence=0.88),
        SongSegment(start_sec=base + 900.0, end_sec=base + 930.0, confidence=0.7),
    ]
    return segments


def audio_match(segment: SongSegment) -> list[SongCandidate]:
    return [
        SongCandidate(
            song_id="song-001",
            title="노래 제목",
            original_artist="원곡자",
            match_score=0.93,
            method="audio",
        ),
        SongCandidate(
            song_id="song-002",
            title="다른 노래",
            original_artist="다른 원곡자",
            match_score=0.76,
            method="audio",
        ),
    ]


def rerank_with_lyrics(segment: SongSegment, candidates: list[SongCandidate]) -> SongCandidate:
    weighted = [
        (candidate.match_score + (segment.confidence * 0.05), candidate)
        for candidate in candidates
    ]
    weighted.sort(key=lambda item: item[0], reverse=True)
    return weighted[0][1]


def save_result(
    store: ResultStore,
    channel_id: str,
    video: Video,
    segment: SongSegment,
    best: SongCandidate,
) -> None:
    match = SongMatch(
        start_time=segment.start_sec,
        end_time=segment.end_sec,
        song_title=best.title,
        original_artist=best.original_artist,
        confidence=round(min(0.99, best.match_score * segment.confidence), 2),
    )
    store.add(channel_id, video.video_id, [match])


def process_channel(channel_url: str) -> list[dict[str, object]]:
    channel_id = fetch_channel_id(channel_url)
    videos = fetch_videos(channel_id)
    store = ResultStore()

    for video in videos:
        _audio = extract_audio(video)
        segments = detect_song_segments(_audio)

        for seg in segments:
            if seg.duration_sec < 60:
                continue

            candidates = audio_match(seg)
            best = rerank_with_lyrics(seg, candidates)

            save_result(store, channel_id, video, seg, best)

    return store.dump()


def main() -> None:
    channel_url = input("Channel URL: ").strip()
    started_at = datetime.now(timezone.utc).isoformat()
    results = process_channel(channel_url)
    print(
        json.dumps(
            {
                "requested_at": started_at,
                "channel_url": channel_url,
                "outputs": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
