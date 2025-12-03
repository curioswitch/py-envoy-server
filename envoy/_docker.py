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
    envs: list[str] = []

    paths, envoy_args = parser.parse_known_args(namespace=EnvoyArgs())
    _handle_path_arg(
        "admin-address-path", paths.admin_address_path, volume_mounts, envoy_args
    )
    _handle_path_arg("base-id-path", paths.base_id_path, volume_mounts, envoy_args)
    _handle_path_arg("config-path", paths.config_path, volume_mounts, envoy_args)
    _handle_path_arg("log-path", paths.log_path, volume_mounts, envoy_args)
    _handle_path_arg("socket-path", paths.socket_path, volume_mounts, envoy_args)

    for key, value in os.environ.items():
        # Skip Docker automatic variables
        if key in ("HOME", "HOSTNAME", "PATH", "TERM"):
            continue
        # Transform paths in well-known variables, including for pyvoy.
        if key in (
            "ENVOY_DYNAMIC_MODULES_SEARCH_PATH",
            "LD_PRELOAD",
            "LD_LIBRARY_PATH",
        ):
            _handle_path_env(key, value, volume_mounts, envs)
        else:
            # We generally want the envoy in Docker to behave as close to a native one as
            # possible. Many of these will still be set to bogus host values, but let's
            # see how well this approach does.
            envs.extend(["-e", f"{key}"])

    version = metadata.version("envoy-server")
    if (post_idx := version.find(".post")) >= 0:
        version = version[:post_idx]

    # As this is almost always used for development, we should go ahead and mount the current
    # directory.
    workdir = _mount_path(Path.cwd(), volume_mounts)

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "host",
        "-w",
        workdir,
        *volume_mounts,
        *envs,
        os.environ.get(
            "ENVOY_SERVER_DOCKER_IMAGE", f"envoyproxy/envoy:distroless-v{version}"
        ),
        *envoy_args,
    ]
    os.execv(docker_path, docker_cmd)  # noqa: S606


def _handle_path_arg(
    arg_name: str, path_str: str | None, volume_mounts: list[str], args: list[str]
) -> None:
    if not path_str:
        return

    mounted_path = _mount_path(Path(path_str).resolve(), volume_mounts)
    args.extend([f"--{arg_name}", mounted_path])


def _handle_path_env(
    env_name: str, path_str: str | None, volume_mounts: list[str], envs: list[str]
) -> None:
    if not path_str:
        return

    mounted_path = _mount_path(Path(path_str).resolve(), volume_mounts)
    envs.extend(["-e", f"{env_name}={mounted_path}"])


def _mount_path(path: Path, volume_mounts: list[str]) -> str:
    parent_dir = path if path.is_dir() else path.parent

    if os.sep == "/":
        # Unix-like, we can use the same path inside Docker.
        volume_mounts.append(f"-v{parent_dir}:{parent_dir}:rw")
        return str(path)
    # Windows, we need to convert to /c/ style path.
    # parent_dir.drive is 'C:', 'D:', etc. - always a string ending in exactly one colon
    drive_letter = parent_dir.drive[:-1].lower()
    # Skip the drive and convert
    rel_parts = parent_dir.parts[1:]
    wsl_dir = (
        f"/mnt/{drive_letter}/{'/'.join(rel_parts)}"
        if rel_parts
        else f"/mnt/{drive_letter}"
    )

    docker_path = wsl_dir if path.is_dir() else f"{wsl_dir}/{path.name}"

    # It should be fine using the wsl directory corresponding to the Windows folder
    # for the host side to support vanilla docker. Docker Desktop would also allow
    # using native paths, and while it may be commonly used, we can't really use it
    # in CI - this should work with either.
    volume_mounts.append(f"-v{wsl_dir}:{wsl_dir}:rw")
    return docker_path
