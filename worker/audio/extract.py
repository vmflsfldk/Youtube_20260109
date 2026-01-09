"""Audio extraction and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import Optional

from worker.models import Video
from worker.ytdlp_runtime import js_runtime_cli_args


@dataclass(frozen=True)
class AudioAsset:
    path: str
    sample_rate: int


def extract_audio(video: Video, target_rate: int = 44100) -> AudioAsset:
    output_dir = Path("audio")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video.video_id}.wav"

    if output_path.exists():
        _validate_audio_duration(output_path, expected_duration=video.duration_sec)
        return AudioAsset(path=str(output_path), sample_rate=target_rate)

    source = f"https://www.youtube.com/watch?v={video.video_id}"
    if not _ffmpeg_available():
        raise AudioExtractionError("ffmpeg is required to extract audio but was not found.")
    if not _ytdlp_available():
        raise AudioExtractionError("yt-dlp is required to extract audio but was not found.")

    logger = logging.getLogger(__name__)
    try:
        _extract_with_ytdlp_pipe(source, output_path, target_rate)
    except AudioExtractionError as exc:
        logger.warning("yt-dlp piping failed, retrying with download fallback: %s", exc)
        _extract_with_ytdlp_download(source, output_path, target_rate)

    duration = _validate_audio_duration(output_path, expected_duration=video.duration_sec)
    logger.info(
        "Extracted audio for video %s duration %.2fs (expected %.2fs).",
        video.video_id,
        duration,
        float(video.duration_sec),
    )

    return AudioAsset(path=str(output_path), sample_rate=target_rate)


class AudioExtractionError(RuntimeError):
    pass


def _extract_with_ytdlp_pipe(source: str, output_path: Path, target_rate: int) -> None:
    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        "bestaudio",
        "-o",
        "-",
        *js_runtime_cli_args(),
        source,
    ]
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(target_rate),
        "-ac",
        "1",
        str(output_path),
    ]
    ytdlp_log = tempfile.NamedTemporaryFile(delete=False, suffix=".ytdlp.log", dir=output_path.parent)
    ytdlp_log_path = Path(ytdlp_log.name)
    ytdlp_log.close()
    ytdlp_err: bytes | None = None
    ffmpeg_err: bytes | None = None
    try:
        with ytdlp_log_path.open("wb") as ytdlp_log_file:
            with subprocess.Popen(
                ytdlp_cmd,
                stdout=subprocess.PIPE,
                stderr=ytdlp_log_file,
            ) as ytdlp_proc:
                with subprocess.Popen(
                    ffmpeg_cmd,
                    stdin=ytdlp_proc.stdout,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ) as ffmpeg_proc:
                    if ytdlp_proc.stdout:
                        ytdlp_proc.stdout.close()
                    _, ffmpeg_err = ffmpeg_proc.communicate()
                ytdlp_proc.wait()
            ytdlp_err = ytdlp_log_path.read_bytes()
    finally:
        if ytdlp_log_path.exists():
            ytdlp_log_path.unlink()

    if ytdlp_proc.returncode != 0 or ffmpeg_proc.returncode != 0:
        raise AudioExtractionError(
            "yt-dlp pipe extraction failed "
            f"(yt-dlp={ytdlp_proc.returncode}, ffmpeg={ffmpeg_proc.returncode}): "
            f"{_format_errors(ytdlp_err, ffmpeg_err)}"
        )


def _extract_with_ytdlp_download(source: str, output_path: Path, target_rate: int) -> None:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".audio", dir=output_path.parent)
    temp_path = Path(temp_file.name)
    temp_file.close()
    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f",
        "bestaudio",
        "-o",
        str(temp_path),
        *js_runtime_cli_args(),
        source,
    ]
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(temp_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(target_rate),
        "-ac",
        "1",
        str(output_path),
    ]
    try:
        result = subprocess.run(ytdlp_cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise AudioExtractionError(
                f"yt-dlp download failed (code={result.returncode}): {result.stderr.strip()}"
            )
        ffmpeg = subprocess.run(ffmpeg_cmd, check=False, capture_output=True, text=True)
        if ffmpeg.returncode != 0:
            raise AudioExtractionError(
                f"ffmpeg conversion failed (code={ffmpeg.returncode}): {ffmpeg.stderr.strip()}"
            )
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _ffmpeg_available() -> bool:
    return _which("ffmpeg") is not None


def _ytdlp_available() -> bool:
    return _which("yt-dlp") is not None


def _which(command: str) -> Optional[str]:
    import shutil

    return shutil.which(command)


def _validate_audio_duration(output_path: Path, expected_duration: int | float) -> float:
    duration = _probe_duration(output_path)
    if duration <= 0:
        raise AudioExtractionError(f"Audio duration invalid for {output_path}.")
    if expected_duration:
        diff = abs(duration - float(expected_duration))
        if diff > max(5.0, float(expected_duration) * 0.1):
            logging.getLogger(__name__).warning(
                "Audio duration mismatch for %s (expected %.2fs, got %.2fs).",
                output_path,
                float(expected_duration),
                duration,
            )
    return duration


def _probe_duration(output_path: Path) -> float:
    if _which("ffprobe"):
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(output_path),
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            value = result.stdout.strip()
            try:
                return float(value)
            except ValueError:
                logging.getLogger(__name__).warning("ffprobe duration parse failed: %s", value)
    return _probe_wave_duration(output_path)


def _probe_wave_duration(output_path: Path) -> float:
    import wave

    with wave.open(str(output_path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate() or 1
    return frames / rate


def _format_errors(ytdlp_err: bytes | None, ffmpeg_err: bytes | None) -> str:
    messages = []
    if ytdlp_err:
        messages.append(ytdlp_err.decode(errors="ignore").strip())
    if ffmpeg_err:
        messages.append(ffmpeg_err.decode(errors="ignore").strip())
    return " | ".join(message for message in messages if message)
