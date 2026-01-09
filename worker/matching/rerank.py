"""Candidate reranking using lyrics signals."""

from __future__ import annotations

from typing import List

from worker.asr.transcribe import Transcript
from worker.matching.lyrics_match import match_lyrics
from worker.models import SongCandidate, SongSegment


def rerank_with_lyrics(segment: SongSegment, transcript: Transcript, candidates: List[SongCandidate]) -> SongCandidate:
    lyrics_scores = {score.song_id: score.score for score in match_lyrics(transcript, candidates)}
    weighted = []
    for candidate in candidates:
        lyric_score = lyrics_scores.get(candidate.song_id, 0.0)
        total = candidate.match_score + (segment.confidence * 0.05) + (lyric_score * 0.1)
        weighted.append((total, candidate))
    weighted.sort(key=lambda item: item[0], reverse=True)
    return weighted[0][1]
