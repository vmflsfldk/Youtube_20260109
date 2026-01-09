"""Local song catalog used for deterministic candidate generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogSong:
    song_id: str
    title: str
    original_artist: str
    keywords: tuple[str, ...]
    embedding: tuple[float, ...] | None = None


CATALOG: tuple[CatalogSong, ...] = (
    CatalogSong(
        song_id="song-001",
        title="노래 제목",
        original_artist="원곡자",
        keywords=("샘플", "노래", "제목"),
        embedding=(0.12, 0.24, 0.38, 0.44, 0.19, 0.71, 0.33, 0.57),
    ),
    CatalogSong(
        song_id="song-002",
        title="다른 노래",
        original_artist="다른 원곡자",
        keywords=("다른", "노래", "가사"),
        embedding=(0.42, 0.18, 0.62, 0.29, 0.51, 0.22, 0.75, 0.36),
    ),
    CatalogSong(
        song_id="song-003",
        title="별의 밤",
        original_artist="스텔라",
        keywords=("별", "밤", "우주", "꿈"),
        embedding=(0.28, 0.55, 0.31, 0.66, 0.47, 0.15, 0.41, 0.83),
    ),
)
