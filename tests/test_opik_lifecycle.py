"""Tests for the local Opik lifecycle (no Docker required)."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.back.harness.observability.opik_lifecycle import ensure_opik


class FakeRunner:
    def __init__(self, returncode: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.returncode = returncode

    def __call__(self, script, args, timeout):
        self.calls.append(list(args))
        return subprocess.CompletedProcess(args=args, returncode=self.returncode)


class SequenceVerifier:
    def __init__(self, outcomes: list[bool]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        if not self.outcomes:
            return False
        return self.outcomes.pop(0)


class LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.home = root / "opik"
        self.home.mkdir()
        self.script = self.home / "opik.ps1"
        self.script.write_bytes(b"# opik")
        self.state = root / "state"
        self.env = patch.dict(
            os.environ,
            {
                "IRINA_OPIK_ENABLED": "1",
                "IRINA_OPIK_HOME": str(self.home),
                "IRINA_STATE_DIR": str(self.state),
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_disabled_does_nothing(self) -> None:
        os.environ["IRINA_OPIK_ENABLED"] = "0"
        runner = FakeRunner()
        status = ensure_opik(runner=runner)
        self.assertEqual(status.state, "disabled")
        self.assertEqual(runner.calls, [])

    def test_healthy_stack_is_reused_without_start(self) -> None:
        runner = FakeRunner()
        status = ensure_opik(
            runner=runner,
            port_probe=lambda: True,
            verifier=lambda: True,
        )
        self.assertEqual(status.state, "reused")
        self.assertEqual(runner.calls, [])

    def test_missing_stack_is_started(self) -> None:
        runner = FakeRunner()
        status = ensure_opik(
            runner=runner,
            port_probe=lambda: False,
            verifier=SequenceVerifier([False, True]),
            sleep=lambda _seconds: None,
            timeout=0,
        )
        self.assertEqual(status.state, "started")
        self.assertEqual(runner.calls, [[]])
        self.assertTrue(self.script.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_unhealthy_listener_is_restarted_once(self) -> None:
        runner = FakeRunner()
        status = ensure_opik(
            runner=runner,
            port_probe=lambda: True,
            verifier=SequenceVerifier([False, True]),
            sleep=lambda _seconds: None,
            timeout=0,
        )
        self.assertEqual(status.state, "started")
        self.assertEqual(runner.calls, [["--stop"], []])

    def test_explicit_restart_stops_before_start(self) -> None:
        os.environ["IRINA_OPIK_RESTART"] = "1"
        self.addCleanup(os.environ.pop, "IRINA_OPIK_RESTART", None)
        runner = FakeRunner()
        status = ensure_opik(
            runner=runner,
            port_probe=lambda: False,
            verifier=SequenceVerifier([False, True]),
            sleep=lambda _seconds: None,
            timeout=0,
        )
        self.assertEqual(status.state, "started")
        self.assertEqual(runner.calls, [["--stop"], []])

    def test_start_failure_fails_open(self) -> None:
        runner = FakeRunner(returncode=1)
        status = ensure_opik(
            runner=runner,
            port_probe=lambda: False,
            verifier=lambda: False,
            sleep=lambda _seconds: None,
            timeout=0,
        )
        self.assertEqual(status.state, "failed")
        self.assertIn("start failed", status.detail)

    def test_fresh_lock_fails_open_without_starting(self) -> None:
        self.state.mkdir(parents=True)
        (self.state / "opik.lock").write_text("other", encoding="utf-8")
        runner = FakeRunner()
        status = ensure_opik(
            runner=runner,
            port_probe=lambda: False,
            verifier=lambda: False,
            sleep=lambda _seconds: None,
            timeout=0,
        )
        self.assertEqual(status.state, "failed")
        self.assertEqual(runner.calls, [])

    def test_missing_script_fails_open(self) -> None:
        self.script.unlink()
        status = ensure_opik(runner=FakeRunner())
        self.assertEqual(status.state, "failed")
        self.assertIn("opik.ps1", status.detail)


if __name__ == "__main__":
    unittest.main()
