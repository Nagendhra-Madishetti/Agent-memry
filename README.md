# Cogniflow

**Temporal, self-falsifying belief substrate for agentic RAG.** The combination of a
bi-temporal knowledge graph (à la Graphiti) with an agentic retrieval loop (à la
LlamaIndex), welded by a closed feedback loop: retrieve → check validity → falsify
superseded beliefs → persist the verdict → reshape the next retrieval.

This is **ChronoRAG** (temporal) × **PALIMPSEST** (self-falsifying) as a library.

> **Status: Phase 6 - hardened for scale and contributors (1.0-ready).**
> The auditable, self-hostable belief ledger for agents. Both original promises are cashed:
> **(1) multi-backend** - a Neo4j backend passes the *same* heartbeat / both-stamps / replay
> un-knowing / provenance assertions as FalkorDB with no weakened check and no core
> special-casing (the Phase-0 abstraction held); **(2) the contributor proof** - a new policy
> added entirely from the public API, outside `core/`, certified by the same conformance
> suite. The deferred-debt ledger is fully disposed (see `PROJECT_STATUS.md`): durable queue
> journal, write-time `superseded_by`, archive seam with correct replay over archived history,
> a CI integration lane over real backends, and a grown verify_fact eval with **recall** as
> the headline. Non-OpenAI is real: the whole pipeline runs on MiniMax-M3 via NVIDIA.
> Extend it from [CONTRIBUTING.md](CONTRIBUTING.md) + [docs/EXTENDING.md](docs/EXTENDING.md)
> without touching core. Non-goals (stay honest): no UI in core, no hosted offering,
> self-hostable is the moat.

> **Product layer - Slice A (OKF in -> temporally-correct answer out, headless).**
> Cogniflow ingests Google's [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog)
> bundles (`cogniflow.okf`, built to the spec's weak conformance, derived `valid_at`
> labeled, no core changes) and answers through a straight temporal-RAG loop
> (`cogniflow.pipelines.temporal_rag_answer`). The controlled head-to-head
> (`demo/okf_head_to_head.py`, same LLM/corpus/pipeline, only the memory layer differs):
> on an OKF bundle whose `weekly_active_users` metric is redefined March->June, **plain
> RAG returns the stale 7-day definition; Cogniflow returns the current 28-day one and
> replays the 7-day one for `as_of=March`.** The win is temporal correctness, not recall.

> **Product layer - Slice A.2 (the second front door: any document in).** Beyond OKF,
> Cogniflow ingests plain text, markdown, and **PDFs** (`cogniflow.documents`) through the
> *same* Episode/`write` path - parse -> structure-preserving chunks -> Episodes, no core
> changes. The parser is pluggable (`DocumentParser`): pypdf is the default behind the
> `[documents]` extra, MinerU is the documented production adapter behind `[mineru]`;
> heavy deps are never core. **ColPali / image-indexing is deliberately out** - you cannot
> attach a validity interval to a page-image embedding, and the temporal layer needs facts
> (see [docs/DOCUMENT_INGESTION.md](docs/DOCUMENT_INGESTION.md)). Cross-version
> supersession is free: re-ingesting an updated document stamps the old fact with both
> `invalid_at` and `expired_at`. The PDF head-to-head (`demo/doc_head_to_head.py`, two
> report versions, HQ Boston->Denver) shows the structural win: plain RAG has **no as-of
> axis** and cannot answer "as of 2020" at all; Cogniflow returns the current fact for now
> and replays the old one for the past. Document fact-extraction is honest about its limit
> - reliable for concrete statements, weak for abstract prose; structured input (OKF's
> `fact` key) remains the deterministic path.

> **Product layer - Slice A.3 (the context-serving API: any model can call it).** Cogniflow
> is now a standalone **context engine** (`cogniflow.context.serve_context`): query in,
> temporally-correct *context* out - **facts, not a generated answer** - for any model to
> put in its own prompt. The `as_of` axis is a first-class parameter (the differentiator,
> exposed). The honesty labels survive to the output: each served fact carries its
> `valid_at`/`invalid_at`, provenance, and a `valid_at_source` confidence
> (`authoritative`/`derived`/`none`, plus the raw label) - persisted on the edge at write
> and round-tripped to the serving boundary, proven end to end by a live test. Two
> read-only, self-hostable surfaces (`cogniflow.serving`): an **MCP server** (`[mcp]`
> extra) as the primary "any agent calls it" path, and **HTTP/REST** (`[serve]` extra)
> underneath - both run in the caller's environment, so data never leaves. The extraction
> floor ships in every response's `notes`. See [docs/CONTEXT_API.md](docs/CONTEXT_API.md).
> (The human/compliance audit dashboard is the separate Slice B.)

> **Product layer - Slice B (the audit/replay dashboard: the moat made visible).** A
> **read-only** window onto the belief ledger for a human (`cogniflow.serving.create_audit_app`,
> `[serve]` extra, self-hostable): current beliefs, the **event-time** axis (what was true at
> T - scrub April->7-day, July->28-day), the **system-time replay** scrubber (what the system
> *knew* at S), and provenance traces - over the four `AuditLedger` methods, no write verb
> exposed. **The centerpiece is the un-knowing made visible:** scrubbed to before a
> supersession, a fact reads believed-then and un-superseded, never with its current
> `invalid_at` - the engine un-knows and the UI renders only what it returns, so present
> knowledge cannot leak backward (asserted by the hardest test in the slice). Provenance
> resolves the episode UUID to the human-readable document name from stored linkage
> (G1) - an unresolvable UUID is shown as a UUID, never guessed - and each fact shows its
> `valid_at_source` confidence. This is the one screen no plain RAG can build, because it is
> driven by system-time replay nobody else has. See
> [docs/AUDIT_DASHBOARD.md](docs/AUDIT_DASHBOARD.md).

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
