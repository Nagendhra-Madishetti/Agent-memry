# Cogniflow

**Temporal, self-falsifying belief substrate for agentic RAG.** The combination of a
bi-temporal knowledge graph (à la Graphiti) with an agentic retrieval loop (à la
LlamaIndex), welded by a closed feedback loop: retrieve → check validity → falsify
superseded beliefs → persist the verdict → reshape the next retrieval.

This is **ChronoRAG** (temporal) × **PALIMPSEST** (self-falsifying) as a library.

> **Status: Phase 5 (inline verification + advanced retrieval - the opt-in probabilistic tier).**
> The expensive, opt-in capabilities are in, structurally fenced off from the deterministic
> ledger. `verify_fact` is the LLM `FalsificationPolicy` (registry `falsification: llm`) plus
> a tool: **read-only and advisory** - it returns a verdict and never writes (acting on it
> routes through the existing queued write-back). It is **bounded**: timeout, defined
> fallback, and a distinguishable *indeterminate* verdict; any failure degrades to
> indeterminate, never a confident clean and never a mutation. Its reliability is **measured**
> (precision/recall on a labeled set via `cogniflow.eval`), not asserted by one green run.
> Retrieval ranking is opt-in and default-off, with **validity-filter before rank** (a
> correctness decision). Point-in-time caching is **dual-axis**: frozen past-S replays cache
> permanently; current-knowledge event-time invalidates on write. R1: no function-calling
> model is configured, so the agent stays ReAct and that re-query reliability is documented.
> Deferred to Phase 6: multi-backend (Neo4j parity), persist `superseded_by`, scale/partition,
> non-OpenAI swap verification. Replay UI stays a separate optional package.

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
