"""Song segment detection using basic energy heuristics."""

from __future__ import annotations

from typing import List, Optional
import wave
import audioop
import importlib
import importlib.util
from pathlib import Path
import shutil

from worker.audio.extract import AudioAsset
from worker.audio.vocal import separate_vocals
from worker.models import SongSegment


def detect_song_segments(
    audio_path: str,
    min_song_prob: float = 0.55,
    merge_gap_sec: float = 3.0,
    model_weight: float = 0.6,
    rms_weight: float = 0.25,
    label_weight: float = 0.15,
    merge_confidence_threshold: float = 0.7,
    merge_confidence_bonus_sec: float = 2.0,
) -> List[SongSegment]:
    if not Path(audio_path).exists():
        return []
    frame_rate, rms_values = _read_rms_values(audio_path)

    if not rms_values:
        return []

    rms_list = [value for _, value in rms_values]
    median_rms = sorted(rms_list)[len(rms_list) // 2]
    threshold = max(100, int(median_rms * 1.4))
    max_rms = max(rms_list) or 1
    labels = _classify_audio_segments(audio_path, len(rms_values))
    svd_scores = _compute_svd_scores(audio_path, len(rms_values), frame_rate)

    song_probs: list[float] = []
    confidence_scores: list[float] = []
    for index, rms in rms_values:
        rms_score = rms / max_rms
        label_score = _label_score(labels[index]) if labels else 1.0
        if rms < threshold:
            rms_score *= 0.5
        if svd_scores is not None:
            model_score = svd_scores[index]
            combined = model_weight * model_score + rms_weight * rms_score + label_weight * label_score
            song_probs.append(min(1.0, combined))
            confidence_scores.append(model_score)
        else:
            song_probs.append(min(1.0, 0.6 * rms_score + 0.4 * label_score))
            confidence_scores.append(song_probs[-1])

    raw_segments = _segments_from_probs(song_probs, min_song_prob)
    merged_segments, merged_confidences = _merge_segments(
        raw_segments,
        merge_gap_sec,
        confidence_scores,
        merge_confidence_threshold,
        merge_confidence_bonus_sec,
    )
    return [
        _build_segment(start, end, song_probs, confidence)
        for (start, end), confidence in zip(merged_segments, merged_confidences, strict=True)
    ]


def filter_short_segments(
    segments: List[SongSegment], min_duration: float = 60.0, min_confidence: float = 0.6
) -> List[SongSegment]:
    return [
        segment
        for segment in segments
        if segment.duration_sec >= min_duration or segment.confidence >= min_confidence
    ]


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


def _merge_segments(
    segments: list[tuple[int, int]],
    merge_gap_sec: float,
    confidence_scores: list[float],
    merge_confidence_threshold: float,
    merge_confidence_bonus_sec: float,
) -> tuple[list[tuple[int, int]], list[float]]:
    if not segments:
        return ([], [])
    merged = [segments[0]]
    merged_confidences = [_average_score(confidence_scores, segments[0])]
    for start, end in segments[1:]:
        prev_start, prev_end = merged[-1]
        prev_confidence = merged_confidences[-1]
        current_confidence = _average_score(confidence_scores, (start, end))
        gap = start - prev_end
        allowed_gap = merge_gap_sec
        if min(prev_confidence, current_confidence) >= merge_confidence_threshold:
            allowed_gap += merge_confidence_bonus_sec
        if gap <= allowed_gap:
            merged[-1] = (prev_start, end)
            merged_confidences[-1] = _average_score(confidence_scores, (prev_start, end))
        else:
            merged.append((start, end))
            merged_confidences.append(current_confidence)
    return merged, merged_confidences


def _build_segment(start_sec: int, end_sec: int, song_probs: List[float], confidence: float) -> SongSegment:
    segment_probs = song_probs[start_sec:end_sec] or [0.0]
    average_prob = sum(segment_probs) / len(segment_probs)
    blended_confidence = (average_prob + confidence) / 2
    adjusted_confidence = min(0.99, max(0.5, blended_confidence))
    return SongSegment(
        start_sec=float(start_sec), end_sec=float(end_sec), confidence=round(adjusted_confidence, 2)
    )


def _average_score(scores: list[float], segment: tuple[int, int]) -> float:
    start, end = segment
    segment_scores = scores[start:end] or [0.0]
    return sum(segment_scores) / len(segment_scores)


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


def _read_rms_values(audio_path: str) -> tuple[int, list[tuple[int, int]]]:
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
    return frame_rate, rms_values


def _compute_svd_scores(audio_path: str, total_seconds: int, sample_rate: int) -> Optional[list[float]]:
    custom_scores = _compute_custom_svd_scores(audio_path, total_seconds)
    if custom_scores is not None:
        return custom_scores
    pyannote_scores = _compute_pyannote_scores(audio_path, total_seconds)
    if pyannote_scores is not None:
        return pyannote_scores
    return _compute_vocal_activity_scores(audio_path, total_seconds, sample_rate)


def _compute_custom_svd_scores(audio_path: str, total_seconds: int) -> Optional[list[float]]:
    if importlib.util.find_spec("svd_model") is None:
        return None
    model_module = importlib.import_module("svd_model")
    if not hasattr(model_module, "predict"):
        return None
    try:
        scores = model_module.predict(audio_path)
    except Exception:
        return None
    return _normalize_scores(scores, total_seconds)


def _compute_pyannote_scores(audio_path: str, total_seconds: int) -> Optional[list[float]]:
    if importlib.util.find_spec("pyannote.audio") is None:
        return None
    pyannote_module = importlib.import_module("pyannote.audio")
    pipeline_cls = getattr(pyannote_module, "Pipeline", None)
    if pipeline_cls is None:
        return None
    try:
        pipeline = pipeline_cls.from_pretrained("pyannote/voice-activity-detection")
    except Exception:
        return None
    try:
        vad = pipeline(audio_path)
    except Exception:
        return None
    scores = [0.0] * total_seconds
    try:
        timeline = vad.get_timeline().support()
    except AttributeError:
        timeline = vad.get_timeline()
    for segment in timeline:
        start = int(getattr(segment, "start", 0))
        end = int(getattr(segment, "end", 0))
        for index in range(start, min(end, total_seconds)):
            scores[index] = 1.0
    return scores


def _compute_vocal_activity_scores(
    audio_path: str, total_seconds: int, sample_rate: int
) -> Optional[list[float]]:
    if not _vocal_activity_backend_available():
        return None
    audio_asset = AudioAsset(path=audio_path, sample_rate=sample_rate)
    vocal_stem = separate_vocals(audio_asset)
    if not Path(vocal_stem.path).exists():
        return None
    _, vocal_rms_values = _read_rms_values(vocal_stem.path)
    vocal_scores = [value for _, value in vocal_rms_values]
    return _normalize_scores(vocal_scores, total_seconds)


def _normalize_scores(scores: list[float], total_seconds: int) -> list[float]:
    if not scores:
        return [0.0] * total_seconds
    max_score = max(scores) or 1.0
    normalized = [min(1.0, score / max_score) for score in scores]
    if len(normalized) >= total_seconds:
        return normalized[:total_seconds]
    return normalized + [0.0] * (total_seconds - len(normalized))


def _vocal_activity_backend_available() -> bool:
    return shutil.which("demucs") is not None
