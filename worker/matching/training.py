"""Training helpers for comment-derived labels."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from worker.audio.extract import AudioAsset
from worker.matching.audio_match import audio_match
from worker.models import SongSegment, TimestampedComment, TrainingSample


def build_training_samples(
    audio: AudioAsset,
    comments: Iterable[TimestampedComment],
    window_sec: float = 30.0,
) -> list[TrainingSample]:
    samples: list[TrainingSample] = []
    for comment in comments:
        segment = _segment_from_comment(comment, window_sec)
        candidates = audio_match(
            audio.path,
            segment.start_sec,
            segment.end_sec,
            confidence=segment.confidence,
        )
        best = candidates[0]
        is_match = _normalize(best.title) == _normalize(comment.song_title) and _normalize(
            best.original_artist
        ) == _normalize(comment.original_artist)
        samples.append(
            TrainingSample(
                timestamp_sec=comment.timestamp_sec,
                expected_title=comment.song_title,
                expected_artist=comment.original_artist,
                matched_title=best.title,
                matched_artist=best.original_artist,
                match_score=best.match_score,
                is_match=is_match,
            )
        )
    return samples


def summarize_training(samples: Iterable[TrainingSample]) -> dict[str, float]:
    samples_list = list(samples)
    if not samples_list:
        return {"total": 0.0, "matched": 0.0, "accuracy": 0.0}
    matched = sum(1 for sample in samples_list if sample.is_match)
    total = len(samples_list)
    return {
        "total": float(total),
        "matched": float(matched),
        "accuracy": round(matched / total, 3),
    }


def save_training_samples(video_id: str, samples: Iterable[TrainingSample]) -> str:
    output_dir = Path("training") / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_id}.json"
    payload = [asdict(sample) for sample in samples]
    output_path.write_text(_to_json(payload), encoding="utf-8")
    return str(output_path)


def _segment_from_comment(comment: TimestampedComment, window_sec: float) -> SongSegment:
    start = max(0.0, comment.timestamp_sec - window_sec)
    end = comment.timestamp_sec + window_sec
    return SongSegment(start_sec=start, end_sec=end, confidence=0.85)


def _normalize(text: str) -> str:
    return text.strip().lower()


def _to_json(payload: object) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)
