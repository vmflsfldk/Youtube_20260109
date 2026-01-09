"""Catalog loader backed by a relational store."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Iterable

DEFAULT_DB_PATH = Path(os.getenv("SONG_CATALOG_DB", "worker/matching/songs.db"))


@dataclass(frozen=True)
class CatalogSong:
    song_id: str
    title: str
    original_artist: str
    aliases: tuple[str, ...]
    embedding: tuple[float, ...] | None = None


@dataclass(frozen=True)
class CatalogIndex:
    songs: tuple[CatalogSong, ...]

    def iter_embeddings(self) -> Iterable[tuple[int, tuple[float, ...]]]:
        for index, song in enumerate(self.songs):
            if song.embedding:
                yield index, song.embedding


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS songs (
            song_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            original_artist TEXT NOT NULL,
            aliases TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS song_embeddings (
            song_id TEXT PRIMARY KEY,
            embedding TEXT NOT NULL,
            FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
        )
        """
    )
    connection.commit()


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [str(item) for item in data if item]
    return []


def _parse_embedding(raw: str | None) -> tuple[float, ...] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    values: list[float] = []
    for item in data:
        try:
            values.append(float(item))
        except (TypeError, ValueError):
            continue
    return tuple(values) if values else None


def load_catalog(db_path: Path | None = None) -> tuple[CatalogSong, ...]:
    path = db_path or DEFAULT_DB_PATH
    with _connect(path) as connection:
        _ensure_schema(connection)
        rows = connection.execute(
            """
            SELECT songs.song_id, songs.title, songs.original_artist, songs.aliases,
                   song_embeddings.embedding
            FROM songs
            LEFT JOIN song_embeddings ON songs.song_id = song_embeddings.song_id
            ORDER BY songs.song_id
            """
        ).fetchall()
    songs: list[CatalogSong] = []
    for row in rows:
        aliases = tuple(_parse_json_list(row["aliases"]))
        embedding = _parse_embedding(row["embedding"])
        songs.append(
            CatalogSong(
                song_id=row["song_id"],
                title=row["title"],
                original_artist=row["original_artist"],
                aliases=aliases,
                embedding=embedding,
            )
        )
    return tuple(songs)


@lru_cache(maxsize=1)
def get_catalog_index(db_path: Path | None = None) -> CatalogIndex:
    return CatalogIndex(songs=load_catalog(db_path))
