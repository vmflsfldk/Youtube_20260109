"""Lyrics matching stub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from worker.asr.transcribe import Transcript
from worker.models import SongCandidate


@dataclass(frozen=True)
class LyricsScore:
    song_id: str
    score: float


def match_lyrics(transcript: Transcript, candidates: List[SongCandidate]) -> List[LyricsScore]:
    base = 0.5 if "샘플" in transcript.text else 0.4
    return [
        LyricsScore(song_id=candidate.song_id, score=base + candidate.match_score * 0.1)
        for candidate in candidates
    ]
