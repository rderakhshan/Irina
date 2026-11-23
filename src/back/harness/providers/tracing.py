"""Span-less Opik tracing for every provider call.

One flat trace per LLM call: input, output, and provider/model metadata. The
wrapper deliberately records no spans yet; a span-based layout can be added
inside :class:`TracingProvider` without touching any call site.

Tracing is optional and fail-open: a missing SDK, an unreachable Opik server,
or any client error never changes the provider result.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from ..observability.opik_lifecycle import opik_home, tracing_enabled
from ..observability.span_context import current_tracer
from ..tools_and_guardrails.security import redact_secrets
from .base import (
    Provider,
    ProviderResponse,
    ProviderStreamEvent,
    StreamEventType,
)

ClientFactory = Callable[[], Any]

_client: Any = None
_client_failed = False
_client_lock = threading.Lock()
_client_factory: ClientFactory | None = None
_opik_module: Any = None
_opik_checked = False

_TRUTHY = {"1", "true", "yes", "on"}


def _local_sdk_root() -> Path | None:
    """Return the checkout's Python SDK src directory, when present."""
    home = opik_home()
    if home is None:
        return None
    candidate = home / "sdks" / "python" / "src"
    if (candidate / "opik" / "__init__.py").is_file():
        return candidate
    return None


def _load_opik() -> Any:
    """Import the Opik SDK, preferring the local checkout.

    A cloned Opik repository at the project root shadows the package as a
    namespace package, and its Python SDK uses a ``src`` layout. Retry with the
    project roots removed and the local ``sdks/python/src`` path appended.
    """
    global _opik_module, _opik_checked
    if _opik_checked:
        return _opik_module
    _opik_checked = True
    os.environ.setdefault("OPIK_CONSOLE_LOGGING_LEVEL", "WARNING")
    try:
        import opik as candidate  # type: ignore[import-not-found]

        if hasattr(candidate, "Opik"):
            _opik_module = candidate
            return _opik_module
    except Exception:
        pass

    for name in [key for key in sys.modules if key == "opik" or key.startswith("opik.")]:
        sys.modules.pop(name, None)

    local_src = _local_sdk_root()
    project_roots = {str(parent) for parent in Path(__file__).resolve().parents}
    saved_path = list(sys.path)
    try:
        sys.path[:] = [
            entry
            for entry in sys.path
            if entry not in {"", "."}
            and str(Path(entry).resolve()) not in project_roots
        ]
        if local_src is not None:
            sys.path.insert(0, str(local_src))
        import opik as candidate  # type: ignore[import-not-found]

        _opik_module = candidate if hasattr(candidate, "Opik") else None
    except Exception:
        _opik_module = None
    finally:
        sys.path[:] = saved_path
    return _opik_module


def sdk_available() -> bool:
    """Return whether the Opik Python SDK can be imported."""
    return _load_opik() is not None


def set_client_factory(factory: ClientFactory | None) -> None:
    """Override client construction; used by tests and embedders."""
    global _client_factory, _client
    _client_factory = factory
    _client = None


def _ensure_project(client: Any, name: str) -> None:
    """Create the trace project once; ignore 'already exists' errors."""
    try:
        client.rest_client.projects.create_project(name=name)
    except Exception:
        pass


def _default_client() -> Any:
    module = _load_opik()
    if module is None:
        return None
    project = os.environ.get("OPIK_PROJECT_NAME") or "Irina"
    os.environ.setdefault("OPIK_PROJECT_NAME", project)
    os.environ.setdefault("OPIK_SUPPRESS_BATCHING_UPDATE_WARNING", "true")
    os.environ.setdefault("OPIK_CONSOLE_LOGGING_LEVEL", "WARNING")
    client = module.Opik()
    _ensure_project(client, project)
    return client


def _get_client() -> Any:
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed:
        return None
    with _client_lock:
        if _client is not None:
            return _client
        if _client_failed:
            return None
        factory = _client_factory or _default_client
        try:
            _client = factory()
        except Exception:
            _client_failed = True
            _client = None
        return _client


def _enabled() -> bool:
    if _as_bool(os.environ.get("OPIK_TRACK_DISABLE")):
        return False
    return tracing_enabled()


def _as_bool(value: str | None) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


def _safe(value: Any) -> Any:
    """Redact secrets from strings before they leave the process."""
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


def _usage_dict(usage: Any) -> dict[str, int] | None:
    if usage is None:
        return None
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    if input_tokens is None and output_tokens is None:
        return None
    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(input_tokens or 0) + int(output_tokens or 0),
    }


def flush_tracing() -> None:
    """Flush pending traces; never raises."""
    client = _client
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        pass


def wrap_provider(provider: Provider) -> Provider:
    """Return a tracing wrapper when tracing is enabled."""
    if not _enabled() or not sdk_available():
        return provider
    return TracingProvider(provider)


class TracingProvider:
    """Delegate a provider and record one span-less Opik trace per call."""

    def __init__(
        self,
        inner: Provider,
        *,
        client_factory: ClientFactory | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._inner = inner
        # Enabled state is fixed at construction: the wrapper only exists when
        # tracing was enabled, and runtime imports must not change that.
        self._enabled_override = True if enabled is None else enabled
        if client_factory is not None:
            set_client_factory(client_factory)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def _active(self) -> bool:
        if not self._enabled_override:
            return False
        return not _as_bool(os.environ.get("OPIK_TRACK_DISABLE"))

    def _provider_name(self) -> str:
        for attribute in ("provider_name", "name", "provider_id"):
            value = getattr(self._inner, attribute, "")
            if value:
                return str(value)
        return type(self._inner).__name__

    def _begin(self, model: str, system: str, messages, tools):
        """Capture the trace start and input; the trace is written at the end.

        A single create-trace message containing input, output, and an explicit
        end time is reliable across SDK/backend versions; separate update
        messages can be dropped, leaving an empty placeholder row.
        """
        if not self._active():
            return None
        if _get_client() is None:
            return None
        payload = _safe({"system": system, "messages": messages, "tools": tools})
        tracer = current_tracer()
        if tracer is not None:
            handle = tracer.start_span(
                "llm",
                f"llm.{self._provider_name()}:{model}",
                span_type="llm",
                input=payload,
                concerns=("trustworthiness", "safety"),
                model=model,
                provider=self._provider_name(),
            )
            return ("span", handle)
        return ("trace", datetime.now(timezone.utc), payload)

    def _end(self, trace: Any, output: dict[str, Any], metadata: dict[str, Any]) -> None:
        if trace is None:
            return
        if trace[0] == "span":
            handle = trace[1]
            handle.set_output(output)
            handle.set_metadata(metadata)
            usage = metadata.get("usage")
            if isinstance(usage, dict):
                handle.set_usage(
                    {
                        "prompt_tokens": int(usage.get("input_tokens", 0)),
                        "completion_tokens": int(usage.get("output_tokens", 0)),
                        "total_tokens": int(usage.get("total_tokens", 0)),
                    }
                )
            handle.end()
            return
        _, started_at, payload = trace
        try:
            client = _get_client()
            if client is None:
                return
            client.trace(
                name=f"llm:{self._provider_name()}:{metadata.get('model', '')}",
                input=payload,
                output=_safe(output),
                metadata=_safe(metadata),
                start_time=started_at,
                end_time=datetime.now(timezone.utc),
            )
        except Exception:
            pass

    def _metadata(self, model: str, **extra: Any) -> dict[str, Any]:
        metadata = {
            "provider": self._provider_name(),
            "model": model,
            "tracing": "irina",
        }
        metadata.update({key: value for key, value in extra.items() if value is not None})
        return metadata

    def complete(self, model: str, system: str, messages, tools) -> ProviderResponse:
        trace = self._begin(model, system, messages, tools)
        try:
            response = self._inner.complete(model, system, messages, tools)
        except Exception as exc:
            self._end(
                trace,
                {"error": f"{type(exc).__name__}: {exc}"},
                self._metadata(model),
            )
            raise
        self._end(
            trace,
            {
                "text": response.text,
                "tool_calls": [
                    {"name": call.name, "args": call.args}
                    for call in response.tool_calls
                ],
            },
            self._metadata(
                model,
                finish_reason=response.finish_reason,
                usage=_usage_dict(response.usage),
                streamed=False,
            ),
        )
        return response

    def stream(
        self, model: str, system: str, messages, tools
    ) -> Iterator[ProviderStreamEvent]:
        trace = self._begin(model, system, messages, tools)
        chunks: list[str] = []
        tool_names: list[str] = []
        finish_reason = ""
        usage = None
        error: str | None = None
        try:
            for event in self._inner.stream(model, system, messages, tools):
                if event.type is StreamEventType.TEXT_DELTA and event.text:
                    chunks.append(event.text)
                elif event.type is StreamEventType.TOOL_CALL_START and event.tool_name:
                    tool_names.append(event.tool_name)
                elif event.type is StreamEventType.FINISH:
                    finish_reason = event.finish_reason or finish_reason
                    usage = event.usage or usage
                yield event
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            output: dict[str, Any] = {
                "text": "".join(chunks),
                "tool_calls": tool_names,
            }
            if error is not None:
                output["error"] = error
            self._end(
                trace,
                output,
                self._metadata(
                    model,
                    finish_reason=finish_reason or None,
                    usage=_usage_dict(usage),
                    streamed=True,
                ),
            )


__all__ = [
    "TracingProvider",
    "flush_tracing",
    "sdk_available",
    "set_client_factory",
    "wrap_provider",
]
