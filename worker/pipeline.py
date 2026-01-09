"""Minimal end-to-end pipeline implementation for YouTube singing segment detection."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from worker.asr.transcribe import transcribe_segment
from worker.audio.extract import AudioAsset, extract_audio
from worker.audio.vocal import separate_vocals
from worker.crawler.comments import fetch_timestamped_comments, save_timestamped_comments
from worker.crawler.youtube import fetch_channel_id, fetch_live_videos, fetch_videos, filter_new_videos
from worker.matching.audio_match import audio_match
from worker.matching.catalog import find_song_id_by_title_artist, has_song_lyrics, upsert_song_lyrics
from worker.matching.lyrics_fetch import fetch_lyrics
from worker.matching.rerank import rerank_with_lyrics
from worker.matching.training import build_training_samples, save_training_samples, summarize_training
from worker.models import SongMatch, SongSegment, Video
from worker.segment.detect import detect_song_segments, filter_short_segments


@dataclass(frozen=True)
class PipelineConfig:
    min_segment_duration: float = 60.0
    min_segment_confidence: float = 0.6
    segment_min_song_prob: float = 0.55
    segment_merge_gap_sec: float = 3.0
    segment_merge_confidence_threshold: float = 0.7
    segment_merge_confidence_bonus_sec: float = 2.0
    segment_model_weight: float = 0.6
    segment_rms_weight: float = 0.25
    segment_label_weight: float = 0.15
    enable_vocal_separation: bool = False
    sample_rate: int = 44100
    use_lyrics_rerank: bool = True
    comment_window_sec: float = 30.0


DEFAULT_DB_PATH = Path(os.getenv("PIPELINE_DB_PATH", "worker/pipeline.db"))
logger = logging.getLogger(__name__)


def _connect_db(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    _ensure_schema(connection)
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_url TEXT,
            channel_name TEXT,
            last_crawled_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            channel_id TEXT,
            title TEXT,
            duration_sec INTEGER,
            published_at TEXT,
            processed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS song_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            start_sec REAL,
            end_sec REAL,
            duration_sec REAL,
            confidence REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS song_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment_id INTEGER,
            song_id TEXT,
            match_score REAL,
            method TEXT,
            confirmed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def _normalize_comment_value(value: str) -> str:
    return value.strip().lower()


def _upsert_channel(connection: sqlite3.Connection, channel_id: str, channel_url: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        INSERT INTO channels (channel_id, channel_url, last_crawled_at)
        VALUES (?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            channel_url = excluded.channel_url,
            last_crawled_at = excluded.last_crawled_at
        """,
        (channel_id, channel_url, now),
    )
    connection.commit()


def _upsert_video(
    connection: sqlite3.Connection, channel_id: str, video: Video, processed: bool = False
) -> None:
    connection.execute(
        """
        INSERT INTO videos (video_id, channel_id, title, duration_sec, processed)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            channel_id = excluded.channel_id,
            title = excluded.title,
            duration_sec = excluded.duration_sec,
            processed = excluded.processed
        """,
        (video.video_id, channel_id, video.title, video.duration_sec, int(processed)),
    )
    connection.commit()


def _mark_video_processed(connection: sqlite3.Connection, video_id: str) -> None:
    connection.execute("UPDATE videos SET processed = 1 WHERE video_id = ?", (video_id,))
    connection.commit()


def _fetch_processed_video_ids(connection: sqlite3.Connection, channel_id: str) -> list[str]:
    rows = connection.execute(
        "SELECT video_id FROM videos WHERE channel_id = ? AND processed = 1",
        (channel_id,),
    ).fetchall()
    return [row["video_id"] for row in rows]


def _insert_segment(connection: sqlite3.Connection, video_id: str, segment: SongSegment) -> int:
    cursor = connection.execute(
        """
        INSERT INTO song_segments (video_id, start_sec, end_sec, duration_sec, confidence)
        VALUES (?, ?, ?, ?, ?)
        """,
        (video_id, segment.start_sec, segment.end_sec, segment.duration_sec, segment.confidence),
    )
    connection.commit()
    return int(cursor.lastrowid)


def _insert_match(
    connection: sqlite3.Connection,
    segment_id: int,
    song_id: str,
    match_score: float,
    method: str,
) -> None:
    connection.execute(
        """
        INSERT INTO song_matches (segment_id, song_id, match_score, method)
        VALUES (?, ?, ?, ?)
        """,
        (segment_id, song_id, match_score, method),
    )
    connection.commit()


def _save_feedback_template(
    channel_id: str,
    video_id: str,
    matches: Sequence[SongMatch],
) -> str:
    output_dir = Path("training") / "feedback"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.json"
    payload = {
        "channel_id": channel_id,
        "video_id": video_id,
        "items": [
            {
                "start_time": match.start_time,
                "end_time": match.end_time,
                "song_title": match.song_title,
                "original_artist": match.original_artist,
                "confidence": match.confidence,
                "corrected_title": None,
                "corrected_artist": None,
                "notes": None,
            }
            for match in matches
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output_path)


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


def process_video(
    channel_id: str,
    video: Video,
    config: PipelineConfig,
    connection: sqlite3.Connection,
) -> dict[str, object]:
    _upsert_video(connection, channel_id, video, processed=False)
    audio = prepare_audio(video, config)
    segments = detect_song_segments(
        audio.path,
        min_song_prob=config.segment_min_song_prob,
        merge_gap_sec=config.segment_merge_gap_sec,
        model_weight=config.segment_model_weight,
        rms_weight=config.segment_rms_weight,
        label_weight=config.segment_label_weight,
        merge_confidence_threshold=config.segment_merge_confidence_threshold,
        merge_confidence_bonus_sec=config.segment_merge_confidence_bonus_sec,
    )
    filtered_segments = filter_short_segments(
        segments,
        min_duration=config.min_segment_duration,
        min_confidence=config.min_segment_confidence,
    )

    matches: list[SongMatch] = []
    for segment in filtered_segments:
        segment_id = _insert_segment(connection, video.video_id, segment)
        candidates = audio_match(audio.path, segment.start_sec, segment.end_sec)
        if not candidates:
            logger.warning(
                "오디오 매칭 후보 없음: video_id=%s start_sec=%s end_sec=%s",
                video.video_id,
                segment.start_sec,
                segment.end_sec,
            )
            matches.append(build_song_match(segment, "unknown", "unknown", 0.0))
            continue
        if config.use_lyrics_rerank:
            transcript = transcribe_segment(audio.path, segment.start_sec, segment.end_sec)
            best = rerank_with_lyrics(segment, transcript, candidates)
            if best is None:
                logger.warning(
                    "가사 리랭크 결과 없음: video_id=%s start_sec=%s end_sec=%s",
                    video.video_id,
                    segment.start_sec,
                    segment.end_sec,
                )
                matches.append(build_song_match(segment, "unknown", "unknown", 0.0))
                continue
        else:
            best = sorted(candidates, key=lambda item: item.match_score, reverse=True)[0]
        _insert_match(connection, segment_id, best.song_id, best.match_score, best.method)
        match = build_song_match(segment, best.title, best.original_artist, best.match_score)
        matches.append(match)

    _mark_video_processed(connection, video.video_id)
    feedback_path = _save_feedback_template(channel_id, video.video_id, matches)
    return {
        "channel_id": channel_id,
        "video_id": video.video_id,
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
        "feedback_template_path": feedback_path,
    }


def process_channel(
    channel_url: str,
    config: PipelineConfig | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    config = config or PipelineConfig()
    logger.info("process_channel 시작: channel_url=%s", channel_url)
    channel_id = fetch_channel_id(channel_url)
    connection = _connect_db(db_path)
    _upsert_channel(connection, channel_id, channel_url)
    processed_ids = _fetch_processed_video_ids(connection, channel_id)
    videos = fetch_videos(channel_id)
    videos = filter_new_videos(videos, processed_ids=processed_ids)
    outputs: list[dict[str, object]] = []

    total = len(videos)
    for index, video in enumerate(videos, start=1):
        logger.info(
            "영상 처리 시작 (%s/%s): video_id=%s title=%s",
            index,
            total,
            video.video_id,
            video.title,
        )
        outputs.append(process_video(channel_id, video, config, connection))
        logger.info(
            "영상 처리 완료 (%s/%s): video_id=%s title=%s",
            index,
            total,
            video.video_id,
            video.title,
        )

    if not outputs:
        logger.info("처리할 새 영상이 없습니다. (새 영상 없음/필터링됨)")

    connection.close()
    logger.info("process_channel 종료: channel_url=%s results=%s", channel_url, len(outputs))
    return outputs


def collect_archived_audio(
    channel_url: str,
    config: PipelineConfig | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    config = config or PipelineConfig()
    logger.info("collect_archived_audio 시작: channel_url=%s", channel_url)
    channel_id = fetch_channel_id(channel_url)
    connection = _connect_db(db_path)
    _upsert_channel(connection, channel_id, channel_url)
    processed_ids = _fetch_processed_video_ids(connection, channel_id)
    videos = fetch_live_videos(channel_id)
    videos = filter_new_videos(videos, processed_ids=processed_ids)
    outputs: list[dict[str, object]] = []

    total = len(videos)
    for index, video in enumerate(videos, start=1):
        logger.info(
            "아카이브 음원 수집 시작 (%s/%s): video_id=%s title=%s",
            index,
            total,
            video.video_id,
            video.title,
        )
        audio = extract_audio(video, target_rate=config.sample_rate)
        outputs.append(
            {
                "channel_id": channel_id,
                "video_id": video.video_id,
                "title": video.title,
                "audio_path": audio.path,
                "sample_rate": audio.sample_rate,
                "is_live": video.is_live,
            }
        )
        logger.info(
            "아카이브 음원 수집 완료 (%s/%s): video_id=%s title=%s",
            index,
            total,
            video.video_id,
            video.title,
        )

    if not outputs:
        logger.info("수집할 아카이브 영상이 없습니다. (새 영상 없음/필터링됨/라이브 시작 전이면 제외)")

    connection.close()
    logger.info("collect_archived_audio 종료: channel_url=%s results=%s", channel_url, len(outputs))
    return outputs


def collect_archived_comment_training(
    channel_url: str,
    config: PipelineConfig | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    config = config or PipelineConfig()
    logger.info("collect_archived_comment_training 시작: channel_url=%s", channel_url)
    channel_id = fetch_channel_id(channel_url)
    connection = _connect_db(db_path)
    _upsert_channel(connection, channel_id, channel_url)
    processed_ids = _fetch_processed_video_ids(connection, channel_id)
    videos = fetch_live_videos(channel_id)
    videos = filter_new_videos(videos, processed_ids=processed_ids)
    outputs: list[dict[str, object]] = []

    total = len(videos)
    for index, video in enumerate(videos, start=1):
        logger.info(
            "아카이브 댓글 학습 수집 시작 (%s/%s): video_id=%s title=%s",
            index,
            total,
            video.video_id,
            video.title,
        )
        audio = extract_audio(video, target_rate=config.sample_rate)
        parsed_comments = fetch_timestamped_comments(video.video_id)
        comments = parsed_comments.comments
        comment_path = save_timestamped_comments(video.video_id, comments)
        lyrics_updates: list[dict[str, str]] = []
        unique_songs: dict[tuple[str, str], tuple[str, str]] = {}
        for comment in comments:
            key = (_normalize_comment_value(comment.song_title), _normalize_comment_value(comment.original_artist))
            if key not in unique_songs:
                unique_songs[key] = (comment.song_title, comment.original_artist)

        for song_title, original_artist in unique_songs.values():
            song_id = find_song_id_by_title_artist(song_title, original_artist)
            if not song_id:
                lyrics_updates.append(
                    {
                        "song_title": song_title,
                        "original_artist": original_artist,
                        "status": "song_id_not_found",
                    }
                )
                continue
            if has_song_lyrics(song_id):
                lyrics_updates.append(
                    {
                        "song_id": song_id,
                        "song_title": song_title,
                        "original_artist": original_artist,
                        "status": "exists",
                    }
                )
                continue
            result = fetch_lyrics(song_title, original_artist)
            if result is None:
                lyrics_updates.append(
                    {
                        "song_id": song_id,
                        "song_title": song_title,
                        "original_artist": original_artist,
                        "status": "lyrics_not_found",
                    }
                )
                continue
            upsert_song_lyrics(song_id, result.lyrics_text, result.source)
            lyrics_updates.append(
                {
                    "song_id": song_id,
                    "song_title": song_title,
                    "original_artist": original_artist,
                    "status": "stored",
                    "source": result.source,
                }
            )
        if comments:
            samples = build_training_samples(
                audio,
                comments,
                window_sec=config.comment_window_sec,
                use_lyrics_rerank=config.use_lyrics_rerank,
            )
            sample_path = save_training_samples(video.video_id, samples)
        else:
            samples = []
            sample_path = None
        summary = summarize_training(samples)
        outputs.append(
            {
                "channel_id": channel_id,
                "video_id": video.video_id,
                "title": video.title,
                "audio_path": audio.path,
                "sample_rate": audio.sample_rate,
                "timestamped_comments": [
                    {
                        "timestamp_sec": comment.timestamp_sec,
                        "song_title": comment.song_title,
                        "original_artist": comment.original_artist,
                        "raw_text": comment.raw_text,
                    }
                    for comment in comments
                ],
                "timestamped_comments_path": comment_path,
                "training_samples_path": sample_path,
                "training_summary": summary,
                "training_summary_empty": not summary or summary.get("total", 0.0) == 0.0,
                "raw_comment_count": parsed_comments.total_comments,
                "timestamped_comment_count": parsed_comments.parsed_comments,
                "comment_status": (
                    "댓글 없음"
                    if parsed_comments.total_comments == 0
                    else "타임스탬프 없음"
                    if parsed_comments.parsed_comments == 0
                    else "댓글 있음"
                ),
                "lyrics_updates": lyrics_updates,
            }
        )
        logger.info(
            "아카이브 댓글 학습 수집 완료 (%s/%s): video_id=%s title=%s raw_comments=%s timestamped_comments=%s",
            index,
            total,
            video.video_id,
            video.title,
            parsed_comments.total_comments,
            parsed_comments.parsed_comments,
        )

    if not outputs:
        logger.info("학습할 아카이브 영상이 없습니다. (새 영상 없음/필터링됨/라이브 시작 전이면 제외)")

    connection.close()
    logger.info(
        "collect_archived_comment_training 종료: channel_url=%s results=%s",
        channel_url,
        len(outputs),
    )
    return outputs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(
        description="YouTube singing segment pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--channel-url",
        help="대상 채널 URL (미지정 시 대화형 입력).",
    )
    parser.add_argument(
        "--stage",
        choices=("crawl", "analysis", "comment-training"),
        help=(
            "실행 단계 선택: crawl(아카이브 음원 수집) | analysis(전체 분석) | comment-training(아카이브 댓글 학습).\n"
            "미지정 시 대화형 입력으로 1~3 선택."
        ),
    )
    parser.add_argument(
        "--output",
        help="결과 JSON을 저장할 파일 경로. 미지정 시 stdout에 출력.",
    )
    parser.add_argument(
        "--db-path",
        help=(
            "SQLite DB 파일 경로 (기본: 환경변수 PIPELINE_DB_PATH 또는 worker/pipeline.db). "
            "채널/영상 상태를 이 파일에 저장."
        ),
    )
    args = parser.parse_args()

    channel_url = (args.channel_url or "").strip()
    while not channel_url:
        print("오류: 채널 URL이 비어 있습니다. 다시 입력해주세요.")
        channel_url = input("Channel URL: ").strip()

    stage = args.stage
    if not stage:
        while True:
            selection = input(
                "파이프라인 선택 (1. 크롤링 / 2. 분석 / 3. 댓글 학습): "
            ).strip()
            if selection in {"1", "crawl"}:
                stage = "crawl"
                break
            if selection in {"2", "analysis"}:
                stage = "analysis"
                break
            if selection in {"3", "comment-training"}:
                stage = "comment-training"
                break
            print(
                "오류: 허용되지 않는 선택입니다. "
                "1, 2, 3 또는 crawl/analysis/comment-training 중에서 선택하세요."
            )

    db_path = Path(args.db_path) if args.db_path else None
    started_at = datetime.now(timezone.utc).isoformat()
    print(f"선택된 실행 단계: {stage}")
    if stage == "crawl":
        results = collect_archived_audio(channel_url, db_path=db_path)
    elif stage == "comment-training":
        results = collect_archived_comment_training(channel_url, db_path=db_path)
    else:
        results = process_channel(channel_url, db_path=db_path)
    payload = {
        "requested_at": started_at,
        "channel_url": channel_url,
        "stage": stage,
        "outputs": results,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
