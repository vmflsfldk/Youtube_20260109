"""Vocal separation helper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Optional

from worker.audio.extract import AudioAsset


@dataclass(frozen=True)
class VocalStem:
    path: str
    source_audio: str


def separate_vocals(audio: AudioAsset) -> VocalStem:
    output_path = Path(audio.path).with_suffix("").with_name(f"{Path(audio.path).stem}_vocals.wav")
    if output_path.exists():
        return VocalStem(path=str(output_path), source_audio=audio.path)

    if _demucs_available():
        _run_demucs(audio.path, output_path.parent)
        if output_path.exists():
            return VocalStem(path=str(output_path), source_audio=audio.path)

    output_path.write_bytes(Path(audio.path).read_bytes())
    return VocalStem(path=str(output_path), source_audio=audio.path)


def _demucs_available() -> bool:
    return _which("demucs") is not None


def _run_demucs(audio_path: str, output_dir: Path) -> None:
    cmd = ["demucs", "--two-stems", "vocals", "-o", str(output_dir), audio_path]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _which(command: str) -> Optional[str]:
    import shutil

    return shutil.which(command)
