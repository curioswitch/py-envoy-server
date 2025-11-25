from __future__ import annotations

import argparse
import os
import shutil
from importlib import metadata
from pathlib import Path


class EnvoyArgs:
    """Subset of Envoy arguments pointing to filesystem paths we need to mount in Docker."""

    config_path: str
    admin_address_path: str
    base_id_path: str
    log_path: str
    socket_path: str


def run_with_docker() -> None:
    """Runs Envoy using Docker, for platforms not natively supported such as Windows.

    This is meant to allow executing Envoy, not to isolate it, so we keep networking
    simplest by using host networking without port mapping and mounting any referenced
    paths rw.
    """

    docker_path = shutil.which("docker")
    if not docker_path:
        msg = (
            "This platform requires Docker to run Envoy, but Docker could not be found. "
            "Ensure it is installed and available."
        )
        raise RuntimeError(msg)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config-path", type=str, default="")
    parser.add_argument("--admin-address-path", type=str, default="")
    parser.add_argument("--base-id-path", type=str, default="")
    parser.add_argument("--log-path", type=str, default="")
    parser.add_argument("--socket-path", type=str, default="")

    volume_mounts: list[str] = []

    paths, envoy_args = parser.parse_known_args(namespace=EnvoyArgs())
    if paths.admin_address_path:
        _handle_path(
            "admin-address-path", paths.admin_address_path, volume_mounts, envoy_args
        )
    if paths.base_id_path:
        _handle_path("base-id-path", paths.base_id_path, volume_mounts, envoy_args)
    if paths.config_path:
        _handle_path("config-path", paths.config_path, volume_mounts, envoy_args)
    if paths.log_path:
        _handle_path("log-path", paths.log_path, volume_mounts, envoy_args)
    if paths.socket_path:
        _handle_path("socket-path", paths.socket_path, volume_mounts, envoy_args)

    version = metadata.version("envoy-server")
    if (post_idx := version.find(".post")) >= 0:
        version = version[:post_idx]

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "host",
        *volume_mounts,
        f"envoyproxy/envoy:distroless-v{version}",
        *envoy_args,
    ]
    os.execv(docker_path, docker_cmd)  # noqa: S606


def _handle_path(
    arg_name: str, path_str: str | None, volume_mounts: list[str], args: list[str]
) -> None:
    if not path_str:
        return

    path = Path(path_str).resolve()

    # All of these should be files but it doesn't hurt to handle dir.
    parent_dir = path if path.is_dir() else path.parent

    if os.sep == "/":
        # Unix-like, we can use the same path inside Docker.
        args.extend([f"--{arg_name}", str(path)])
        volume_mounts.append(f"-v{parent_dir}:{parent_dir}:rw")
    else:
        # Windows, we need to convert to /c/ style path.
        # parent_dir.drive is 'C:', 'D:', etc. - always a string ending in exactly one colon
        drive_letter = parent_dir.drive[:-1].lower()
        # Skip the drive and convert
        rel_parts = parent_dir.parts[1:]
        docker_dir = (
            f"/{drive_letter}/{'/'.join(rel_parts)}"
            if rel_parts
            else f"/{drive_letter}"
        )

        docker_path = docker_dir if path.is_dir() else f"{docker_dir}/{path.name}"

        args.extend([f"--{arg_name}", docker_path])
        volume_mounts.append(f"-v{parent_dir}:{docker_dir}:rw")
