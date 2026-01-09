"""ASR transcription stub."""

from __future__ import annotations

from dataclasses import dataclass

from worker.models import SongSegment


@dataclass(frozen=True)
class Transcript:
    segment: SongSegment
    text: str


def transcribe_segment(segment: SongSegment) -> Transcript:
    return Transcript(segment=segment, text="샘플 가사 텍스트")
