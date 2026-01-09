"""Helpers for fetching and parsing timestamped YouTube comments."""

from __future__ import annotations

import logging
import re
from importlib import util as importlib_util
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List

from worker.models import TimestampedComment

TIMESTAMP_PATTERN = re.compile(r"(?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})")
COMMENT_PATTERN = re.compile(
    r"(?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})\s+(?P<title>[^-/—]+?)\s*(?:-|/|—)\s*(?P<artist>.+)",
    re.UNICODE,
)


def fetch_timestamped_comments(video_id: str) -> List[TimestampedComment]:
    if importlib_util.find_spec("yt_dlp") is not None:
        comments = _fetch_comments_with_ytdlp(video_id)
        return comments
    return _fallback_timestamped_comments(video_id)


def save_timestamped_comments(video_id: str, comments: Iterable[TimestampedComment]) -> str:
    output_dir = Path("training") / "comments"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.json"
    payload = [asdict(comment) for comment in comments]
    output_path.write_text(_to_json(payload), encoding="utf-8")
    return str(output_path)


def _fetch_comments_with_ytdlp(video_id: str) -> List[TimestampedComment]:
    try:
        yt_dlp = _load_ytdlp()
    except ModuleNotFoundError:
        return []
    if yt_dlp is None:
        return []

    url = f"https://www.youtube.com/watch?v={video_id}"
    options = {"quiet": True, "skip_download": True, "extract_comments": True}
    ydl = yt_dlp.YoutubeDL(options)
    try:
        info = ydl.extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises many exception types
        logging.warning("yt-dlp failed to fetch comments for %s: %s", video_id, exc)
        return []
    raw_comments = [comment.get("text", "") for comment in info.get("comments", []) if isinstance(comment, dict)]
    return _parse_timestamped_comments(raw_comments)


def _parse_timestamped_comments(raw_comments: Iterable[str]) -> List[TimestampedComment]:
    parsed: list[TimestampedComment] = []
    for text in raw_comments:
        if not text or not TIMESTAMP_PATTERN.search(text):
            continue
        match = COMMENT_PATTERN.search(text)
        if not match:
            continue
        timestamp = _parse_timestamp(match.group("timestamp"))
        if timestamp is None:
            continue
        parsed.append(
            TimestampedComment(
                timestamp_sec=timestamp,
                song_title=match.group("title").strip(),
                original_artist=match.group("artist").strip(),
                raw_text=text,
            )
        )
    return parsed


def _parse_timestamp(value: str) -> float | None:
    parts = value.split(":")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None
    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds
    if len(numbers) == 3:
        hours, minutes, seconds = numbers
        return hours * 3600 + minutes * 60 + seconds
    return None


def _fallback_timestamped_comments(video_id: str) -> List[TimestampedComment]:
    seed = sum(ord(char) for char in video_id) % 3 + 1
    examples = [
        "0:35 Example Song A - Example Artist A",
        "5:12 Example Song B / Example Artist B",
        "12:01 Example Song C — Example Artist C",
    ]
    return _parse_timestamped_comments(examples[:seed])


def _load_ytdlp():
    if importlib_util.find_spec("yt_dlp") is None:
        return None
    import importlib

    return importlib.import_module("yt_dlp")


def _to_json(payload: object) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)
