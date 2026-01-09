"""Vocal separation stub."""

from __future__ import annotations

from dataclasses import dataclass

from worker.audio.extract import AudioAsset


@dataclass(frozen=True)
class VocalStem:
    path: str
    source_audio: str


def separate_vocals(audio: AudioAsset) -> VocalStem:
    return VocalStem(path=audio.path.replace(".wav", "_vocals.wav"), source_audio=audio.path)
