# Demo OKF bundle (a concept that moves)

A minimal, spec-conformant OKF bundle in two versions, supplied because Google's sample
bundles are **static catalog metadata** - nothing in them changes, so they can't show
supersession on their own. Here the same concept (`metrics/weekly_active_users`) is
**redefined between versions**:

- `v1/` - timestamp **2026-03-01**, WAU = trailing **7-day** distinct users.
- `v2/` - timestamp **2026-06-01**, WAU = trailing **28-day** distinct users.

This is exactly what real git-versioned OKF bundles produce over time (a new file + a
`log.md` entry) - and exactly what OKF cannot answer: *"what did this metric mean in
March?"*. Each concept also carries an optional `fact` extension key (OKF permits arbitrary
keys) so the redefinition is a precise, deterministic temporal fact; without it, the body
is ingested as prose and the engine extracts what it can.

`demo/okf_head_to_head.py` ingests v1 then v2 into Agent Memry and runs the controlled
comparison against a plain vector RAG over the same files.
