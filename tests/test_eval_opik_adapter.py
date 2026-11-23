"""Opik adapter write-shape tests without a running server."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.back.evaluations.opik_adapter import client as adapter


class FakeTrace:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.id = "trace-1"
        self.ended = False

    def end(self) -> None:
        self.ended = True


class FakeClient:
    def __init__(self) -> None:
        self.traces: list[FakeTrace] = []

    def trace(self, **kwargs) -> FakeTrace:
        trace = FakeTrace(**kwargs)
        self.traces.append(trace)
        return trace


class OpikAdapterTests(unittest.TestCase):
    def test_log_trace_writes_payload_once_without_end(self) -> None:
        client = FakeClient()
        with patch.object(adapter, "_get_client", return_value=client):
            trace_id = adapter.log_trace(
                "eval:case",
                input={"case": "x"},
                output={"passed": True},
                metadata={"level": "L1_simulated_workflow"},
            )
        self.assertEqual(trace_id, "trace-1")
        trace = client.traces[0]
        self.assertEqual(trace.kwargs["input"], {"case": "x"})
        self.assertEqual(trace.kwargs["output"], {"passed": True})
        self.assertIn("start_time", trace.kwargs)
        self.assertIn("end_time", trace.kwargs)
        self.assertFalse(trace.ended)

    def test_log_trace_degrades_when_client_is_unavailable(self) -> None:
        with patch.object(adapter, "_get_client", return_value=None):
            self.assertIsNone(
                adapter.log_trace("eval:case", input={}, output={})
            )


if __name__ == "__main__":
    unittest.main()
