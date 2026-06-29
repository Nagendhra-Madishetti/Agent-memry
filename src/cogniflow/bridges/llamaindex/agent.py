"""Minimal agent wiring (T4): a LlamaIndex agent whose only tool is a
TemporalGraphRetriever, with the TemporalValidityPostprocessor in the chain.

``as_of`` is bound per agent (via the retriever + postprocessor), so the same
question asked of two agents built at two different as_of values is the heartbeat
through the agent path.

Agent choice: ReActAgent, not FunctionAgent. The configured LLM (MiniMax-M3 via an
OpenAI-compatible endpoint) does not emit native tool calls, which FunctionAgent
requires. ReActAgent drives any chat LLM via a text Thought/Action/Observation loop
and parses the tool call from text. Swap to FunctionAgent if a function-calling
model is configured.
"""

from __future__ import annotations

from datetime import datetime

from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.tools import RetrieverTool
from llama_index.llms.openai_like import OpenAILike

from ...backends.graphiti_falkordb import GraphitiFalkorDBConfig
from ...core.contracts import AsyncSubstrate
from ...writeback import WriteBackQueue
from .postprocessor import TemporalValidityPostprocessor
from .retriever import TemporalGraphRetriever
from .tools import make_record_observation_tool

_SYSTEM_PROMPT = (
    "You answer questions about time-stamped facts. You MUST call the "
    "temporal_facts tool exactly once, then answer in one short sentence using "
    "only the fact it returns. If it returns nothing, say you do not know."
)

_RECORD_SYSTEM_PROMPT = (
    "You record new time-stamped facts. When the user states a new fact, call the "
    "record_observation tool exactly once with: a one-sentence statement, and when "
    "they can be identified, subject, predicate, obj, and valid_at (a year or ISO "
    "date). Then reply with the tool's acknowledgement. Do not answer from your own "
    "knowledge."
)


def make_llm(config: GraphitiFalkorDBConfig, max_tokens: int = 2048) -> OpenAILike:
    """Build an OpenAI-compatible chat LLM from the backend config.

    ``max_tokens`` must be set: MiniMax-M3 (a reasoning model) returns empty
    choices on the async path when it is unbounded, so leave generous headroom for
    reasoning plus the answer.
    """
    return OpenAILike(
        model=config.llm_model,
        api_key=config.llm_api_key,
        api_base=config.llm_base_url,
        is_chat_model=True,
        is_function_calling_model=True,
        temperature=0,
        max_tokens=max_tokens,
        timeout=120,
    )


def build_temporal_agent(
    substrate: AsyncSubstrate,
    *,
    as_of: datetime | None,
    llm: OpenAILike,
    top_k: int = 5,
    include_expired: bool = False,
) -> ReActAgent:
    retriever = TemporalGraphRetriever(
        substrate, as_of=as_of, top_k=top_k, include_expired=include_expired
    )
    # P1: inject the substrate's own validity instance so both call sites share one object.
    postprocessor = TemporalValidityPostprocessor(
        validity_policy=getattr(substrate, "validity", None),
        as_of=as_of,
        include_expired=include_expired,
    )
    tool = RetrieverTool.from_defaults(
        retriever=retriever,
        node_postprocessors=[postprocessor],
        name="temporal_facts",
        description=(
            "Look up time-stamped facts about an entity (such as a company's "
            "headquarters) as of a fixed date."
        ),
    )
    return ReActAgent(tools=[tool], llm=llm, system_prompt=_SYSTEM_PROMPT)


def build_recording_agent(
    queue: WriteBackQueue,
    group_id: str,
    *,
    llm: OpenAILike,
) -> ReActAgent:
    """An agent whose only tool is record_observation (seam d, the write half)."""
    tool = make_record_observation_tool(queue, group_id)
    return ReActAgent(tools=[tool], llm=llm, system_prompt=_RECORD_SYSTEM_PROMPT)
