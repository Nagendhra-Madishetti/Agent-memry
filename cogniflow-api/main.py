"""Cogniflow Playground API - the live backend for the web app's real-world test.

Upload real documents -> ingest through the ACTUAL Cogniflow pipeline (pypdf/markdown parse ->
Episodes -> temporal store) -> ask with an as-of time -> temporally-correct context + cited
answer + the audit/replay ledger. Each browser session is an isolated FalkorDB group.

Run (needs FalkorDB + .env with COGNIFLOW_LLM_* and COGNIFLOW_EMBEDDER_API_KEY):
    pip install -e ".[all,serve]"
    python -m uvicorn cogniflow-api.main:app --port 8000
or  python cogniflow-api/main.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# make the src/ package importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from cogniflow.backends.embedders import available_embedders  # noqa: E402
from cogniflow.backends.graphiti_falkordb import (  # noqa: E402
    GraphitiFalkorDBBackend,
    GraphitiFalkorDBConfig,
)
from cogniflow.context import serve_context  # noqa: E402
from cogniflow.documents import ingest_document  # noqa: E402
from cogniflow.generation import generate_answer  # noqa: E402
from cogniflow.generators import (  # noqa: E402
    OpenAICompatibleGenerator,
    available_generators,
    create_generator,
    create_generator_from_env,
)
from cogniflow.rerankers import available_rerankers  # noqa: E402
from cogniflow.serving.audit import serialize_belief, serialize_trace  # noqa: E402

DEFAULT_EMBEDDER = "bge-m3" if os.getenv("COGNIFLOW_EMBEDDER_API_KEY") else "hash"

app = FastAPI(title="Cogniflow Playground API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "COGNIFLOW_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# session_id -> {"config": {...}, "backend": GraphitiFalkorDBBackend | None}
_SESSIONS: dict[str, dict] = {}
_GENERATOR = None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # accept ISO-8601 with a trailing "Z" (Python <3.11's fromisoformat rejects it)
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _generator():
    global _GENERATOR
    if _GENERATOR is None:
        _GENERATOR = create_generator_from_env()  # fail-loud if no key
    return _GENERATOR


def _build_generator(gen: dict) -> OpenAICompatibleGenerator:
    """Build a session generation model. A custom base_url (bring-your-own provider or a local
    model like Ollama/vLLM) goes straight to the OpenAI-compatible client - no preset and no key
    required (local endpoints ignore it). Otherwise use a named preset (fail-loud on bad name)."""
    base_url = (gen.get("base_url") or "").strip()
    if base_url:
        return OpenAICompatibleGenerator(
            api_key=(gen.get("api_key") or "").strip() or "local",
            model=(gen.get("model") or "").strip() or "local-model",
            base_url=base_url,
        )
    return create_generator(
        gen.get("name") or "nvidia",
        api_key=gen.get("api_key"),
        model=gen.get("model"),
    )


def _sess_generator(session_id: str):
    """The generation model for a session: a custom/selected plugin if configured, else the
    environment default. Built lazily and cached per session."""
    sess = _SESSIONS.get(session_id)
    gen = sess and sess["config"].get("gen")
    if sess and gen:
        if sess.get("generator") is None:
            sess["generator"] = _build_generator(gen)
        return sess["generator"]
    return _generator()


async def _backend(session_id: str) -> GraphitiFalkorDBBackend:
    if not session_id:
        raise HTTPException(422, "session_id required")
    sess = _SESSIONS.setdefault(session_id, {"config": {}, "backend": None})
    if sess["backend"] is None:
        c = sess["config"]
        cfg = GraphitiFalkorDBConfig.from_env(group_id=f"pg_{session_id}")
        cfg.embedder = c.get("embedder", DEFAULT_EMBEDDER)
        if c.get("embedder_model"):
            cfg.embedder_model = c["embedder_model"]
        if c.get("embedder_base_url"):
            cfg.embedder_base_url = c["embedder_base_url"]
        if c.get("embedder_api_key"):
            cfg.embedder_api_key = c["embedder_api_key"]
        cfg.retrieval_policy = c.get("retrieval_policy", "default")
        cfg.retrieval_params = c.get("retrieval_params", {})
        backend = GraphitiFalkorDBBackend(cfg)
        await backend.setup()
        sess["backend"] = backend
    return sess["backend"]


async def _names(backend: GraphitiFalkorDBBackend, beliefs) -> dict[str, str]:
    uuids = [u for b in beliefs for u in b.provenance]
    return await backend.resolve_episodes(uuids) if uuids else {}


# ---- models ----------------------------------------------------------------
class Query(BaseModel):
    session_id: str
    query: str
    as_of: str | None = None
    top_k: int = 6


class TextIngest(BaseModel):
    session_id: str
    text: str
    title: str = "note"
    reference_time: str | None = None


class PluginConfig(BaseModel):
    session_id: str
    embedder: str | None = None
    reranker: str | None = None  # "" / None = off (default retrieval policy)
    # custom provider / local model (OpenAI-compatible base_url + model + key). Covers both
    # "bring your own API provider" and "point at a local model" (e.g. Ollama/vLLM).
    embedder_model: str | None = None
    embedder_base_url: str | None = None
    embedder_api_key: str | None = None
    reranker_model: str | None = None
    reranker_base_url: str | None = None
    reranker_api_key: str | None = None
    # generation model (AI model plugin) — selectable + custom/local endpoint
    generator: str | None = None
    generator_model: str | None = None
    generator_base_url: str | None = None
    generator_api_key: str | None = None


# ---- routes ----------------------------------------------------------------
@app.get("/api/health")
async def health() -> dict:
    falkordb = False
    try:
        from falkordb import FalkorDB

        FalkorDB(host="localhost", port=6379).select_graph("__ping__").query("RETURN 1")
        falkordb = True
    except Exception:
        pass
    return {
        "status": "ok",
        "falkordb": falkordb,
        "llm": bool(os.getenv("COGNIFLOW_LLM_API_KEY")),
        "embedder": DEFAULT_EMBEDDER,
    }


@app.get("/api/plugins")
async def plugins() -> dict:
    return {
        "embedders": available_embedders(),
        "rerankers": ["off", *available_rerankers()],
        "generators": available_generators(),
        "backends": ["falkordb", "neo4j"],
        "defaults": {"embedder": DEFAULT_EMBEDDER, "reranker": "off"},
    }


@app.post("/api/session")
async def new_session() -> dict:
    sid = uuid.uuid4().hex[:12]
    _SESSIONS[sid] = {"config": {}, "backend": None}
    return {"session_id": sid}


@app.post("/api/config")
async def set_config(cfg: PluginConfig) -> dict:
    sess = _SESSIONS.setdefault(cfg.session_id, {"config": {}, "backend": None})
    c = sess["config"]
    if cfg.embedder:
        c["embedder"] = cfg.embedder
        c["embedder_model"] = cfg.embedder_model
        c["embedder_base_url"] = cfg.embedder_base_url
        c["embedder_api_key"] = cfg.embedder_api_key
    if cfg.reranker is not None:
        if cfg.reranker in ("", "off", "default"):
            c["retrieval_policy"] = "default"
            c["retrieval_params"] = {}
        else:
            params: dict = {"reranker": cfg.reranker}
            if cfg.reranker_model:
                params["model"] = cfg.reranker_model
            if cfg.reranker_base_url:
                params["base_url"] = cfg.reranker_base_url
            if cfg.reranker_api_key:
                params["api_key"] = cfg.reranker_api_key
            c["retrieval_policy"] = "reranker"
            c["retrieval_params"] = params
    if cfg.generator == "managed":
        c.pop("gen", None)  # back to the platform default (env-configured)
        sess["generator"] = None
    elif cfg.generator:
        c["gen"] = {
            "name": cfg.generator,
            "model": cfg.generator_model,
            "base_url": cfg.generator_base_url,
            "api_key": cfg.generator_api_key,
        }
        sess["generator"] = None  # rebuild the generator on next answer
    # force rebuild with new config on next use
    if sess["backend"] is not None:
        await sess["backend"].close()
        sess["backend"] = None
    return {"ok": True, "config": {k: v for k, v in sess["config"].items() if k != "gen"}}


@app.post("/api/ingest")
async def ingest(
    session_id: str = Form(...),
    reference_time: str | None = Form(None),
    file: UploadFile = File(...),
) -> dict:
    backend = await _backend(session_id)
    suffix = Path(file.filename or "upload.txt").suffix or ".txt"
    data = await file.read()
    tmp = Path(tempfile.gettempdir()) / f"cf_{uuid.uuid4().hex}{suffix}"
    tmp.write_bytes(data)
    try:
        receipts = await ingest_document(backend, tmp, reference_time=_parse_dt(reference_time))
    finally:
        tmp.unlink(missing_ok=True)
    created = sum(len(r.created_belief_ids) for r in receipts)
    invalidated = sum(len(r.invalidated_belief_ids) for r in receipts)
    return {
        "document": file.filename,
        "chunks": len(receipts),
        "facts_created": created,
        "facts_superseded": invalidated,
    }


@app.post("/api/ingest-text")
async def ingest_text(body: TextIngest) -> dict:
    from cogniflow.core.types import Episode, utc_now

    backend = await _backend(body.session_id)
    ref = _parse_dt(body.reference_time) or utc_now()
    ep = Episode(
        id=f"{body.title}-{uuid.uuid4().hex[:6]}",
        content=body.text,
        reference_time=ref,
        source="text",
        source_description=body.title,
        metadata={"valid_at_source": "provided" if body.reference_time else "none"},
    )
    receipt = await backend.write(ep)
    return {
        "document": body.title,
        "facts_created": len(receipt.created_belief_ids),
        "facts_superseded": len(receipt.invalidated_belief_ids),
    }


@app.post("/api/context")
async def context(q: Query) -> dict:
    backend = await _backend(q.session_id)
    res = await serve_context(backend, q.query, as_of=_parse_dt(q.as_of), top_k=q.top_k)
    return res.to_dict()


@app.post("/api/answer")
async def answer(q: Query) -> dict:
    backend = await _backend(q.session_id)
    res = await generate_answer(
        backend, q.query, _sess_generator(q.session_id), as_of=_parse_dt(q.as_of), top_k=q.top_k
    )
    return res.to_dict()


@app.get("/api/audit/current")
async def audit_current(session_id: str) -> dict:
    backend = await _backend(session_id)
    beliefs = await backend.event_time_query(datetime.now(timezone.utc))
    names = await _names(backend, beliefs)
    return {"beliefs": [serialize_belief(b, names) for b in beliefs]}


@app.get("/api/audit/event")
async def audit_event(session_id: str, as_of: str) -> dict:
    backend = await _backend(session_id)
    beliefs = await backend.event_time_query(_parse_dt(as_of))
    names = await _names(backend, beliefs)
    return {"as_of": as_of, "beliefs": [serialize_belief(b, names) for b in beliefs]}


@app.get("/api/audit/replay")
async def audit_replay(session_id: str, system_time: str) -> dict:
    backend = await _backend(session_id)
    beliefs = await backend.system_time_replay(_parse_dt(system_time))
    names = await _names(backend, beliefs)
    return {"system_time": system_time, "beliefs": [serialize_belief(b, names) for b in beliefs]}


@app.get("/api/audit/provenance/{belief_id}")
async def audit_provenance(belief_id: str, session_id: str) -> dict:
    backend = await _backend(session_id)
    trace = await backend.provenance_trace(belief_id)
    uuids = list(trace.asserted_by) + (
        [trace.superseded_by_episode] if trace.superseded_by_episode else []
    )
    names = await backend.resolve_episodes(uuids) if uuids else {}
    return serialize_trace(trace, names)


@app.post("/api/reset")
async def reset(session_id: str) -> dict:
    sess = _SESSIONS.get(session_id)
    if sess and sess["backend"] is not None:
        await sess["backend"].close()
    try:
        from falkordb import FalkorDB

        FalkorDB(host="localhost", port=6379).select_graph(f"pg_{session_id}").delete()
    except Exception:
        pass
    _SESSIONS[session_id] = {"config": sess["config"] if sess else {}, "backend": None}
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
