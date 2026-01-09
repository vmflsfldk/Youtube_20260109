"""Lyrics matching with lightweight token similarity."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
from typing import List

from worker.asr.transcribe import Transcript
from worker.matching.catalog import get_catalog_index
from worker.models import SongCandidate


@dataclass(frozen=True)
class LyricsScore:
    song_id: str
    score: float


def match_lyrics(transcript: Transcript, candidates: List[SongCandidate]) -> List[LyricsScore]:
    text = transcript.text.strip()
    if not text:
        return [LyricsScore(song_id=candidate.song_id, score=0.0) for candidate in candidates]

    tokens = {token for token in text.replace("\n", " ").split() if token}
    scores: list[LyricsScore] = []
    use_rapidfuzz = importlib_util.find_spec("rapidfuzz") is not None

    catalog = get_catalog_index()
    for candidate in candidates:
        catalog_keywords = next(
            (
                (song.title, song.original_artist, *song.aliases)
                for song in catalog.songs
                if song.song_id == candidate.song_id
            ),
            tuple(),
        )
        keyword_tokens = {
            token
            for value in catalog_keywords
            for token in str(value).replace("\n", " ").split()
            if token
        }
        overlap = tokens.intersection(keyword_tokens)
        base = (len(overlap) / max(1, len(keyword_tokens))) if keyword_tokens else 0.0
        similarity = base

        if use_rapidfuzz:
            from rapidfuzz import fuzz  # type: ignore[import-not-found]

            similarity = max(similarity, fuzz.partial_ratio(text, candidate.title) / 100.0)
            similarity = max(similarity, fuzz.partial_ratio(text, candidate.original_artist) / 100.0)

        score = min(0.99, 0.5 * similarity + 0.1 * candidate.match_score)
        scores.append(LyricsScore(song_id=candidate.song_id, score=round(score, 2)))

    return scores
