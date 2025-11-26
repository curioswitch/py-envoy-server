from __future__ import annotations

import contextlib
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import cast

import httpx


def test_runs():
    envoy_path = shutil.which("envoy")
    assert envoy_path is not None, "Envoy binary not found in PATH"
    assert ".venv" in envoy_path, "Envoy binary is not from the virtual environment"

    config_path = Path(__file__).parent / "config" / "envoy-conf.yaml"
    # admin_address_file will always be an absolute path, and we check relative path here
    config_path = config_path.relative_to(Path.cwd())

    with NamedTemporaryFile("r") as admin_address_file:
        process = None

        def run_envoy():
            nonlocal process
            process = subprocess.Popen(
                [
                    envoy_path,
                    "-c",
                    str(config_path),
                    "--admin-address-path",
                    admin_address_file.name,
                    "--log-level",
                    "error",
                ],
                text=True,
            )

        thread = threading.Thread(target=run_envoy, daemon=True)
        thread.start()
        port = None
        process = cast("subprocess.Popen | None", process)
        for _ in range(100):
            if process is None:
                time.sleep(0.1)
                continue
            assert process.returncode is None, "Envoy process exited prematurely"
            with contextlib.suppress(Exception):
                try:
                    admin_address = Path(admin_address_file.name).read_text()
                except Exception:
                    print(  # noqa: T201
                        "Waiting for admin address file to be populated",
                        file=sys.stderr,
                    )
                    admin_address = None
                if admin_address:
                    response = httpx.get(
                        f"http://{admin_address}/listeners?format=json"
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    socket_address = response_data["listener_statuses"][0][
                        "local_address"
                    ]["socket_address"]
                    port = socket_address["port_value"]
                    break
            time.sleep(0.1)
        assert port is not None, "Failed to get admin port from Envoy"

    response = httpx.get(f"http://127.0.0.1:{port}/hello")
    response.raise_for_status()
    assert response.text == "Hello Python"
    assert process is not None
    process.terminate()
    process.wait()
    thread.join()
