"""Audio matching using segment embeddings."""

from __future__ import annotations

from array import array
import importlib
import importlib.util
import math
from typing import Iterable, List, Sequence

from worker.matching.catalog import get_catalog_index
from worker.models import SongCandidate


def audio_match(
    audio_path: str,
    start_sec: float,
    end_sec: float,
    *,
    confidence: float | None = None,
) -> List[SongCandidate]:
    confidence = 0.8 if confidence is None else confidence
    segment_embedding = _extract_segment_embedding(audio_path, start_sec, end_sec)
    index = get_catalog_index()
    if not index.songs:
        return []
    candidates: list[SongCandidate] = []
    for position, song in enumerate(index.songs):
        embedding_score = None
        if segment_embedding is not None and song.embedding:
            embedding_score = _cosine_similarity(segment_embedding, song.embedding)
        if embedding_score is None:
            score = _fallback_score(start_sec, end_sec, confidence, position)
            method = "audio-fallback"
        else:
            score = _embedding_score(embedding_score, confidence)
            method = "audio-embedding"
        candidates.append(
            SongCandidate(
                song_id=song.song_id,
                title=song.title,
                original_artist=song.original_artist,
                match_score=round(score, 2),
                method=method,
            )
        )
    candidates.sort(key=lambda item: item.match_score, reverse=True)
    return candidates


def _extract_segment_embedding(
    audio_path: str,
    start_sec: float,
    end_sec: float,
) -> tuple[float, ...] | None:
    segment = _read_audio_segment(audio_path, start_sec, end_sec)
    if segment is None:
        return None
    samples, sample_rate = segment
    module = _load_chromaprint()
    if module is None:
        return None
    return _chromaprint_embedding(module, samples, sample_rate)


def _read_audio_segment(
    audio_path: str,
    start_sec: float,
    end_sec: float,
) -> tuple[array, int] | None:
    import wave

    if end_sec <= start_sec:
        return None
    with wave.open(audio_path, "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        if sample_width != 2:
            return None
        start_frame = int(start_sec * frame_rate)
        end_frame = int(end_sec * frame_rate)
        total_frames = wav_file.getnframes()
        if start_frame >= total_frames:
            return None
        wav_file.setpos(max(0, min(start_frame, total_frames - 1)))
        frames_to_read = max(0, min(end_frame, total_frames) - wav_file.tell())
        raw_frames = wav_file.readframes(frames_to_read)
    samples = array("h")
    samples.frombytes(raw_frames)
    if channels > 1:
        samples = array("h", samples[::channels])
    return samples, frame_rate


def _load_chromaprint() -> object | None:
    spec = importlib.util.find_spec("chromaprint")
    if spec is None:
        return None
    return importlib.import_module("chromaprint")


def _chromaprint_embedding(
    module: object,
    samples: array,
    sample_rate: int,
) -> tuple[float, ...] | None:
    fingerprint: Iterable[int] | str | None = None
    if hasattr(module, "Fingerprinter"):
        fingerprinter = module.Fingerprinter(sample_rate, 1)
        fingerprinter.start()
        fingerprinter.feed(samples.tobytes())
        fingerprinter.finish()
        fingerprint = fingerprinter.fingerprint
    elif hasattr(module, "generate_fingerprint"):
        fingerprint_data = module.generate_fingerprint(samples.tobytes(), sample_rate)
        if isinstance(fingerprint_data, tuple):
            fingerprint = fingerprint_data[0]
        else:
            fingerprint = fingerprint_data
    if fingerprint is None:
        return None
    return _hash_to_embedding(fingerprint, target_dim=8)


def _hash_to_embedding(fingerprint: Iterable[int] | str, target_dim: int) -> tuple[float, ...]:
    if isinstance(fingerprint, str):
        data = fingerprint.encode("utf-8")
    else:
        data = bytes(int(value) & 0xFF for value in fingerprint)
    if not data:
        return tuple(0.0 for _ in range(target_dim))
    totals = [0] * target_dim
    for idx, value in enumerate(data):
        totals[idx % target_dim] += value
    max_value = max(totals) or 1
    return tuple(round(total / max_value, 4) for total in totals)


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    score = dot / (left_norm * right_norm)
    return max(0.0, min(1.0, score))


def _embedding_score(similarity: float, confidence: float) -> float:
    scaled = similarity * (0.7 + (confidence * 0.3))
    return max(0.0, min(0.99, scaled))


def _fallback_score(start_sec: float, end_sec: float, confidence: float, index: int) -> float:
    duration = max(0.0, end_sec - start_sec)
    duration_factor = min(1.0, duration / 240.0)
    base = 0.6 + (confidence * 0.2) + (duration_factor * 0.2)
    offset = (index + int(start_sec) % 3) * 0.03
    return max(0.0, min(0.99, base - offset))
