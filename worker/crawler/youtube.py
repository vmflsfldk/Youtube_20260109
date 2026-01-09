"""YouTube crawler helpers."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from importlib import util as importlib_util
from typing import Iterable, List

from worker.models import Video


def fetch_channel_id(channel_url: str) -> str:
    if importlib_util.find_spec("yt_dlp") is not None:
        channel_id = _resolve_channel_id_with_ytdlp(channel_url)
        if channel_id:
            return channel_id
    match = re.search(r"(UC[\w-]{5,})", channel_url)
    if match:
        return match.group(1)
    safe = re.sub(r"[^a-zA-Z0-9]", "", channel_url)[-10:]
    return f"UC{safe or 'UNKNOWN'}"


def fetch_videos(channel_id: str) -> List[Video]:
    if importlib_util.find_spec("yt_dlp") is not None:
        videos = _fetch_videos_with_ytdlp(channel_id)
        if videos:
            return videos
    seed = sum(ord(char) for char in channel_id) % 3 + 1
    return [
        Video(
            video_id=f"vid{index + 1:02d}",
            title=f"Sample Video {index + 1}",
            duration_sec=3600 + index * 600,
            is_live=False,
        )
        for index in range(seed)
    ]


def fetch_live_videos(channel_id: str) -> List[Video]:
    if importlib_util.find_spec("yt_dlp") is not None:
        videos = _fetch_live_videos_with_ytdlp(channel_id)
        if videos:
            return videos
    seed = sum(ord(char) for char in channel_id) % 2 + 1
    return [
        Video(
            video_id=f"live{index + 1:02d}",
            title=f"Sample Live Stream {index + 1}",
            duration_sec=7200 + index * 600,
            is_live=True,
        )
        for index in range(seed)
    ]


def filter_new_videos(videos: Iterable[Video], processed_ids: Iterable[str]) -> List[Video]:
    processed = set(processed_ids)
    return [video for video in videos if video.video_id not in processed]


def _resolve_channel_id_with_ytdlp(channel_url: str) -> str | None:
    metadata = _fetch_channel_metadata(channel_url, playlist_end=1)
    if not metadata:
        return None
    return metadata.get("channel_id") or metadata.get("uploader_id")


def _fetch_videos_with_ytdlp(channel_id: str) -> List[Video]:
    channel_url = f"https://www.youtube.com/channel/{channel_id}"
    metadata = _fetch_channel_metadata(channel_url)
    return _parse_videos(metadata)


def _fetch_live_videos_with_ytdlp(channel_id: str) -> List[Video]:
    channel_url = f"https://www.youtube.com/channel/{channel_id}/streams"
    metadata = _fetch_channel_metadata(channel_url)
    videos = _parse_videos(metadata, assume_live=True)
    return [video for video in videos if video.is_live]


def _parse_videos(metadata: dict | None, assume_live: bool = False) -> List[Video]:
    entries = metadata.get("entries") if metadata else None
    if not entries:
        return []
    videos: list[Video] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        video = _build_video(entry, assume_live=assume_live)
        if video:
            videos.append(video)
    return videos


def _build_video(entry: dict, assume_live: bool = False) -> Video | None:
    video_id = entry.get("id")
    title = entry.get("title")
    duration = entry.get("duration") or entry.get("duration_string") or 0
    try:
        duration_sec = int(duration)
    except (TypeError, ValueError):
        duration_sec = 0
    if not video_id or not title:
        return None
    is_live = _entry_is_live(entry) or assume_live
    return Video(video_id=video_id, title=title, duration_sec=duration_sec, is_live=is_live)


def _entry_is_live(entry: dict) -> bool:
    live_status = entry.get("live_status")
    if isinstance(live_status, str):
        return live_status in {"is_live", "was_live", "post_live"}
    return bool(entry.get("is_live") or entry.get("was_live"))


def _fetch_channel_metadata(channel_url: str, playlist_end: int | None = None) -> dict | None:
    yt_dlp = _load_ytdlp()
    if yt_dlp is None:
        return None
    options = {"quiet": True, "extract_flat": True}
    if playlist_end is not None:
        options["playlistend"] = playlist_end
    ydl = yt_dlp.YoutubeDL(options)
    try:
        return ydl.extract_info(channel_url, download=False)
    except yt_dlp.utils.DownloadError as exc:  # type: ignore[attr-defined]
        logging.warning("yt-dlp failed to fetch channel metadata: %s", exc)
        return _fallback_metadata(channel_url)


def _fallback_metadata(channel_url: str) -> dict | None:
    if not shutil_which("yt-dlp"):
        return None
    cmd = ["yt-dlp", "--dump-single-json", "--flat-playlist", channel_url]
    try:
        output = subprocess.check_output(cmd, text=True)
    except subprocess.CalledProcessError as exc:
        logging.warning("yt-dlp CLI failed: %s", exc)
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logging.warning("yt-dlp output parse error: %s", exc)
        return None


def _load_ytdlp():
    if importlib_util.find_spec("yt_dlp") is None:
        return None
    import importlib

    return importlib.import_module("yt_dlp")


def shutil_which(command: str) -> str | None:
    import shutil

    return shutil.which(command)
