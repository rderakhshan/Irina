"""L2 harness integration test with a scripted model."""

from __future__ import annotations

import unittest

from src.back.evaluations.runners import run_scripted


class HarnessRunnerTests(unittest.TestCase):
    def test_scripted_run_uses_real_harness(self) -> None:
        run = run_scripted("Return the canonical answer.", "42")
        self.assertEqual(run.answer, "42")
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.integration_level, "L2_irina_integrated")
        event_types = {event.type.value for event in run.events}
        self.assertIn("run_end", event_types)
        self.assertIn("assistant", event_types)


if __name__ == "__main__":
    unittest.main()
