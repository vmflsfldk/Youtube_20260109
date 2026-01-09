"""Song segment detection using basic energy heuristics."""

from __future__ import annotations

from typing import List
import wave
import audioop
from pathlib import Path

from worker.models import SongSegment


def detect_song_segments(audio_path: str) -> List[SongSegment]:
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

    segments: list[SongSegment] = []
    current_start = None
    max_rms = max(rms_list) or 1
    for index, rms in rms_values:
        time_sec = index
        if rms >= threshold:
            if current_start is None:
                current_start = time_sec
        else:
            if current_start is not None:
                segments.append(
                    _build_segment(current_start, time_sec, rms_list, max_rms)
                )
                current_start = None
    if current_start is not None:
        segments.append(_build_segment(current_start, len(rms_values), rms_list, max_rms))
    return segments


def filter_short_segments(segments: List[SongSegment], min_duration: float = 60.0) -> List[SongSegment]:
    return [segment for segment in segments if segment.duration_sec >= min_duration]


def _build_segment(start_sec: int, end_sec: int, rms_values: List[int], max_rms: int) -> SongSegment:
    segment_rms = rms_values[start_sec:end_sec] or [0]
    average_rms = sum(segment_rms) / len(segment_rms)
    confidence = min(0.99, max(0.5, average_rms / max_rms))
    return SongSegment(start_sec=float(start_sec), end_sec=float(end_sec), confidence=round(confidence, 2))
