"""Observability for the read / write-back path.

A single ``emit`` fans every event out to: (1) structured logging (always),
(2) any registered in-process sinks (used by tests to verify the trace-emission
contract), and (3) Langfuse when ``LANGFUSE_PUBLIC_KEY`` is configured (a no-op
otherwise). The Langfuse path and the sink path go through the same ``emit``, so a
test that asserts on sinks is exercising the exact code path Langfuse rides on.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("memry")

# In-process sinks: callables (event_name, payload). Used by tests and any embedder
# of memry that wants the event stream without Langfuse.
Sink = Callable[[str, dict[str, Any]], None]
_SINKS: list[Sink] = []

_LANGFUSE: Any = None
_LANGFUSE_TRIED = False


def add_sink(sink: Sink) -> None:
    _SINKS.append(sink)


def remove_sink(sink: Sink) -> None:
    if sink in _SINKS:
        _SINKS.remove(sink)


def clear_sinks() -> None:
    _SINKS.clear()


def _langfuse() -> Any:
    global _LANGFUSE, _LANGFUSE_TRIED
    if _LANGFUSE_TRIED:
        return _LANGFUSE
    _LANGFUSE_TRIED = True
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        return None
    try:
        from langfuse import Langfuse

        _LANGFUSE = Langfuse()
    except Exception:
        _LANGFUSE = None
    return _LANGFUSE


def emit(event: str, **payload: Any) -> None:
    """Emit one observability event to logging, sinks, and Langfuse."""
    logger.info("%s %s", event, payload)
    for sink in list(_SINKS):
        try:
            sink(event, payload)
        except Exception:
            pass
    client = _langfuse()
    if client is not None:
        try:
            client.event(name=event, metadata=payload)
        except Exception:
            pass


def log_read(text: str, as_of: Any, n_candidates: int, n_kept: int) -> None:
    emit(
        "memry.read",
        query=text,
        as_of=str(as_of),
        candidates=n_candidates,
        kept=n_kept,
    )


def log_queue_event(event: str, **payload: Any) -> None:
    """Emit a write-back queue transition (enqueue/start/success/retry/fail/reject/drain)."""
    emit(f"memry.writeback.{event}", **payload)
