from __future__ import annotations

import os
import sys

from ._envoy import get_envoy_path


def main() -> None:
    envoy = get_envoy_path()
    os.execv(envoy, sys.argv)  # noqa: S606


if __name__ == "__main__":
    main()
