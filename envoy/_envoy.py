from __future__ import annotations

from pathlib import Path


def get_envoy_path() -> Path:
    return Path(__file__).parent / "_bin" / "envoy"
