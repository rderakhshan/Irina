"""Tests for span-less provider tracing (no Opik server required)."""

from __future__ import annotations

import unittest

from src.back.harness.providers.base import (
    ProviderResponse,
    ProviderStreamEvent,
    StreamEventType,
    TokenUsage,
    ToolCall,
)
from src.back.harness.providers.tracing import TracingProvider


class FakeTrace:
    def __init__(self, name, **kwargs) -> None:
        self.name = name
        self.kwargs = kwargs
        self.input = kwargs.get("input")
        self.output = kwargs.get("output")
        self.metadata = kwargs.get("metadata")


class FakeClient:
    def __init__(self) -> None:
        self.traces: list[FakeTrace] = []
        self.flushed = False

    def trace(self, name, **kwargs) -> FakeTrace:
        trace = FakeTrace(name, **kwargs)
        self.traces.append(trace)
        return trace

    def flush(self) -> None:
        self.flushed = True


class FakeProvider:
    provider_name = "fake"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def complete(self, model, system, messages, tools) -> ProviderResponse:
        if self.fail:
            raise RuntimeError("boom")
        return ProviderResponse(
            text="hello",
            tool_calls=[ToolCall(id="c1", name="bash", args={"command": "ls"})],
            finish_reason="stop",
            usage=TokenUsage(input_tokens=3, output_tokens=5),
        )

    def stream(self, model, system, messages, tools):
        yield ProviderStreamEvent(type=StreamEventType.TEXT_DELTA, text="hel")
        yield ProviderStreamEvent(type=StreamEventType.TEXT_DELTA, text="lo")
        yield ProviderStreamEvent(
            type=StreamEventType.TOOL_CALL_START, tool_name="bash"
        )
        yield ProviderStreamEvent(
            type=StreamEventType.FINISH,
            finish_reason="stop",
            usage=TokenUsage(input_tokens=3, output_tokens=5),
        )


class TracingTests(unittest.TestCase):
    def make(self, *, enabled=True, fail=False):
        client = FakeClient()
        provider = TracingProvider(
            FakeProvider(fail=fail),
            client_factory=lambda: client,
            enabled=enabled,
        )
        return provider, client

    def test_complete_records_one_trace(self) -> None:
        provider, client = self.make()
        response = provider.complete("m1", "sys", [{"role": "user", "text": "q"}], [])
        self.assertEqual(response.text, "hello")
        self.assertEqual(len(client.traces), 1)
        trace = client.traces[0]
        self.assertEqual(trace.name, "llm:fake:m1")
        self.assertEqual(trace.kwargs["input"]["system"], "sys")
        self.assertEqual(trace.kwargs["output"]["text"], "hello")
        self.assertEqual(trace.kwargs["output"]["tool_calls"][0]["name"], "bash")
        self.assertEqual(trace.kwargs["metadata"]["usage"]["total_tokens"], 8)
        self.assertIn("start_time", trace.kwargs)
        self.assertIn("end_time", trace.kwargs)

    def test_complete_error_records_and_reraises(self) -> None:
        provider, client = self.make(fail=True)
        with self.assertRaises(RuntimeError):
            provider.complete("m1", "sys", [], [])
        trace = client.traces[0]
        self.assertIn("boom", trace.kwargs["output"]["error"])

    def test_stream_records_one_trace(self) -> None:
        provider, client = self.make()
        events = list(provider.stream("m2", "sys", [], []))
        self.assertEqual(len(events), 4)
        self.assertEqual(len(client.traces), 1)
        trace = client.traces[0]
        self.assertEqual(trace.kwargs["output"]["text"], "hello")
        self.assertEqual(trace.kwargs["output"]["tool_calls"], ["bash"])
        self.assertTrue(trace.kwargs["metadata"]["streamed"])

    def test_disabled_records_nothing(self) -> None:
        provider, client = self.make(enabled=False)
        provider.complete("m1", "sys", [], [])
        list(provider.stream("m1", "sys", [], []))
        self.assertEqual(client.traces, [])


if __name__ == "__main__":
    unittest.main()
