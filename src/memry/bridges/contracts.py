"""Framework-neutral bridge contracts.

A *bridge* adapts the substrate onto an external framework (LlamaIndex first). To
keep the core dependency-free, the bridge *contracts* live here and import nothing
framework-specific; concrete adapters (which import e.g. llama-index-core) live in
their own submodules and convert ``BridgeNode`` <-> the framework's node type.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from ..core.types import RetrievalResult


@dataclass(frozen=True, slots=True)
class BridgeNode:
    """A framework-neutral retrieved node carrying temporal metadata.

    A concrete bridge maps this to/from the host framework's node type (for
    LlamaIndex: ``NodeWithScore`` wrapping a ``TextNode``).
    """

    id: str
    text: str
    score: float | None = None
    valid_at: datetime | None = None
    invalid_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class RetrieverBridge(Protocol):
    """Adapts ``Substrate.read`` into the host framework's retriever surface."""

    def retrieve(
        self,
        query_text: str,
        as_of: datetime | None = None,
        top_k: int = 5,
    ) -> Sequence[BridgeNode]: ...


@runtime_checkable
class PostprocessorBridge(Protocol):
    """Adapts the validity check into the host framework's node-postprocessor."""

    def filter(
        self,
        nodes: Sequence[BridgeNode],
        as_of: datetime | None = None,
    ) -> Sequence[BridgeNode]: ...


@runtime_checkable
class ToolBridge(Protocol):
    """Describes an agent tool (e.g. verify_fact / record_observation)."""

    @property
    def name(self) -> str: ...

    def describe(self) -> Mapping[str, Any]: ...


def from_retrieval_result(result: RetrievalResult) -> list[BridgeNode]:
    """Convert a core ``RetrievalResult`` into framework-neutral bridge nodes."""
    return [
        BridgeNode(
            id=sb.belief.id,
            text=sb.belief.statement,
            score=sb.score,
            valid_at=sb.belief.valid_at,
            invalid_at=sb.belief.invalid_at,
            metadata=dict(sb.belief.metadata),
        )
        for sb in result.results
    ]
