"""Shared helpers for yt-dlp JavaScript runtime configuration."""

from __future__ import annotations

from typing import Any


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
    node_path = _which("node")
    if node_path:
        return "node", node_path
    deno_path = _which("deno")
    if deno_path:
        return "deno", deno_path
    return None


def _which(command: str) -> str | None:
    import shutil

    return shutil.which(command)
