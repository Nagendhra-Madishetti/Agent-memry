# Your agent's memory is just a database query

**CVE-2026-48121: a NoSQL injection in LangGraph's MongoDB checkpointer let one tenant read
another tenant's agent state.**

Fixed in `@langchain/langgraph-checkpoint-mongodb@1.3.1`. If you are on 1.3.0 or earlier and
you let user input reach `config.configurable`, upgrade first and read this after.

---

## The short version

LangGraph persists agent state through a checkpointer. The MongoDB implementation took the
identifiers that scope a conversation, `thread_id`, `checkpoint_ns` and `checkpoint_id`, out
of `config.configurable` and passed them into a `find()` query without enforcing that they
were strings.

MongoDB does not care whether a value is a string or a query operator. So an identifier that
arrives as an object is not an identifier any more, it is a filter:

```ts
graph.invoke(input, {
  configurable: {
    thread_id: { $gt: "" },     // matches every thread
    checkpoint_ns: { $ne: null },
  },
});
```

`{ $gt: "" }` is greater than the empty string, which is to say: everything. The query that
was supposed to scope a read to one conversation now scopes it to all of them, and returns
checkpoint state, metadata and pending writes belonging to other tenants.

This is CWE-943, the same class of bug the web has been fixing since the 2000s, arriving in a
new place: the memory layer of an AI agent.

## Be clear about the severity

CVSS 6.7, medium. It deserves an accurate description rather than a scary one:

- It is **not** remote code execution and it is **not** unauthenticated. The attacker needs
  to already be a user of your application.
- It is **not** exploitable in every deployment. If your `thread_id` comes from a session or
  a server-issued identifier, or your API layer validates it as a string, you were never
  exposed.
- It **is** a confidentiality break in exactly the deployments people actually build:
  multi-tenant assistants where a thread identifier is accepted from the client, because
  passing the conversation id from the front end is the obvious thing to do.

That last case is common enough to matter, and the data at stake is unusually sensitive.

## Why this class of bug lands differently in agent memory

An injection into an ordinary table leaks rows of that table. An injection into an agent
checkpoint leaks something else: the working state of a conversation.

Checkpoints hold what the user told the assistant, what the assistant concluded, tool call
arguments and results, and pending writes that have not been committed yet. In a support
assistant that is account details. In an internal copilot it is whatever the employee pasted
in. It is the least structured and least reviewed data in the system, and it is exactly the
data a memory layer exists to keep.

We have decades of instinct that says *sanitize what goes into the database*. We have very
little instinct that says *the agent's memory is a database*, because it does not look like
one from the application code. You call `graph.invoke()`. You are thinking about the graph,
not about a Mongo filter document being assembled three layers down.

That gap between how it reads and what it does is where this bug lived.

## Why it was easy to miss

Nothing in the calling code looks like string concatenation. There is no query being built by
hand, no obvious injection point. The identifier is passed through a config object into a
library, and the library passes it to the driver.

The vulnerability is in a type assumption, not in a query. `thread_id` was assumed to be a
string because it is always a string when you write the code yourself. It stops being a
string the moment it arrives from an HTTP request body, where JSON gives the caller objects
for free.

Type assumptions are invisible in review. Nobody reads `find({ thread_id })` and thinks
"but what if that is an object".

## The fix

Version 1.3.1 enforces the type at the boundary, coercing and validating the checkpoint
identifiers before they reach the query rather than trusting the caller. The maintainers
(credit to `etairl` for the remediation and `hntrl` for review) turned it around promptly.

## What to check in your own stack

This bug is specific to one package, but the shape of it is not. Worth checking today:

1. **Does user input reach your checkpointer's identifiers?** Trace `thread_id` from the HTTP
   request to the persistence layer. If a request body can set it, validate it as a string at
   the edge.
2. **Are you validating types, not just presence?** A schema that says `thread_id` is required
   and a schema that says `thread_id` is a `string` are different schemas. Only one of them
   stops this.
3. **Does your tenant boundary exist below the identifier?** Scoping by a caller-supplied id
   is not isolation. If the query has no server-side tenant predicate, one bad identifier is
   the whole boundary.
4. **What is actually in your checkpoints?** Most teams have never looked. Retention and
   access rules should follow that answer, not the assumption that it is "just conversation
   state".

## Disclosure

Reported privately through GitHub Security Advisories, fixed by the maintainers, published as
[GHSA-98xf-r82g-9mhx](https://github.com/advisories/GHSA-98xf-r82g-9mhx) /
[CVE-2026-48121](https://nvd.nist.gov/vuln/detail/CVE-2026-48121) on 12 June 2026. Affects
`@langchain/langgraph-checkpoint-mongodb <= 1.3.0`, patched in 1.3.1.

The LangChain team handled it the way you would want: no friction, no argument about
severity, a fix and an advisory.

---

## Why I was looking

I build memory infrastructure for AI agents, so I read other people's memory layers closely.
Persistence code is where the interesting failures are, because it is the part everyone
treats as plumbing.

If you want the same paranoia applied to temporal correctness rather than injection, that is
[RAGBrain](https://github.com/Nagendhra-Madishetti/ragbrain): a bi-temporal RAG layer that
records when each fact was true and when the system learned it, so replaying a past moment
cannot be contaminated by knowledge that arrived later.

```bash
pip install ragbrain
```

```python
from ragbrain import MemoryLedger

db = MemoryLedger()
db.remember("Acme HQ is Boston", key="acme.hq", valid_at="2019-01-01")
db.remember("Acme HQ is Denver", key="acme.hq", valid_at="2022-01-01")

db.answer("Where is Acme HQ?")                       # Denver
db.answer("Where is Acme HQ?", as_of="2020-01-01")   # Boston
db.replay("2021-06-01")[0].statement                 # Boston, the correction is un-known
```
