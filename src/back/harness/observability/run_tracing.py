"""Run-level Opik tracing with spans grouped by pillar.

Trace layout:
    thread_id = session id (or "Irina")
    irina:llm / irina:memory / irina:tools / irina:environment traces
    spans inside each trace carry pillar, concerns, timing, usage, errors.

All writes are post-run: traces and spans are created with explicit
start/end times after the run, avoiding Opik's create/update race.
"""

from __future__ import annotations

import traceback as traceback_module
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

from ..tools_and_guardrails.security import redact_secrets
from .span_context import current_tracer

PILLARS = ("llm", "memory", "tools", "environment")
DEFAULT_CONCERNS = {
    "llm": ("trustworthiness", "safety"),
    "memory": ("trustworthiness", "explainability"),
    "tools": ("accountability", "safety"),
    "environment": ("accountability", "security_resilience"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: Any, *, limit: int = 20_000) -> Any:
    if isinstance(value, str):
        text = redact_secrets(value)
        return text if len(text) <= limit else text[:limit] + "...[truncated]"
    if isinstance(value, dict):
        return {str(key): _clean(item, limit=limit) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item, limit=limit) for item in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_secrets(str(value))[:limit]


def _usage(usage: Any) -> dict[str, int] | None:
    if usage is None:
        return None
    prompt = getattr(usage, "input_tokens", None)
    completion = getattr(usage, "output_tokens", None)
    if prompt is None and completion is None:
        return None
    total = int(prompt or 0) + int(completion or 0)
    return {
        "prompt_tokens": int(prompt or 0),
        "completion_tokens": int(completion or 0),
        "total_tokens": total,
    }


@dataclass(slots=True)
class SpanRecord:
    pillar: str
    name: str
    span_type: str
    start: datetime
    end: datetime
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    concerns: tuple[str, ...] = ()
    usage: dict[str, int] | None = None
    model: str = ""
    provider: str = ""
    error_info: dict[str, Any] | None = None


class SpanHandle:
    def __init__(self, tracer: "RunTracer", record: SpanRecord) -> None:
        self._tracer = tracer
        self._record = record
        self._ended = False

    @property
    def id(self) -> str:
        return ""

    def set_output(self, output: dict[str, Any]) -> None:
        self._record.output.update(_clean(output))

    def set_metadata(self, metadata: dict[str, Any]) -> None:
        self._record.metadata.update(_clean(metadata))

    def set_usage(self, usage: dict[str, int] | None) -> None:
        self._record.usage = usage

    def set_model(self, model: str, provider: str = "") -> None:
        self._record.model = model
        self._record.provider = provider

    def fail(self, exc: BaseException) -> None:
        self._record.error_info = {
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "traceback": "".join(
                traceback_module.format_exception(type(exc), exc, exc.__traceback__)
            )[-8_000:],
        }
        self._record.output.setdefault("error", f"{type(exc).__name__}: {exc}")
        self._end()

    def end(self) -> None:
        self._end()

    def _end(self) -> None:
        if self._ended:
            return
        self._ended = True
        self._record.end = _now()
        if self._record.end <= self._record.start:
            self._record.end = self._record.start + timedelta(milliseconds=1)

    def __enter__(self) -> "SpanHandle":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> bool:
        if exc is not None:
            self.fail(exc)
        else:
            self._end()
        return False


class RunTracer:
    """Collects spans during a run and writes them as Opik pillar traces."""

    def __init__(
        self,
        *,
        run_id: str,
        task: str,
        session_id: str = "",
        thread_id: str = "Irina",
        parent_run_id: str | None = None,
        client_factory: Any | None = None,
    ) -> None:
        self.run_id = run_id
        self.parent_run_id = parent_run_id
        self.task = task[:2_000]
        self.session_id = session_id
        self.thread_id = thread_id or "Irina"
        self._client_factory = client_factory
        self._spans: list[SpanRecord] = []
        self._open_tools: dict[str, SpanHandle] = {}
        self._finished = False

    @classmethod
    def start(
        cls,
        *,
        task: str,
        session_id: str = "",
        thread_id: str = "",
        parent_run_id: str | None = None,
        client_factory: Any | None = None,
    ) -> "RunTracer | None":
        try:
            from .opik_lifecycle import tracing_enabled
            from ..providers.tracing import sdk_available

            if not tracing_enabled() or not sdk_available():
                return None
        except Exception:
            return None
        run_id = str(uuid.uuid4())
        return cls(
            run_id=run_id,
            task=task,
            session_id=session_id,
            thread_id=thread_id or session_id or "Irina",
            parent_run_id=parent_run_id,
            client_factory=client_factory,
        )

    def start_span(
        self,
        pillar: str,
        name: str,
        *,
        span_type: str = "general",
        input: dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        concerns: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        usage: dict[str, int] | None = None,
        model: str = "",
        provider: str = "",
    ) -> SpanHandle:
        record = SpanRecord(
            pillar=pillar if pillar in PILLARS else "environment",
            name=name,
            span_type=span_type,
            start=_now(),
            end=_now(),
            input=_clean(input or {}),
            output=_clean(output or {}),
            metadata=_clean(metadata or {}),
            concerns=concerns or DEFAULT_CONCERNS.get(pillar, ()),
            tags=list(tags),
            usage=usage,
            model=model,
            provider=provider,
        )
        self._spans.append(record)
        return SpanHandle(self, record)

    @contextmanager
    def span(self, pillar: str, name: str, **kwargs: Any) -> Iterator[SpanHandle]:
        handle = self.start_span(pillar, name, **kwargs)
        try:
            yield handle
        except BaseException as exc:
            handle.fail(exc)
            raise
        else:
            handle.end()

    def record_event(self, event: Any) -> None:
        event_type = getattr(event, "type", None)
        value = getattr(event_type, "value", event_type)
        if value == "model":
            self._record_zero_span(
                "llm",
                "model.routing",
                span_type="general",
                output={
                    "provider": getattr(event, "provider", ""),
                    "model": getattr(event, "model", ""),
                    "model_id": getattr(event, "model_id", ""),
                    "routing_mode": getattr(event, "routing_mode", ""),
                    "routing_reason": getattr(event, "routing_reason", ""),
                },
                concerns=("trustworthiness", "lifecycle"),
            )
        elif value == "tool_start":
            call = getattr(event, "tool_call", None)
            if call is None:
                return
            handle = self.start_span(
                "tools",
                f"tool.{call.name}",
                span_type="tool",
                input={"tool": call.name, "args": dict(call.args), "call_id": call.id},
                concerns=("accountability", "safety"),
            )
            self._open_tools[call.id] = handle
        elif value == "tool_end":
            call = getattr(event, "tool_call", None)
            if call is None:
                return
            handle = self._open_tools.pop(call.id, None)
            result = str(getattr(event, "result", "") or "")
            if handle is None:
                handle = self.start_span(
                    "tools",
                    f"tool.{call.name}",
                    span_type="tool",
                    input={"tool": call.name, "args": dict(call.args), "call_id": call.id},
                )
            handle.set_output(
                {"result": result[:20_000], "failed": result.startswith(("ERROR:", "BLOCKED:"))}
            )
            if result.startswith(("ERROR:", "BLOCKED:")):
                handle.set_metadata({"blocked_or_failed": True})
            handle.end()
        elif value == "memory":
            self._record_zero_span(
                "memory",
                f"memory.{getattr(event, 'memory_phase', 'operation') or 'operation'}",
                span_type="general",
                output={
                    "provider": getattr(event, "memory_provider", ""),
                    "phase": getattr(event, "memory_phase", ""),
                    "count": getattr(event, "memory_count", None),
                    "ok": getattr(event, "memory_ok", None),
                },
                concerns=("trustworthiness", "explainability"),
            )
        elif value == "context_compacted":
            self._record_zero_span(
                "memory",
                "memory.compaction",
                span_type="general",
                output={
                    "before_tokens": getattr(event, "before_tokens", None),
                    "after_tokens": getattr(event, "after_tokens", None),
                    "summarized": getattr(event, "summarized_messages", 0),
                    "preserved": getattr(event, "preserved_messages", 0),
                    "succeeded": getattr(event, "compaction_succeeded", None),
                },
            )
        elif value == "assistant":
            calls = []
            for call in getattr(event, "tool_calls", []) or []:
                calls.append(
                    {
                        "id": getattr(call, "id", ""),
                        "name": getattr(call, "name", ""),
                        "args": dict(getattr(call, "args", {}) or {}),
                    }
                )
            self._record_zero_span(
                "llm",
                f"assistant.turn.{getattr(event, 'turn', 0)}",
                span_type="general",
                output={"text": getattr(event, "text", ""), "tool_calls": calls},
                concerns=("trustworthiness", "explainability"),
            )
        elif value == "run_end":
            self._record_zero_span(
                "environment",
                "run.end",
                span_type="general",
                output={
                    "status": getattr(getattr(event, "status", None), "value", None),
                    "reason": getattr(event, "reason", ""),
                    "response": getattr(event, "text", ""),
                    "usage": _usage(getattr(event, "usage", None)),
                },
                concerns=("accountability", "auditing"),
            )

    def _record_zero_span(
        self,
        pillar: str,
        name: str,
        *,
        span_type: str = "general",
        output: dict[str, Any] | None = None,
        input: dict[str, Any] | None = None,
        concerns: tuple[str, ...] = (),
    ) -> None:
        handle = self.start_span(
            pillar,
            name,
            span_type=span_type,
            input=input,
            output=output,
            concerns=concerns,
        )
        if output:
            handle.set_output(output)
        handle.end()

    def finish(
        self,
        *,
        status: str,
        error: BaseException | None = None,
    ) -> None:
        if self._finished:
            return
        self._finished = True
        for handle in list(self._open_tools.values()):
            handle.set_output({"result": "unfinished tool call"})
            handle.end()
        self._open_tools.clear()
        client = self._client()
        if client is None:
            return
        grouped: dict[str, list[SpanRecord]] = {pillar: [] for pillar in PILLARS}
        for record in self._spans:
            grouped.setdefault(record.pillar, []).append(record)
        for pillar, records in grouped.items():
            if not records:
                continue
            concerns = sorted({item for record in records for item in record.concerns})
            start = min(record.start for record in records)
            end = max(record.end for record in records)
            if end <= start:
                end = start + timedelta(milliseconds=1)
            tags = ["irina", f"pillar:{pillar}", *[f"concern:{item}" for item in concerns]]
            try:
                trace = client.trace(
                    name=f"irina:{pillar}",
                    input={
                        "run_id": self.run_id,
                        "pillar": pillar,
                        "task": self.task,
                        "spans": len(records),
                    },
                    output={
                        "run_id": self.run_id,
                        "status": status,
                        "spans": len(records),
                        "error": f"{type(error).__name__}: {error}" if error else None,
                    },
                    metadata={
                        "run_id": self.run_id,
                        "parent_run_id": self.parent_run_id,
                        "session_id": self.session_id,
                        "pillar": pillar,
                        "concerns": concerns,
                        "integration": "runtime",
                    },
                    tags=tags,
                    thread_id=self.thread_id,
                    start_time=start,
                    end_time=end,
                )
                trace_id = getattr(trace, "id", None)
                for record in records:
                    kwargs: dict[str, Any] = {
                        "name": record.name,
                        "type": record.span_type,
                        "start_time": record.start,
                        "end_time": record.end,
                        "input": record.input,
                        "output": record.output,
                        "metadata": {
                            **record.metadata,
                            "pillar": record.pillar,
                            "concerns": list(record.concerns),
                            "run_id": self.run_id,
                        },
                        "tags": [
                            f"pillar:{record.pillar}",
                            *[f"concern:{item}" for item in record.concerns],
                            *record.tags,
                        ],
                    }
                    if record.usage:
                        kwargs["usage"] = record.usage
                    if record.model:
                        kwargs["model"] = record.model
                    if record.provider:
                        kwargs["provider"] = record.provider
                    if record.error_info:
                        kwargs["error_info"] = record.error_info
                    if trace_id:
                        client.span(trace_id=trace_id, **kwargs)
                    else:
                        trace.span(**kwargs)
            except Exception:
                continue

    def _client(self) -> Any:
        if self._client_factory is not None:
            try:
                return self._client_factory()
            except Exception:
                return None
        try:
            from ..providers.tracing import _get_client

            return _get_client()
        except Exception:
            return None


@contextmanager
def trace_span(
    pillar: str,
    name: str,
    **kwargs: Any,
) -> Iterator[SpanHandle | None]:
    tracer = current_tracer()
    if tracer is None:
        yield None
        return
    with tracer.span(pillar, name, **kwargs) as handle:
        yield handle


__all__ = [
    "DEFAULT_CONCERNS",
    "PILLARS",
    "RunTracer",
    "SpanHandle",
    "SpanRecord",
    "trace_span",
]
