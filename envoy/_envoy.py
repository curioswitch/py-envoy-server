from __future__ import annotations

import sys
from pathlib import Path


def get_envoy_path() -> Path:
    exe = "envoy"
    if sys.platform != "win32":
        exe = "envoy"
    else:
        exe = "envoy.dll"
    return Path(__file__).parent / "_bin" / exe
