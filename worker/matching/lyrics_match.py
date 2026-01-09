"""Lyrics matching with lightweight token similarity."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
from typing import List

from worker.asr.transcribe import Transcript
from worker.matching.catalog import get_catalog_index, get_song_lyrics_map
from worker.models import SongCandidate


@dataclass(frozen=True)
class LyricsScore:
    song_id: str
    score: float


def match_lyrics(transcript: Transcript, candidates: List[SongCandidate]) -> List[LyricsScore]:
    text = transcript.text.strip()
    if not text:
        return [LyricsScore(song_id=candidate.song_id, score=0.0) for candidate in candidates]

    tokens = _tokenize(text)
    scores: list[LyricsScore] = []
    use_rapidfuzz = importlib_util.find_spec("rapidfuzz") is not None

    catalog = get_catalog_index()
    lyrics_map = get_song_lyrics_map([candidate.song_id for candidate in candidates])
    for candidate in candidates:
        lyrics_entry = lyrics_map.get(candidate.song_id)
        lyrics_text = lyrics_entry.lyrics_text if lyrics_entry else ""
        catalog_keywords = next(
            (
                (song.title, song.original_artist, *song.aliases)
                for song in catalog.songs
                if song.song_id == candidate.song_id
            ),
            tuple(),
        )
        keyword_tokens = _tokenize(" ".join(str(value) for value in catalog_keywords))
        lyrics_tokens = _tokenize(lyrics_text)
        target_tokens = lyrics_tokens or keyword_tokens
        overlap = tokens.intersection(target_tokens)
        base = (len(overlap) / max(1, len(target_tokens))) if target_tokens else 0.0
        similarity = base

        if use_rapidfuzz:
            from rapidfuzz import fuzz  # type: ignore[import-not-found]

            if lyrics_text:
                similarity = max(similarity, fuzz.partial_ratio(text, lyrics_text) / 100.0)
            else:
                similarity = max(similarity, fuzz.partial_ratio(text, candidate.title) / 100.0)
                similarity = max(similarity, fuzz.partial_ratio(text, candidate.original_artist) / 100.0)

        score = min(0.99, 0.5 * similarity + 0.1 * candidate.match_score)
        scores.append(LyricsScore(song_id=candidate.song_id, score=round(score, 2)))

    return scores


def _tokenize(value: str) -> set[str]:
    return {token for token in value.replace("\n", " ").split() if token}
