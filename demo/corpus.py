"""Swappable corpus for the head-to-head demo. Edit freely and re-run.

Each entry has `text` (what plain RAG indexes). Entries that are time-stamped facts
also carry a `fact` triple + `year` (what Agent Memry ingests, with the year as the
fact's valid-from). Distractors have only `text`.

The scenario: Acme Corp was HQ'd in Boston for years (lots of Boston text), then quietly
moved to Denver (one understated update). Plain similarity retrieval favors the abundant,
keyword-matching Boston text and, under top-k, drops the lone Denver update - so RAG
answers the stale city. Agent Memry knows Denver superseded Boston and answers the current
one (and, asked as-of an earlier date, correctly answers Boston).
"""

from __future__ import annotations

QUESTION = "Where is Acme Corp headquartered?"

CORPUS = [
    {
        "text": "Acme Corp is headquartered in Boston.",
        "fact": {"subject": "Acme Corp", "predicate": "HEADQUARTERED_IN", "object": "Boston"},
        "year": 2015,
    },
    {"text": "Acme Corp's Boston headquarters houses its engineering and finance teams."},
    {"text": "The Boston headquarters of Acme Corp is widely regarded as iconic."},
    {"text": "Acme Corp was founded in Boston and its headquarters has been there for years."},
    {"text": "Visitors to Acme Corp often tour the company's Boston headquarters lobby."},
    {
        "text": "Acme Corp recently relocated its principal offices to Denver.",
        "fact": {"subject": "Acme Corp", "predicate": "HEADQUARTERED_IN", "object": "Denver"},
        "year": 2024,
    },
]
