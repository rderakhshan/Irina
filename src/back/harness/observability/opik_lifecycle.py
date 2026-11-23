"""Start or reuse the local Opik stack before a run.

Design constraints:

* Reuse a healthy stack. Never restart it just because Irina started.
* Start the stack only when it is not running.
* Recover one time from an unhealthy-but-listening stack, then fail open.
* Never block or fail an Irina run because observability is unavailable.
* Every subprocess call is bounded by a timeout.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

STATE_DIR_NAME = ".irina"
LOCK_NAME = "opik.lock"
LOCK_STALE_SECONDS = 900
DEFAULT_PORT = 5173
DEFAULT_TIMEOUT_SECONDS = 120
PROBE_INTERVAL_SECONDS = 3.0
STOP_TIMEOUT_SECONDS = 180
START_TIMEOUT_SECONDS = 300

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}

# Capture test-runner state at import time. Checking sys.modules later is
# unreliable: routing and ML dependencies import unittest at runtime.
_TEST_RUNNER_AT_IMPORT = "unittest" in sys.modules or "pytest" in sys.modules


@dataclass(frozen=True)
class OpikStatus:
    """Outcome of one local Opik lifecycle attempt."""

    state: str
    url: str
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.state in {"reused", "started"}


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None or not value.strip():
        return default
    lowered = value.strip().lower()
    if lowered in _TRUTHY:
        return True
    if lowered in _FALSY:
        return False
    return default


def opik_home() -> Path | None:
    """Return the directory that contains the Opik checkout's opik.ps1.

    Prefer the checkout at the repository root over any vendored copy deeper
    in the tree (``src/back/opik``), matching the documented start command.
    """
    configured = os.environ.get("IRINA_OPIK_HOME")
    if configured:
        candidate = Path(configured).expanduser()
        return candidate if (candidate / "opik.ps1").is_file() else None
    parents = Path(__file__).resolve().parents
    for parent in parents:
        if not (parent / "pyproject.toml").is_file():
            continue
        candidate = parent / "opik"
        if (candidate / "opik.ps1").is_file():
            return candidate
        break
    for parent in parents:
        candidate = parent / "opik"
        if (candidate / "opik.ps1").is_file():
            return candidate
    return None


def tracing_enabled() -> bool:
    """Return whether Irina should trace to the local Opik stack."""
    if _as_bool(os.environ.get("OPIK_TRACK_DISABLE")):
        return False
    explicit = os.environ.get("IRINA_OPIK_ENABLED")
    if explicit is not None and explicit.strip():
        return _as_bool(explicit)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    if _TEST_RUNNER_AT_IMPORT:
        return False
    return opik_home() is not None


def opik_url() -> str:
    configured = os.environ.get("IRINA_OPIK_URL")
    if configured:
        return configured.rstrip("/")
    port = os.environ.get("IRINA_OPIK_PORT") or str(DEFAULT_PORT)
    return f"http://localhost:{port}/api"


def _state_root() -> Path:
    configured = os.environ.get("IRINA_STATE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / STATE_DIR_NAME).resolve()


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def _ensure_bom(path: Path) -> None:
    """Add a UTF-8 BOM to opik.ps1 once; Windows PowerShell 5.1 needs it."""
    try:
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            return
        path.write_bytes(b"\xef\xbb\xbf" + data)
    except OSError:
        # Read-only or locked checkout: the script may still run, so continue.
        pass


def _powershell() -> str:
    return shutil.which("powershell") or "powershell"


def _run_script(
    script: Path,
    args: list[str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    command = [
        _powershell(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *args,
    ]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _acquire_lock(state_root: Path) -> Path | None:
    """Create the lifecycle lock, or clear a stale one."""
    state_root.mkdir(parents=True, exist_ok=True)
    lock = state_root / LOCK_NAME
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
            except OSError:
                return None
            if age < LOCK_STALE_SECONDS:
                return None
            try:
                lock.unlink()
            except OSError:
                return None
            continue
        except OSError:
            return None
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        return lock
    return None


def _release_lock(lock: Path | None) -> None:
    if lock is None:
        return
    try:
        lock.unlink()
    except OSError:
        pass


def _wait_until_healthy(verify, sleep, timeout: float) -> bool:
    if verify():
        return True
    attempts = max(1, int(timeout / PROBE_INTERVAL_SECONDS))
    for _ in range(attempts):
        sleep(PROBE_INTERVAL_SECONDS)
        if verify():
            return True
    return False


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name) or default)
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name) or default)
    except (TypeError, ValueError):
        return default


def ensure_opik(
    *,
    runner=None,
    port_probe=None,
    verifier=None,
    sleep=time.sleep,
    timeout: float | None = None,
) -> OpikStatus:
    """Reuse or start the local Opik stack without raising.

    Args:
        runner: Injectable ``(script, args, timeout) -> CompletedProcess``.
        port_probe: Injectable ``() -> bool`` that reports the UI port state.
        verifier: Injectable ``() -> bool`` that reports stack health.
        sleep: Injectable sleep function for the health poll.
        timeout: Seconds to wait for the stack to become healthy.

    Returns:
        An :class:`OpikStatus`; failures are reported, never raised.
    """
    if not tracing_enabled():
        return OpikStatus("disabled", opik_url(), "tracing is disabled")

    home = opik_home()
    if home is None:
        return OpikStatus(
            "failed",
            opik_url(),
            "opik.ps1 not found; set IRINA_OPIK_HOME",
        )
    script = home / "opik.ps1"
    if os.name != "nt":
        return OpikStatus(
            "failed",
            opik_url(),
            "the local Opik lifecycle script is Windows-only",
        )

    url = opik_url()
    wait_seconds = (
        timeout
        if timeout is not None
        else _float_env("IRINA_OPIK_START_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)
    )
    port = _int_env("IRINA_OPIK_PORT", DEFAULT_PORT)
    run = runner or _run_script
    probe = port_probe or (lambda: _port_open(port))
    verify = verifier or (
        lambda: run(script, ["--verify"], STOP_TIMEOUT_SECONDS).returncode == 0
    )

    os.environ["OPIK_URL_OVERRIDE"] = url
    os.environ.setdefault("OPIK_PROJECT_NAME", "Irina")
    os.environ.setdefault("OPIK_SUPPRESS_BATCHING_UPDATE_WARNING", "true")
    os.environ.setdefault("OPIK_CONSOLE_LOGGING_LEVEL", "WARNING")

    _ensure_bom(script)

    lock = _acquire_lock(_state_root())
    if lock is None:
        # Another Irina is managing the stack; attach when it becomes healthy.
        if _wait_until_healthy(verify, sleep, wait_seconds):
            return OpikStatus("reused", url, "another instance started the stack")
        return OpikStatus("failed", url, "another instance holds the Opik lock")

    try:
        if verify():
            return OpikStatus("reused", url, "existing stack is healthy")

        if _as_bool(os.environ.get("IRINA_OPIK_RESTART")):
            run(script, ["--stop"], STOP_TIMEOUT_SECONDS)
        elif probe():
            # Listening but unhealthy: one bounded recovery attempt.
            run(script, ["--stop"], STOP_TIMEOUT_SECONDS)

        try:
            started = run(script, [], START_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return OpikStatus("failed", url, "opik start timed out")

        if started.returncode != 0:
            # Docker missing or the script failed: do not wait the full timeout.
            if verify():
                return OpikStatus("started", url, "local stack became healthy")
            tail = (started.stderr or started.stdout or "").strip().splitlines()
            reason = tail[-1] if tail else f"exit code {started.returncode}"
            return OpikStatus("failed", url, f"start failed: {reason}")

        if _wait_until_healthy(verify, sleep, wait_seconds):
            return OpikStatus("started", url, "local stack became healthy")
        return OpikStatus("failed", url, "stack did not become healthy in time")
    except Exception as exc:  # never break a run because of observability
        return OpikStatus("failed", url, f"{type(exc).__name__}: {exc}")
    finally:
        _release_lock(lock)


__all__ = [
    "OpikStatus",
    "ensure_opik",
    "opik_home",
    "opik_url",
    "tracing_enabled",
]
