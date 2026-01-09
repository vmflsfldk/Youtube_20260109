"""Minimal end-to-end pipeline implementation for YouTube singing segment detection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from worker.asr.transcribe import transcribe_segment
from worker.audio.extract import AudioAsset, extract_audio
from worker.audio.vocal import separate_vocals
from worker.crawler.youtube import fetch_channel_id, fetch_videos, filter_new_videos
from worker.matching.audio_match import audio_match
from worker.matching.rerank import rerank_with_lyrics
from worker.models import SongMatch, SongSegment, Video
from worker.segment.detect import detect_song_segments, filter_short_segments


@dataclass(frozen=True)
class PipelineConfig:
    min_segment_duration: float = 60.0
    enable_vocal_separation: bool = False
    sample_rate: int = 44100
    use_lyrics_rerank: bool = True


class ResultStore:
    """In-memory result collector mimicking a persistence layer."""

    def __init__(self) -> None:
        self._entries: list[dict[str, object]] = []

    def add(self, channel_id: str, video_id: str, matches: Iterable[SongMatch]) -> None:
        self._entries.append(
            {
                "channel_id": channel_id,
                "video_id": video_id,
                "results": [
                    {
                        "start_time": match.start_time,
                        "end_time": match.end_time,
                        "song_title": match.song_title,
                        "original_artist": match.original_artist,
                        "confidence": match.confidence,
                    }
                    for match in matches
                ],
            }
        )

    def dump(self) -> list[dict[str, object]]:
        return list(self._entries)


def prepare_audio(video: Video, config: PipelineConfig) -> AudioAsset:
    audio = extract_audio(video, target_rate=config.sample_rate)
    if config.enable_vocal_separation:
        vocal = separate_vocals(audio)
        return AudioAsset(path=vocal.path, sample_rate=audio.sample_rate)
    return audio


def build_song_match(segment: SongSegment, best_title: str, best_artist: str, score: float) -> SongMatch:
    return SongMatch(
        start_time=segment.start_sec,
        end_time=segment.end_sec,
        song_title=best_title,
        original_artist=best_artist,
        confidence=round(min(0.99, score * segment.confidence), 2),
    )


def process_video(channel_id: str, video: Video, config: PipelineConfig, store: ResultStore) -> None:
    audio = prepare_audio(video, config)
    segments = detect_song_segments(audio.path)
    filtered_segments = filter_short_segments(segments, min_duration=config.min_segment_duration)

    matches: list[SongMatch] = []
    for segment in filtered_segments:
        candidates = audio_match(segment)
        if config.use_lyrics_rerank:
            transcript = transcribe_segment(segment)
            best = rerank_with_lyrics(segment, transcript, candidates)
        else:
            best = sorted(candidates, key=lambda item: item.match_score, reverse=True)[0]
        match = build_song_match(segment, best.title, best.original_artist, best.match_score)
        matches.append(match)

    store.add(channel_id, video.video_id, matches)


def process_channel(channel_url: str, config: PipelineConfig | None = None) -> list[dict[str, object]]:
    config = config or PipelineConfig()
    channel_id = fetch_channel_id(channel_url)
    videos = fetch_videos(channel_id)
    videos = filter_new_videos(videos, processed_ids=[])
    store = ResultStore()

    for video in videos:
        process_video(channel_id, video, config, store)

    return store.dump()


def main() -> None:
    channel_url = input("Channel URL: ").strip()
    started_at = datetime.now(timezone.utc).isoformat()
    results = process_channel(channel_url)
    print(
        json.dumps(
            {
                "requested_at": started_at,
                "channel_url": channel_url,
                "outputs": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
