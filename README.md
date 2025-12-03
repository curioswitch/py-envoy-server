# envoy-server

A Python package containing a runnable [Envoy](https://github.com/envoyproxy/envoy) command.

On platforms supported natively by Envoy, typically glibc Linux or macOS on arm64, the package
embeds the Envoy binary itself and runs it directly. On other platforms such as Windows, it runs
the official [Envoy docker image](https://hub.docker.com/r/envoyproxy/envoy) - Docker must be installed
to run. The Docker fallback is primarily meant for non-production usage, for example when your
project runs Envoy on Linux in production but should still be runnable on a Windows developer
machine.

Note, this package is for Python users. If you're not already using Python, you may want to try
[func-e](https://github.com/tetratelabs/func-e/) instead.

## Usage

```bash
uv add envoy-server # or pip install
```

The package defines a script named `envoy` which will be available on the `PATH` as normal and can
then be run as you need.

```bash
uv run envoy --version # or just envoy if in the system Python or an activated virtualenv
```

If you just want to run Envoy on a machine with `uv` (or `pipx`, etc) available without a project to
add to, you can.

```bash
uvx --from envoy-server envoy --version
```

The path to the actual Envoy binary can be found with `get_envoy_path`. Note, this will not be available
on Windows or other unsupported Envoy platforms and looking up `envoy` on `PATH` is recommended when
supporting such platforms.

```python
import subprocess

from envoy import get_envoy_path

subprocess.run([get_envoy_path(), "--version"], check=True)
```
