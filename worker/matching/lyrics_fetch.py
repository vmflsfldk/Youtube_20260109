"""Fetch lyrics from external sources or internal APIs."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LyricsFetchResult:
    lyrics_text: str
    source: str


def fetch_lyrics(title: str, artist: str) -> LyricsFetchResult | None:
    title = title.strip()
    artist = artist.strip()
    if not title or not artist:
        logger.warning("가사 검색 실패: 제목/아티스트 누락 (title=%s, artist=%s)", title, artist)
        return None

    api_url = os.getenv("LYRICS_API_URL")
    if api_url:
        result = _fetch_from_custom_api(api_url, title, artist)
        if result:
            return result

    return _fetch_from_lyrics_ovh(title, artist)


def _fetch_from_custom_api(api_url: str, title: str, artist: str) -> LyricsFetchResult | None:
    params = urlparse.urlencode({"title": title, "artist": artist})
    request_url = f"{api_url.rstrip('/')}/?{params}"
    response = _fetch_json(request_url)
    if response is None:
        logger.info("사내 가사 API 응답 없음: url=%s", request_url)
        return None
    lyrics = str(response.get("lyrics", "")).strip()
    if not lyrics:
        logger.info("사내 가사 API 결과 없음: title=%s artist=%s", title, artist)
        return None
    return LyricsFetchResult(lyrics_text=lyrics, source="internal-api")


def _fetch_from_lyrics_ovh(title: str, artist: str) -> LyricsFetchResult | None:
    encoded_artist = urlparse.quote(artist)
    encoded_title = urlparse.quote(title)
    request_url = f"https://api.lyrics.ovh/v1/{encoded_artist}/{encoded_title}"
    response = _fetch_json(request_url)
    if response is None:
        logger.info("외부 가사 API 실패: url=%s", request_url)
        return None
    lyrics = str(response.get("lyrics", "")).strip()
    if not lyrics:
        logger.info("외부 가사 API 결과 없음: title=%s artist=%s", title, artist)
        return None
    return LyricsFetchResult(lyrics_text=lyrics, source="lyrics.ovh")


def _fetch_json(request_url: str) -> dict[str, Any] | None:
    try:
        with urlrequest.urlopen(request_url, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except (urlerror.URLError, TimeoutError) as exc:
        logger.warning("가사 API 요청 실패: url=%s error=%s", request_url, exc)
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        logger.warning("가사 API JSON 파싱 실패: url=%s error=%s", request_url, exc)
        return None
    if isinstance(data, dict):
        return data
    return None
