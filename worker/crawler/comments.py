"""Helpers for fetching and parsing timestamped YouTube comments."""

from __future__ import annotations

import logging
import re
from importlib import util as importlib_util
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from worker.models import TimestampedComment


@dataclass(frozen=True)
class ParsedComments:
    comments: list[TimestampedComment]
    total_comments: int
    parsed_comments: int

TIMESTAMP_PATTERN = re.compile(r"(?P<timestamp>(?:\d{1,2}:)?\d{1,2}:\d{2})")
TITLE_ARTIST_PATTERN = re.compile(r"(?P<title>[^-/—]+?)\s*(?:-|/|—)\s*(?P<artist>.+)", re.UNICODE)


def fetch_timestamped_comments(video_id: str) -> ParsedComments:
    if importlib_util.find_spec("yt_dlp") is not None:
        return _fetch_comments_with_ytdlp(video_id)
    return _fallback_timestamped_comments(video_id)


def save_timestamped_comments(video_id: str, comments: Iterable[TimestampedComment]) -> str:
    output_dir = Path("training") / "comments"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.json"
    payload = [asdict(comment) for comment in comments]
    output_path.write_text(_to_json(payload), encoding="utf-8")
    return str(output_path)


def _fetch_comments_with_ytdlp(video_id: str) -> ParsedComments:
    try:
        yt_dlp = _load_ytdlp()
    except ModuleNotFoundError:
        return ParsedComments(comments=[], total_comments=0, parsed_comments=0)
    if yt_dlp is None:
        return ParsedComments(comments=[], total_comments=0, parsed_comments=0)

    url = f"https://www.youtube.com/watch?v={video_id}"
    options = {"quiet": True, "skip_download": True, "extract_comments": True}
    ydl = yt_dlp.YoutubeDL(options)
    try:
        info = ydl.extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001 - yt-dlp raises many exception types
        logging.warning("yt-dlp failed to fetch comments for %s: %s", video_id, exc)
        return ParsedComments(comments=[], total_comments=0, parsed_comments=0)
    raw_comments = [comment.get("text", "") for comment in info.get("comments", []) if isinstance(comment, dict)]
    return _parse_timestamped_comments(raw_comments)


def _parse_timestamped_comments(raw_comments: Iterable[str]) -> ParsedComments:
    parsed: list[TimestampedComment] = []
    total_comments = 0
    excluded_comments = 0
    parsed_comments = 0
    for text in raw_comments:
        total_comments += 1
        if not text:
            excluded_comments += 1
            continue
        timestamp_matches = list(TIMESTAMP_PATTERN.finditer(text))
        if not timestamp_matches:
            excluded_comments += 1
            continue
        parsed_for_comment = 0
        for index, match in enumerate(timestamp_matches):
            timestamp = _parse_timestamp(match.group("timestamp"))
            if timestamp is None:
                continue
            segment_end = timestamp_matches[index + 1].start() if index + 1 < len(timestamp_matches) else len(text)
            segment = text[match.end() : segment_end].strip()
            title, artist = _parse_title_artist(segment)
            if not title:
                continue
            parsed.append(
                TimestampedComment(
                    timestamp_sec=timestamp,
                    song_title=title,
                    original_artist=artist,
                    raw_text=text,
                )
            )
            parsed_for_comment += 1
        if parsed_for_comment == 0:
            excluded_comments += 1
        else:
            parsed_comments += 1
    logging.info(
        "Parsed %d timestamped segments from %d comments (%d with timestamps, %d excluded).",
        len(parsed),
        total_comments,
        parsed_comments,
        excluded_comments,
    )
    return ParsedComments(comments=parsed, total_comments=total_comments, parsed_comments=parsed_comments)


def _parse_title_artist(segment: str) -> tuple[str | None, str]:
    if not segment:
        return None, ""
    match = TITLE_ARTIST_PATTERN.search(segment)
    if match:
        return match.group("title").strip(), match.group("artist").strip()
    cleaned = segment.strip().strip("-/—").strip()
    if cleaned:
        return cleaned, ""
    return None, ""


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


def _fallback_timestamped_comments(video_id: str) -> ParsedComments:
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
