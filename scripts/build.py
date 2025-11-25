from __future__ import annotations

import subprocess
import sys
import tarfile
import urllib.request
from io import BytesIO
from pathlib import Path
from shutil import copyfileobj

import toml

# Check envoy version minimums and update when needed
MAC_OS_TARGET = "15_0"
GLIBC_TARGET = "2_31"


def main() -> None:
    bin_dir = Path(__file__).parent.parent / "envoy" / "_bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    pyproject = toml.load(Path(__file__).parent.parent / "pyproject.toml")
    version = f"v{pyproject['project']['version']}"
    if (post_idx := version.find(".post")) >= 0:
        version = version[:post_idx]

    for os in ("linux", "darwin"):
        for arch in ("amd64", "arm64"):
            if os == "darwin" and arch == "amd64":
                continue
            match os:
                case "darwin":
                    platform_tag = f"macosx_{MAC_OS_TARGET}_arm64"
                case "linux":
                    match arch:
                        case "amd64":
                            platform_tag = f"manylinux_{GLIBC_TARGET}_x86_64"
                        case "arm64":
                            platform_tag = f"manylinux_{GLIBC_TARGET}_aarch64"

            url = f"https://github.com/tetratelabs/archive-envoy/releases/download/{version}/envoy-{version}-{os}-{arch}.tar.xz"

            envoy_path = bin_dir / "envoy"

            envoy_path.unlink(missing_ok=True)

            with urllib.request.urlopen(url) as response:  # noqa: S310
                archive_bytes = response.read()

            with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:xz") as archive:
                envoy_file = archive.extractfile(
                    f"envoy-{version}-{os}-{arch}/bin/envoy"
                )
                if envoy_file is None:
                    msg = "envoy binary not found in the archive"
                    raise RuntimeError(msg)
                with envoy_path.open("wb") as f:
                    copyfileobj(envoy_file, f)
            envoy_path.chmod(0o755)

            subprocess.run(["uv", "build", "--wheel"], check=True)

            dist_dir = Path(__file__).parent / ".." / "dist"
            built_wheel = next(dist_dir.glob("*-py3-none-any.whl"))

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "wheel",
                    "tags",
                    "--remove",
                    "--platform-tag",
                    platform_tag,
                    built_wheel,
                ],
                check=True,
            )
