"""YouTube crawler helpers."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from importlib import util as importlib_util
from typing import Iterable, List

from worker.models import Video

logger = logging.getLogger(__name__)


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
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        videos = _fetch_uploads_with_api(channel_id, api_key)
        if videos:
            return videos
    if importlib_util.find_spec("yt_dlp") is not None:
        videos = _fetch_videos_with_ytdlp(channel_id)
        if videos:
            return videos
    return []


def fetch_live_videos(channel_id: str) -> List[Video]:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        videos = _fetch_live_and_archived_with_api(channel_id, api_key)
        if videos:
            return videos
    if importlib_util.find_spec("yt_dlp") is not None:
        videos = _fetch_live_videos_with_ytdlp(channel_id)
        if videos:
            return videos
    return []


def filter_new_videos(
    videos: Iterable[Video],
    processed_ids: Iterable[str],
    comment_training_processed_ids: Iterable[str] | None = None,
) -> List[Video]:
    processed = set(processed_ids)
    if comment_training_processed_ids is not None:
        processed |= set(comment_training_processed_ids)
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
    return _parse_videos(metadata)


def _parse_videos(metadata: dict | None) -> List[Video]:
    entries = metadata.get("entries") if metadata else None
    if not entries:
        return []
    videos: list[Video] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        video = _build_video(entry)
        if video:
            videos.append(video)
    return videos


def _build_video(entry: dict) -> Video | None:
    video_id = entry.get("id")
    title = entry.get("title")
    duration = entry.get("duration") or entry.get("duration_string") or 0
    try:
        duration_sec = int(duration)
    except (TypeError, ValueError):
        duration_sec = 0
    if not video_id or not title:
        return None
    exclude_live, live_status = _exclude_live_entry(entry)
    if exclude_live:
        logger.warning(
            "라이브/예정 라이브 영상 제외 (라이브 시작 전이면 제외): video_id=%s title=%s live_status=%s",
            video_id,
            title,
            live_status or "unknown",
        )
        return None
    is_live = _entry_is_live(entry)
    return Video(video_id=video_id, title=title, duration_sec=duration_sec, is_live=is_live)


def _exclude_live_entry(entry: dict) -> tuple[bool, str | None]:
    live_status = entry.get("live_status")
    if isinstance(live_status, str):
        if live_status in {"is_live", "is_upcoming"}:
            return True, live_status
        if live_status in {"not_live", "was_live", "post_live"}:
            return False, live_status
    if entry.get("is_live"):
        return True, "is_live"
    if entry.get("is_upcoming"):
        return True, "is_upcoming"
    if entry.get("was_live"):
        return False, "was_live"
    return False, None


def _entry_is_live(entry: dict) -> bool:
    live_status = entry.get("live_status")
    if isinstance(live_status, str):
        return live_status in {"is_live", "is_upcoming"}
    return bool(entry.get("is_live") or entry.get("is_upcoming"))


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


def _fetch_uploads_with_api(channel_id: str, api_key: str) -> List[Video]:
    channel_response = _youtube_api_request(
        "channels",
        {
            "part": "contentDetails",
            "id": channel_id,
            "maxResults": "1",
        },
        api_key,
    )
    if not channel_response:
        return []
    items = channel_response.get("items") or []
    if not items:
        return []
    uploads_id = (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )
    if not uploads_id:
        return []

    videos: list[Video] = []
    page_token: str | None = None
    while True:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": uploads_id,
            "maxResults": "50",
        }
        if page_token:
            params["pageToken"] = page_token
        response = _youtube_api_request("playlistItems", params, api_key)
        if not response:
            break
        items = response.get("items") or []
        video_ids = [
            item.get("contentDetails", {}).get("videoId")
            for item in items
            if item.get("contentDetails")
        ]
        durations = _fetch_video_durations(video_ids, api_key)
        for item in items:
            content = item.get("contentDetails", {})
            snippet = item.get("snippet", {})
            video_id = content.get("videoId")
            title = snippet.get("title")
            if not video_id or not title:
                continue
            videos.append(
                Video(
                    video_id=video_id,
                    title=title,
                    duration_sec=durations.get(video_id, 0),
                    is_live=False,
                )
            )
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return videos


def _fetch_live_and_archived_with_api(channel_id: str, api_key: str) -> List[Video]:
    videos: list[Video] = []
    for event_type, is_live in (("live", True), ("completed", False)):
        videos.extend(
            _fetch_search_event_videos(channel_id, api_key, event_type, is_live)
        )
    return videos


def _fetch_search_event_videos(
    channel_id: str,
    api_key: str,
    event_type: str,
    is_live: bool,
) -> List[Video]:
    videos: list[Video] = []
    page_token: str | None = None
    while True:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "eventType": event_type,
            "type": "video",
            "maxResults": "50",
        }
        if page_token:
            params["pageToken"] = page_token
        response = _youtube_api_request("search", params, api_key)
        if not response:
            break
        items = response.get("items") or []
        video_ids = [
            item.get("id", {}).get("videoId")
            for item in items
            if item.get("id")
        ]
        durations = _fetch_video_durations(video_ids, api_key)
        for item in items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId")
            title = snippet.get("title")
            if not video_id or not title:
                continue
            if is_live:
                logger.warning(
                    "라이브 영상 제외 (라이브 시작 전이면 제외): video_id=%s title=%s event_type=%s",
                    video_id,
                    title,
                    event_type,
                )
                continue
            videos.append(
                Video(
                    video_id=video_id,
                    title=title,
                    duration_sec=durations.get(video_id, 0),
                    is_live=is_live,
                )
            )
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return videos


def _fetch_video_durations(video_ids: list[str], api_key: str) -> dict[str, int]:
    durations: dict[str, int] = {}
    for chunk in _chunk_list(video_ids, 50):
        if not chunk:
            continue
        response = _youtube_api_request(
            "videos",
            {"part": "contentDetails", "id": ",".join(chunk)},
            api_key,
        )
        if not response:
            continue
        for item in response.get("items") or []:
            video_id = item.get("id")
            duration = item.get("contentDetails", {}).get("duration")
            if not video_id or not duration:
                continue
            durations[video_id] = _parse_iso8601_duration(duration)
    return durations


def _youtube_api_request(endpoint: str, params: dict, api_key: str) -> dict | None:
    params = {**params, "key": api_key}
    query = urllib.parse.urlencode(params)
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}?{query}"
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status != 200:
                    logging.warning(
                        "YouTube API responded with status %s for %s",
                        response.status,
                        endpoint,
                    )
                    return None
                payload = response.read().decode("utf-8")
                return json.loads(payload)
        except urllib.error.HTTPError as exc:
            logging.warning(
                "YouTube API HTTP error on attempt %s: %s",
                attempt,
                exc,
            )
        except urllib.error.URLError as exc:
            logging.warning(
                "YouTube API URL error on attempt %s: %s",
                attempt,
                exc,
            )
        except json.JSONDecodeError as exc:
            logging.warning("YouTube API JSON decode error: %s", exc)
            return None
        time.sleep(2**attempt)
    return None


def _parse_iso8601_duration(value: str) -> int:
    match = re.match(
        r"^PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$",
        value,
    )
    if not match:
        return 0
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return hours * 3600 + minutes * 60 + seconds


def _chunk_list(items: list[str], chunk_size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]


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
