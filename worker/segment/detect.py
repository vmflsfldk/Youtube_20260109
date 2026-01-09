"""Song segment detection using basic energy heuristics."""

from __future__ import annotations

from typing import List, Optional
import wave
import audioop
import importlib
import importlib.util
from pathlib import Path

from worker.models import SongSegment


def detect_song_segments(
    audio_path: str,
    min_song_prob: float = 0.55,
    merge_gap_sec: float = 3.0,
) -> List[SongSegment]:
    if not Path(audio_path).exists():
        return []
    with wave.open(audio_path, "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        window_size = frame_rate
        rms_values = []
        window_index = 0
        while True:
            frames = wav_file.readframes(window_size)
            if not frames:
                break
            if channels > 1:
                frames = audioop.tomono(frames, sample_width, 0.5, 0.5)
            rms = audioop.rms(frames, sample_width)
            rms_values.append((window_index, rms))
            window_index += 1

    if not rms_values:
        return []

    rms_list = [value for _, value in rms_values]
    median_rms = sorted(rms_list)[len(rms_list) // 2]
    threshold = max(100, int(median_rms * 1.4))
    max_rms = max(rms_list) or 1
    labels = _classify_audio_segments(audio_path, len(rms_values))

    song_probs: list[float] = []
    for index, rms in rms_values:
        rms_score = rms / max_rms
        label_score = _label_score(labels[index]) if labels else 1.0
        if rms < threshold:
            rms_score *= 0.5
        song_probs.append(min(1.0, 0.6 * rms_score + 0.4 * label_score))

    raw_segments = _segments_from_probs(song_probs, min_song_prob)
    merged_segments = _merge_segments(raw_segments, merge_gap_sec)
    return [_build_segment(start, end, song_probs) for start, end in merged_segments]


def filter_short_segments(segments: List[SongSegment], min_duration: float = 60.0) -> List[SongSegment]:
    return [segment for segment in segments if segment.duration_sec >= min_duration]


def _segments_from_probs(song_probs: List[float], min_song_prob: float) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    current_start: Optional[int] = None
    for index, prob in enumerate(song_probs):
        if prob >= min_song_prob:
            if current_start is None:
                current_start = index
        else:
            if current_start is not None:
                segments.append((current_start, index))
                current_start = None
    if current_start is not None:
        segments.append((current_start, len(song_probs)))
    return segments


def _merge_segments(segments: list[tuple[int, int]], merge_gap_sec: float) -> list[tuple[int, int]]:
    if not segments:
        return []
    merged = [segments[0]]
    for start, end in segments[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= merge_gap_sec:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged


def _build_segment(start_sec: int, end_sec: int, song_probs: List[float]) -> SongSegment:
    segment_probs = song_probs[start_sec:end_sec] or [0.0]
    average_prob = sum(segment_probs) / len(segment_probs)
    confidence = min(0.99, max(0.5, average_prob))
    return SongSegment(start_sec=float(start_sec), end_sec=float(end_sec), confidence=round(confidence, 2))


def _classify_audio_segments(audio_path: str, total_seconds: int) -> Optional[List[Optional[str]]]:
    if importlib.util.find_spec("inaSpeechSegmenter") is None:
        return None

    segmenter_module = importlib.import_module("inaSpeechSegmenter")
    segmenter = segmenter_module.Segmenter()
    labels = [None] * total_seconds
    for label, start, end in segmenter(audio_path):
        label_name = _normalize_label(label)
        for index in range(int(start), min(int(end), total_seconds)):
            labels[index] = label_name
    return labels


def _normalize_label(label: str) -> str:
    lowered = label.lower()
    if "music" in lowered:
        return "music"
    if lowered in {"speech", "male", "female"}:
        return "speech"
    return "noise"


def _label_score(label: Optional[str]) -> float:
    if label == "music":
        return 1.0
    if label == "speech":
        return 0.3
    if label == "noise":
        return 0.1
    return 0.5
