from __future__ import annotations

import os
import sys

from ._docker import run_with_docker
from ._envoy import get_envoy_path


def main() -> None:
    envoy = get_envoy_path()
    if not envoy.exists() or os.environ.get("ENVOY_SERVER_USE_DOCKER") == "true":
        run_with_docker()
        return
    os.execv(envoy, sys.argv)  # noqa: S606


if __name__ == "__main__":
    main()
