"""Audio matching using deterministic heuristics."""

from __future__ import annotations

from typing import List

from worker.matching.catalog import CATALOG
from worker.models import SongCandidate, SongSegment


def audio_match(segment: SongSegment) -> List[SongCandidate]:
    duration_factor = min(1.0, segment.duration_sec / 240.0)
    base = 0.6 + (segment.confidence * 0.2) + (duration_factor * 0.2)
    candidates: list[SongCandidate] = []
    for index, song in enumerate(CATALOG):
        offset = (index + int(segment.start_sec) % 3) * 0.03
        score = max(0.0, min(0.99, base - offset))
        candidates.append(
            SongCandidate(
                song_id=song.song_id,
                title=song.title,
                original_artist=song.original_artist,
                match_score=round(score, 2),
                method="audio",
            )
        )
    candidates.sort(key=lambda item: item.match_score, reverse=True)
    return candidates
