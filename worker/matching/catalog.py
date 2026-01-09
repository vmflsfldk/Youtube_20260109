"""Local song catalog used for deterministic candidate generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogSong:
    song_id: str
    title: str
    original_artist: str
    keywords: tuple[str, ...]


CATALOG: tuple[CatalogSong, ...] = (
    CatalogSong(
        song_id="song-001",
        title="노래 제목",
        original_artist="원곡자",
        keywords=("샘플", "노래", "제목"),
    ),
    CatalogSong(
        song_id="song-002",
        title="다른 노래",
        original_artist="다른 원곡자",
        keywords=("다른", "노래", "가사"),
    ),
    CatalogSong(
        song_id="song-003",
        title="별의 밤",
        original_artist="스텔라",
        keywords=("별", "밤", "우주", "꿈"),
    ),
)
