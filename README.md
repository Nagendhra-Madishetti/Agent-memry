# Cogniflow

**Temporal, self-falsifying belief substrate for agentic RAG.** The combination of a
bi-temporal knowledge graph (à la Graphiti) with an agentic retrieval loop (à la
LlamaIndex), welded by a closed feedback loop: retrieve → check validity → falsify
superseded beliefs → persist the verdict → reshape the next retrieval.

This is **ChronoRAG** (temporal) × **PALIMPSEST** (self-falsifying) as a library.

> **Status: Phase 1a (walking skeleton, substrate slice).**
> Done: stable contracts, sync + async conformance harness, and the real
> `GraphitiFalkorDBBackend` (AsyncSubstrate). THE heartbeat is proven against live
> FalkorDB + an LLM: the same question at `as_of=T1` vs `as_of=T2` returns different
> answers because a fact was superseded between them (see `examples/heartbeat_demo.py`
> and `tests/integration/`).
> Deferred: the LlamaIndex retriever/postprocessor/agent bridge (Phase 1b), plus
> write-back, pluggable policies, replay API, verification, and advanced rerank.

## Design rule

The **core is dependency-free**. `cogniflow.core` imports nothing but the standard
library. Heavy dependencies (`graphiti-core`, `llama-index-core`, `falkordb`) are pulled
in only by *backends* and *bridges*, and only when their optional extras are installed.
This is what keeps the contracts stable and the architecture pluggable.

## The spine

```
            ┌──────────────────────── core (stdlib only) ───────────────────────┐
            │  types.py     Belief · Episode · RetrievalQuery · ScoredBelief ·   │
            │               RetrievalResult · FalsificationVerdict · WriteReceipt│
            │  contracts.py Substrate / AsyncSubstrate   (write · read · falsify)│
            │  policies.py  RetrievalPolicy · ValidityPolicy ·                   │
            │               FalsificationPolicy · WritebackPolicy   (4 policies) │
            └───────────────┬───────────────────────────────────┬───────────────┘
                            │ implemented by                     │ adapted by
                            ▼                                     ▼
                   backends/ (Substrate impls)           bridges/ (framework glue)
                   - noop.py        ← Phase 0            - contracts.py (neutral)
                   - graphiti.py    ← Phase 1 (deferred) - llamaindex/   ← deferred
                            │
                            ▼
                   conformance/ (the test harness any backend must pass)
```

### The three substrate operations
- **write(episode)** → `WriteReceipt` — ingest a source episode into beliefs.
- **read(query)** → `RetrievalResult` — retrieve beliefs valid as-of a point in time.
- **falsify(target, against=…)** → `FalsificationVerdict` — decide if a belief is superseded.

### The four policy interfaces (the seams from the design analysis)
| Policy | Seam | Question it answers |
|---|---|---|
| `RetrievalPolicy` | read | how to resolve as-of and rank candidates |
| `ValidityPolicy` | invalidate | is this belief valid at time *t*? |
| `FalsificationPolicy` | falsify | is this belief superseded, and by what? |
| `WritebackPolicy` | write-back | should a retrieval outcome become a new belief? |

## Install (dev)

```bash
pip install -e ".[dev]"
```

## Prove the skeleton

```bash
ruff check .
pytest
```

Phase-0 proof: the contracts are stable (field-surface is frozen by tests), a no-op
backend passes the conformance stub, and CI is green across Python 3.10–3.12.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
