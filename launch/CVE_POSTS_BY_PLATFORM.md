# Platform versions of the CVE post

Publish the long write-up somewhere you control first (a blog, or a GitHub gist, or
`docs/` on the repo). Everything below links to it. Do not link straight to the repo:
the write-up is the thing people want, and the repo is one click further.

---

## Hacker News

Submit as a **link** to the write-up, not a text post.

**Title** (factual, no adjectives, under 80 chars):

```
NoSQL injection in LangGraph's Mongo checkpointer allowed cross-tenant reads
```

Alternative if you want the framing rather than the specifics:

```
Your AI agent's memory is a database query (CVE-2026-48121)
```

Then post this as the **first comment**, immediately after submitting:

```
Author here. Short version: LangGraph's MongoDB checkpointer took thread_id,
checkpoint_ns and checkpoint_id out of config.configurable and passed them into a
find() query without enforcing they were strings. Send {"$gt": ""} as a thread_id
and the scoping predicate matches every thread instead of one.

CVSS 6.7, medium, and it deserves the accurate description: you need to already be
an authenticated user, and you are only exposed if user input reaches those
identifiers. If your thread_id is server-issued you were never vulnerable. But
"pass the conversation id from the front end" is the obvious way to build a
multi-tenant assistant, which is what made it worth reporting.

What I find interesting is less the bug class (CWE-943, we have been fixing this
since the 2000s) than where it turned up. Checkpoint state is the least reviewed
and most sensitive data in an agent stack: raw user input, tool arguments, tool
results, uncommitted writes. And nothing at the call site looks like a query. You
write graph.invoke() and a Mongo filter document gets assembled three layers down.

Fixed in @langchain/langgraph-checkpoint-mongodb 1.3.1. The LangChain maintainers
were fast and did not argue about severity.

Happy to answer questions about the disclosure or the checkpointer internals.
```

**Timing**: weekday, roughly 08:00 to 10:00 US Eastern. Then stay at your desk for two hours
and answer every comment. Traction in the first 30 minutes decides whether it is seen at all.

---

## r/netsec

Strict rules, technical audience, link post only. Read the sidebar before submitting.

**Title**:

```
CVE-2026-48121: NoSQL injection in LangGraph's MongoDB checkpointer allowing cross-tenant agent state disclosure
```

No comment needed beyond answering questions. r/netsec dislikes anything that reads as
marketing, so do not mention your own project unless somebody asks what you work on.

---

## r/LocalLLaMA and r/LangChain

More conversational. Text post works here.

**Title**:

```
Found a cross-tenant data leak in LangGraph's Mongo checkpointer (CVE-2026-48121). Worth checking your thread_id handling.
```

**Body**:

```
Fixed in @langchain/langgraph-checkpoint-mongodb 1.3.1, so upgrade first.

The checkpointer used thread_id / checkpoint_ns / checkpoint_id from
config.configurable directly in a Mongo find() without enforcing string types.
Because Mongo treats objects as query operators, passing {"$gt": ""} as a
thread_id turned the scoping filter into a match-everything filter, returning
checkpoint state, metadata and pending writes from other threads.

You are affected if you accept a thread id from the client and pass it through to
invoke() or stream() without validating it as a string. You are fine if your ids
are server-issued.

The general lesson I took from it: agent checkpoints hold the messiest data in the
whole system (raw user text, tool call arguments, tool results) and most teams have
never looked at what is in them. Worth a five minute audit even if you are not on
Mongo.

Write-up with the full detail: [link]
```

---

## LinkedIn

Narrative, first person, no code block (LinkedIn mangles them).

```
I reported a vulnerability in LangGraph earlier this year. It is now published as
CVE-2026-48121, and the write-up is finally out.

The bug: the MongoDB checkpointer, the component that persists an AI agent's state
between turns, trusted the conversation identifiers it was given. If your
application passed a thread id straight from a request body, a caller could send a
MongoDB operator instead of an id and read checkpoint data belonging to other
tenants.

Medium severity, and I want to be accurate about that: you had to be an
authenticated user, and applications using server-issued identifiers were never
exposed. But accepting the conversation id from the client is the obvious way to
build a multi-tenant assistant, so it was worth reporting.

What stayed with me is where it was. We have twenty years of instinct that says
sanitize what goes into a database. We have almost none that says an agent's memory
is a database. You call invoke() and a query gets built three layers below you.

Agent checkpoints hold raw user input, tool arguments, tool results and uncommitted
writes. It is the least reviewed data in most AI stacks and often the most
sensitive. If you run agents in production, it is worth spending five minutes
tracing where your thread id comes from.

Credit to the LangChain maintainers, who fixed it quickly and without friction.

Full write-up: [link]
```

---

## X / Twitter thread

```
1/ I reported a cross-tenant data leak in LangGraph's MongoDB checkpointer.
Published as CVE-2026-48121. Fixed in 1.3.1.

The short version: an AI agent's memory is a database query, and almost nobody
treats it like one.

2/ The checkpointer pulled thread_id, checkpoint_ns and checkpoint_id out of
config.configurable and passed them into find() without enforcing string types.

3/ MongoDB does not distinguish an identifier from an operator. Send this as a
thread_id:

  { "$gt": "" }

Greater than the empty string means everything. The filter that was supposed to
scope one conversation now matches all of them.

4/ Returned: checkpoint state, metadata, pending writes. From other tenants.

CVSS 6.7 medium. You needed to be an authenticated user, and you were only exposed
if client input reached those identifiers. Server-issued ids were always safe.

5/ CWE-943 is an old bug class. What is new is the location.

Checkpoints hold raw user text, tool call arguments, tool results, uncommitted
writes. The least reviewed data in the stack.

6/ And nothing at the call site looks dangerous. You write graph.invoke(). The
Mongo filter is assembled three layers down. The vulnerability is a type
assumption, not a query, and type assumptions are invisible in code review.

7/ If you run agents in production: trace your thread_id from the HTTP request to
persistence. Validate it as a string, not just as present.

Full write-up: [link]
```

---

## Do not

- Post the same text to five places within an hour. Space them across days.
- Lead with your own project anywhere. The finding is the story; the project is the
  signature at the bottom.
- Overstate severity. Somebody in the comments will read the CVSS vector and correct you,
  and that exchange is the only thing anyone will remember.
