"""Run-level span tracing tests without a running Opik server."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.back.harness.observability.run_tracing import RunTracer, trace_span
from src.back.harness.observability.span_context import (
    reset_current_tracer,
    set_current_tracer,
)
from src.back.harness.providers.base import (
    ProviderResponse,
    StreamEventType,
    TokenUsage,
    ToolCall,
)
from src.back.harness.providers.tracing import TracingProvider


class FakeSpan:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeTrace:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.id = "trace-" + str(kwargs.get("name", ""))
        self.spans: list[FakeSpan] = []

    def span(self, **kwargs) -> FakeSpan:
        span = FakeSpan(**kwargs)
        self.spans.append(span)
        return span


class FakeClient:
    def __init__(self) -> None:
        self.traces: list[FakeTrace] = []

    def trace(self, **kwargs) -> FakeTrace:
        trace = FakeTrace(**kwargs)
        self.traces.append(trace)
        return trace

    def span(self, trace_id=None, **kwargs) -> FakeSpan:
        for trace in self.traces:
            if trace.id == trace_id:
                span = FakeSpan(**kwargs)
                trace.spans.append(span)
                return span
        raise AssertionError(f"unknown trace {trace_id}")


class FakeProvider:
    provider_name = "fake"

    def complete(self, model, system, messages, tools) -> ProviderResponse:
        return ProviderResponse(
            text="answer",
            tool_calls=[ToolCall(id="c1", name="bash", args={"command": "ls"})],
            finish_reason="stop",
            usage=TokenUsage(input_tokens=3, output_tokens=2),
        )

    def stream(self, model, system, messages, tools):
        yield SimpleNamespace(type=StreamEventType.FINISH, text="", tool_name="")


class RunTracerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.tracer = RunTracer(
            run_id="run-1",
            task="introduce yourself",
            session_id="session-1",
            thread_id="thread-1",
            client_factory=lambda: self.client,
        )

    def test_spans_group_into_pillar_traces_with_thread(self) -> None:
        with self.tracer.span(
            "tools", "tool.bash", span_type="tool", input={"cmd": "ls"}
        ) as handle:
            handle.set_output({"result": "ok"})
        with self.tracer.span("memory", "memory.retrieve", input={"q": "x"}):
            pass
        self.tracer.finish(status="completed")
        names = {trace.kwargs["name"] for trace in self.client.traces}
        self.assertEqual(names, {"irina:tools", "irina:memory"})
        self.assertTrue(all(trace.kwargs["thread_id"] == "thread-1" for trace in self.client.traces))
        self.assertTrue(
            all("pillar:" in " ".join(trace.kwargs["tags"]) for trace in self.client.traces)
        )
        self.assertTrue(all(trace.spans for trace in self.client.traces))

    def test_event_mapping_creates_tool_and_memory_spans(self) -> None:
        call = ToolCall(id="call-1", name="write_file", args={"path": "a"})
        self.tracer.record_event(
            SimpleNamespace(type=SimpleNamespace(value="tool_start"), tool_call=call)
        )
        self.tracer.record_event(
            SimpleNamespace(
                type=SimpleNamespace(value="tool_end"),
                tool_call=call,
                result="ERROR: denied",
            )
        )
        self.tracer.record_event(
            SimpleNamespace(
                type=SimpleNamespace(value="memory"),
                memory_phase="retrieve",
                memory_provider="fake",
                memory_count=2,
                memory_ok=True,
            )
        )
        self.tracer.finish(status="completed")
        by_name = {trace.kwargs["name"]: trace for trace in self.client.traces}
        self.assertIn("irina:tools", by_name)
        self.assertIn("irina:memory", by_name)
        tool_span = by_name["irina:tools"].spans[0]
        self.assertEqual(tool_span.kwargs["output"]["result"], "ERROR: denied")
        self.assertEqual(tool_span.kwargs["metadata"]["blocked_or_failed"], True)

    def test_llm_provider_emits_span_with_usage_under_run(self) -> None:
        token = set_current_tracer(self.tracer)
        try:
            provider = TracingProvider(
                FakeProvider(), client_factory=lambda: self.client, enabled=True
            )
            provider.complete("model-x", "system", [], [])
        finally:
            reset_current_tracer(token)
        self.tracer.finish(status="completed")
        traces = {trace.kwargs["name"]: trace for trace in self.client.traces}
        self.assertIn("irina:llm", traces)
        span = traces["irina:llm"].spans[0]
        self.assertEqual(span.kwargs["type"], "llm")
        self.assertEqual(span.kwargs["usage"]["total_tokens"], 5)
        self.assertEqual(span.kwargs["model"], "model-x")

    def test_finish_is_idempotent_and_safe_without_client(self) -> None:
        tracer = RunTracer(run_id="r", task="t", client_factory=lambda: None)
        tracer.start_span("tools", "x").end()
        tracer.finish(status="completed")
        tracer.finish(status="completed")

    def test_trace_span_is_noop_without_tracer(self) -> None:
        with trace_span("tools", "nothing") as handle:
            self.assertIsNone(handle)


if __name__ == "__main__":
    unittest.main()


class AssistantSpanTests(unittest.TestCase):
    def test_assistant_and_run_end_capture_outputs(self) -> None:
        client = FakeClient()
        tracer = RunTracer(
            run_id="run-2",
            task="list tools",
            client_factory=lambda: client,
        )
        tracer.record_event(
            SimpleNamespace(
                type=SimpleNamespace(value="assistant"),
                turn=1,
                text="Here are the tools",
                tool_calls=[],
            )
        )
        tracer.record_event(
            SimpleNamespace(
                type=SimpleNamespace(value="run_end"),
                status=SimpleNamespace(value="completed"),
                reason="done",
                text="Here are the tools",
                usage=None,
            )
        )
        tracer.finish(status="completed")
        by_name = {trace.kwargs["name"]: trace for trace in client.traces}
        llm_span = by_name["irina:llm"].spans[0]
        self.assertEqual(llm_span.kwargs["output"]["text"], "Here are the tools")
        end_span = by_name["irina:environment"].spans[0]
        self.assertEqual(end_span.kwargs["output"]["response"], "Here are the tools")


class ParentLinkTests(unittest.TestCase):
    def test_parent_run_id_is_recorded_in_trace_metadata(self) -> None:
        client = FakeClient()
        tracer = RunTracer(
            run_id="child",
            task="subtask",
            parent_run_id="parent",
            client_factory=lambda: client,
        )
        tracer.start_span("tools", "tool.x").end()
        tracer.finish(status="completed")
        self.assertEqual(client.traces[0].kwargs["metadata"]["parent_run_id"], "parent")
