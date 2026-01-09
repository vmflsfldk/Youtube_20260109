"""Audio matching stub."""

from __future__ import annotations

from typing import List

from worker.models import SongCandidate, SongSegment


def audio_match(segment: SongSegment) -> List[SongCandidate]:
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
