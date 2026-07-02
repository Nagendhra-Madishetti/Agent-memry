# Cogniflow

**A bi-temporal RAG platform: any document in → a cited, temporally-correct answer out — plus
the one thing a plain RAG cannot do: replay what the system *believed* at a past moment.**

Cogniflow stores every fact on two independent time axes — *when it was true in the world*
(event time) and *when the system learned it* (system time) — so it can answer not just "what
is true now?" and "what was true in 2020?" but **"what did we believe in 2021, before the 2022
correction — without leaking that correction backward?"** That last question is the wedge.

---

## The one thing plain RAG can't do

Take one fact that changed. Acme Corp's HQ was **Boston** (2019 filing), then **Denver** (2022
filing).

| Question | Plain / vector RAG | Valid-time ("temporal") RAG | **Cogniflow** |
|---|---|---|---|
| Where is Acme HQ **now**? | ✅ Denver | ✅ Denver | ✅ Denver |
| Where was it **in 2020**? | ❌ | ✅ Boston | ✅ Boston |
| What did we **believe in 2021**, before the 2022 filing? | ❌ | ❌ | ✅ **Boston** (Denver un-known) |
| Show the timeline + who superseded what | ❌ | partial | ✅ provenance + audit |

The third row is **system-time replay**. It needs an independent record of *when each fact was
learned*, and the discipline not to let a later correction leak into a past belief. That is the
tested centerpiece of this system.

---

## 60-second demo (from nothing)

Prereqs: Docker. No `.env`, no keys — the hero scenario is **key-free**.

```bash
git clone https://github.com/Nagendhra-web/cogniflow && cd cogniflow
docker compose up -d --build       # FalkorDB + API + web, secure-by-default (auth ON)
bash scripts/demo.sh               # waits for the API, seeds Acme, asserts the four questions
# docker compose logs -f           # follow logs   ·   docker compose down   # stop it
```

`scripts/demo.sh` prints (and asserts):

```
Q1  now              -> Denver
Q2  as of 2020       -> Boston
Q3  replay(2021)     -> Boston   << the 2022 Denver correction is un-known
Q4  timeline         -> Boston (2019 report) superseded by Denver (2022 press release)
```

Then open the **live scrubber** at <http://localhost:3000/playground> and drag the system-time
slider across 2022 — the answer flips Boston↔Denver in front of you.

> **Deployment honesty:** `docker compose up` stands up and *runs* the whole stack in a
> **local / trusted environment**. It is **not** production-grade HA — the in-memory session
> state and in-process queue don't survive multi-replica; k8s/Helm/scale are a later phase.
> The API is **baseline-secure** (bearer-token auth, token-scoped access, rate limits, upload
> caps) — see [SECURITY.md](SECURITY.md). Not "enterprise-ready."

---

## Architecture

```
                          ┌─────────────────────────────────────────────┐
   PDF / MD / text  ─────▶│ INGEST   documents.py                        │
   (+ the date true)      │  parse → structure-preserving chunk → Episode│
                          └───────────────┬─────────────────────────────┘
                                          ▼
                          ┌─────────────────────────────────────────────┐
                          │ WRITE    (LLM extract + contradiction resolve)│
                          │  stamps  valid_at/invalid_at   (EVENT time)   │
                          │          created_at/expired_at (SYSTEM time)  │
                          │  contradiction → expire old + superseded_by   │
                          └───────────────┬─────────────────────────────┘
                                          ▼
                          ┌─────────────────────────────────────────────┐
                          │ STORE    FalkorDB (per-group graph) | Neo4j   │
                          └──────┬───────────────────────────┬──────────┘
             relevance path      │                           │  audit path (direct temporal scan)
                                 ▼                           ▼
        ┌──────────────────────────────────┐   ┌──────────────────────────────────────┐
        │ RETRIEVE serve_context           │   │ REPLAY   core/audit.py                 │
        │  as-of validity-filter → rank    │   │  event_time_query(T)   valid_at ≤ T    │
        │  → grounded generation → cited   │   │  system_time_replay(S) created_at ≤ S  │
        │    answer + provenance           │   │    + un-know post-S corrections        │
        └──────────────────────────────────┘   │  → /api/audit/* + the web scrubber     │
                                                └────────────────────────────────────────┘
```

**The core is dependency-free.** `cogniflow.core` imports only the standard library; heavy deps
(`graphiti-core`, `falkordb`, `llama-index-core`) are pulled in by *backends* and *bridges*
behind optional extras. Embedder, reranker, generation model, and graph backend are each
config-selected, fail-loud plugs.

### How the bitemporal model works
- **Event time** `[valid_at, invalid_at)` — when the fact was true in the world. Answers "as of
  2020."
- **System time** `[created_at, expired_at)` — when the system learned/retracted it. Answers
  "what did we believe at S," and is what makes the un-knowing replay possible.
- A correction **supersedes**: the old fact gets `invalid_at` (event) **and** `expired_at`
  (system) plus a `superseded_by` back-link, stamped at write time.

---

## Use it on your own documents (local — your data never leaves)

```bash
# 1. real generation + retrieval need providers (the seeded hero does not). Put keys in .env:
cp .env.example .env    # set COGNIFLOW_LLM_API_KEY and, for semantic retrieval, an embedder

# 2. ingest a document with the date its facts were true, then ask at different as-of dates
TOKEN=cogniflow-demo-token
curl -H "Authorization: Bearer $TOKEN" -F session_id=mine -F reference_time=2019-01-01 \
     -F file=@your_report.pdf http://localhost:8000/api/ingest
```

**Retrieval quality needs a real embedder.** Cogniflow boots on the key-free `hash` embedder so
the engine runs dependency-free — but hash is **meaning-blind** (lexical, not semantic) and it
**warns loudly** at startup and in every response until you configure one:

- **key-free, needs torch** — `pip install -e ".[embeddings]"`, then `COGNIFLOW_EMBEDDER=bge-m3-local`
- **dependency-light, needs a key** — `COGNIFLOW_EMBEDDER=bge-m3` + `COGNIFLOW_EMBEDDER_API_KEY=…`

A real embedder fixes **retrieval** (which facts come back). It does **not** lift the prose
**extraction** floor (how well facts are pulled from prose — bounded by the LLM, and labeled per
fact via `valid_at_source`). See [docs/EMBEDDERS.md](docs/EMBEDDERS.md).

---

## API (curl) — against the secure-by-default server

Every route but `/api/health` needs the bearer token (`COGNIFLOW_API_TOKENS`; the compose
provisions `cogniflow-demo-token`). A session is scoped to the token that created it.

```bash
TOKEN=cogniflow-demo-token
API=http://localhost:8000
H="Authorization: Bearer $TOKEN"

# seed the demo (key-free), then the four questions:
curl -H "$H" -X POST "$API/api/demo/seed"
curl -H "$H" "$API/api/audit/current?session_id=demo_acme"                    # -> Denver (now)
curl -H "$H" "$API/api/audit/event?session_id=demo_acme&as_of=2020-06-01"     # -> Boston (event time)
curl -H "$H" "$API/api/audit/replay?session_id=demo_acme&system_time=2021-06-01"  # -> Boston (system-time replay)
curl -H "$H" "$API/api/audit/timeline/demo-belief-boston?session_id=demo_acme"    # -> provenance + supersession

# temporally-correct CONTEXT for your own model (facts, not a generated answer):
curl -H "$H" -H 'Content-Type: application/json' -X POST "$API/api/context" \
     -d '{"session_id":"mine","query":"Where is Acme headquartered?","as_of":"2020-06-01"}'
```

Omit the token and you get `401`; use another token against a session you don't own and you get
`403`.

---

## The invariant we enforce

The headline property is the **un-knowing invariant**: replaying to a system-time *before* a
correction returns what was believed then, and does **not** leak the later invalidation
backward. It is enforced two ways:

- **Pure** — [`tests/test_audit_replay.py`](tests/test_audit_replay.py) /
  [`tests/test_validity_policy.py`](tests/test_validity_policy.py) assert the reconstruction as
  deterministic functions (no infra).
- **Live** — [`tests/integration/test_replay_seeded.py`](tests/integration/test_replay_seeded.py)
  asserts it end-to-end against a real **FalkorDB**, **no LLM key**, in the `replay-invariant`
  job of [`.github/workflows/ci.yml`](.github/workflows/ci.yml). If replay ever leaks a later
  correction into the past, CI goes red.

```
replay(2021) -> Boston   (invalid_at un-known; the 2022 move not yet learned)
replay(2023) -> Denver   (the correction is now known)
```

---

## Honest limitations

- **Baseline security, not enterprise.** Bearer auth + scoped access + rate limits + upload
  caps — safe in a *trusted environment*. RBAC, access-audit logging, GDPR deletion, SOC2, and
  hardened isolation are not here. See [SECURITY.md](SECURITY.md).
- **Not production HA.** In-memory session dict + in-process queue break multi-replica; k8s and
  the scale re-architecture are a later phase.
- **Contradiction detection is an LLM call** — reliable on structured input, best-effort on
  prose. `verify_fact`'s recall on the current model is a measured floor, tracked in
  [PROJECT_STATUS.md](PROJECT_STATUS.md).
- **Generation grounding is prompt-instruction only** (no post-hoc faithfulness check yet).
- Full defect ledger: [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

---

## Development

```bash
pip install -e ".[dev]"     # dependency-free core + dev tools
ruff check .
pytest                      # contracts + conformance; integration tests self-skip without infra
```

Extend it without touching core — [CONTRIBUTING.md](CONTRIBUTING.md),
[docs/EXTENDING.md](docs/EXTENDING.md). Design and status: [PROJECT_STATUS.md](PROJECT_STATUS.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
