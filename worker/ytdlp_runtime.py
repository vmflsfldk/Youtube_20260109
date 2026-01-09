"""Shared helpers for yt-dlp JavaScript runtime configuration."""

from __future__ import annotations

import logging
import os
from typing import Any

_warned_no_runtime = False


def js_runtime_cli_args() -> list[str]:
    runtime = _detect_js_runtime()
    if not runtime:
        return []
    name, path = runtime
    return ["--js-runtimes", f"{name}:{path}"]


def js_runtime_options() -> dict[str, dict[str, dict[str, Any]]]:
    runtime = _detect_js_runtime()
    if not runtime:
        return {}
    name, path = runtime
    return {"js_runtimes": {name: {"path": path}}}


def _detect_js_runtime() -> tuple[str, str] | None:
    runtime = _runtime_from_env()
    if runtime:
        return runtime
    node_path = _which("node")
    if node_path:
        return "node", node_path
    deno_path = _which("deno")
    if deno_path:
        return "deno", deno_path
    _log_missing_runtime()
    return None


def _which(command: str) -> str | None:
    import shutil

    return shutil.which(command)


def _runtime_from_env() -> tuple[str, str] | None:
    runtime_value = os.getenv("YTDLP_JS_RUNTIME")
    if runtime_value:
        name, _, path = runtime_value.partition(":")
        if name and path:
            return name, path
        logging.warning(
            "Invalid YTDLP_JS_RUNTIME value %r; expected format is '<name>:<path>'.", runtime_value
        )
    runtime_path = os.getenv("YTDLP_JS_RUNTIME_PATH")
    if runtime_path:
        runtime_name = os.getenv("YTDLP_JS_RUNTIME_NAME", "node")
        return runtime_name, runtime_path
    return None


def _log_missing_runtime() -> None:
    global _warned_no_runtime
    if _warned_no_runtime:
        return
    _warned_no_runtime = True
    logging.warning(
        "yt-dlp JavaScript runtime not found. Install Node.js/Deno or set "
        "YTDLP_JS_RUNTIME='node:/path/to/node' or YTDLP_JS_RUNTIME_PATH."
    )
