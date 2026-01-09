"""Minimal YouTube crawler stubs for the beta pipeline."""

from __future__ import annotations

import re
from typing import Iterable, List

from worker.models import Video


def fetch_channel_id(channel_url: str) -> str:
    match = re.search(r"(UC[\w-]{5,})", channel_url)
    if match:
        return match.group(1)
    safe = re.sub(r"[^a-zA-Z0-9]", "", channel_url)[-10:]
    return f"UC{safe or 'UNKNOWN'}"


def fetch_videos(channel_id: str) -> List[Video]:
    seed = sum(ord(char) for char in channel_id) % 3 + 1
    return [
        Video(
            video_id=f"vid{index + 1:02d}",
            title=f"Sample Video {index + 1}",
            duration_sec=3600 + index * 600,
        )
        for index in range(seed)
    ]


def filter_new_videos(videos: Iterable[Video], processed_ids: Iterable[str]) -> List[Video]:
    processed = set(processed_ids)
    return [video for video in videos if video.video_id not in processed]
