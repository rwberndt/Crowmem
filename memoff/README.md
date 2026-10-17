# Crowmem — Mem Off adapter

Wraps the [Crowmem](https://github.com/rwberndt/Crowmem) memory engine (a standalone FastAPI service) as a Claude Code plugin + the five entrant-contract scripts, so it can run as a Track 1 entrant in [Mem Off](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-mem-off-hackathon-YYYY-MM-DD) (no dated event exists yet — that folder is still a template).

## Layout

```
memoff/
  memory.yml            # entrant manifest
  install.sh            # clones pinned Crowmem commit, provisions Postgres+pgvector, starts the service
  wipe.sh / wipe_check.sh
  wait.sh
  receipt.sh / _receipt.py
  usage.sh / _usage.py
  _common.sh            # shared sh config (CROWMEM_HOME, ports, store-name helper)
  plugin/
    .claude-plugin/plugin.json
    hooks/
      hooks.json
      _client.py          # shared HTTP client, stdlib-only
      session_start.py     # prime context before the issue text arrives
      user_prompt_submit.py  # real goal-conditioned recall on the issue text
      post_tool_use.py       # every tool call becomes an episode
      stop.py                 # captures the agent's self-reported STATUS line
      session_end.py          # reports the outcome for every recall this issue made
```

## What's verified vs. assumed

Everything below was checked against the real running Crowmem service on this machine. **Nothing was run against the actual Mem Off harness or a real Claude Code plugin load** — no dated event exists yet to test against, and `claude --plugin-dir` wasn't exercised end-to-end here.

| Piece | Status |
|---|---|
| `wipe.sh`, `wipe_check.sh`, `wait.sh` | Verified live: seeded a project, confirmed `wipe_check` fails non-empty, wiped, confirmed it passes empty. |
| `receipt.sh` (both the stashed-id and most-recent-retrieval fallback paths) | Verified live against real recall data. |
| `usage.sh` (since-timestamp tracking across repeated calls) | Verified live: two calls, second call only reports the delta. |
| All five hook scripts (`session_start.py` … `session_end.py`) | Verified by feeding each one crafted stdin JSON matching the hook schema confirmed from Claude Code's docs (not from running inside an actual session), piped against the live API. Full chain confirmed: a memory's `utility_score`/`successful_use_count` moved after a simulated `SessionStart → UserPromptSubmit → PostToolUse → Stop → SessionEnd` sequence. |
| `plugin/.claude-plugin/plugin.json`, `plugin/hooks/hooks.json` | Written to the exact schema Claude Code's plugin-components docs show, **not loaded into a real Claude Code session** (`claude --plugin-dir plugin` was never run here). |
| `install.sh` | **Not run anywhere.** Linux-only (apt/postgresql/pgvector build steps); this session is Windows. Written to documented Debian/Ubuntu conventions and the entrant contract, with explicit fallbacks (package pgvector → build from source; `python3.12` → generic `python3`), but genuinely unverified. |
| `memory.yml` | Hand-written to `templates/memory.yml` and `CONTRACT.md`; never validated against `harness/memoff/memory.schema.json` (not available to us — the schema file lives inside the harness, which doesn't exist yet). |
| `cognee-report` / `memoff-memory-report` skill integration | **Not implemented at all.** These are organiser-provided skills referenced by the contract but not inspected — their actual install/invocation shape is unknown. |

## Known, stated limitation: the outcome signal

Hooks never see the private grader's verdict — `SessionEnd`'s payload is just `{"reason": ...}`. The reinforcement signal comes from `Stop`'s `last_assistant_message`, parsed for a `STATUS: implemented|not_implemented` line (the same self-report the harness's own claim-scoring reads). A confidently-wrong agent could reinforce a memory that didn't actually help. This is a best-effort proxy, not ground truth — stated in `memory.yml`'s `notes`, not hidden.

## Before actually submitting

1. Pin `memory.yml`'s `version` and `_common.sh`'s `CROWMEM_PINNED_COMMIT` to a real Crowmem commit SHA (left as `PIN_ME` during active development since it would go stale every commit).
2. Run `install.sh` on an actual clean Linux container and fix whatever it gets wrong — it has not been executed anywhere.
3. Load `plugin/` into a real Claude Code session (`claude --plugin-dir plugin`) and confirm hooks actually fire and inject context as expected — the hook scripts were only tested by hand-feeding them JSON, not by an actual session invoking them.
4. Install and wire in the `cognee-report` and `memoff-memory-report` skills per `CONTRACT.md` point 5/6 — currently entirely missing.
5. Validate `memory.yml` against the real `memory.schema.json` once the harness repo exists.

## Manual local testing (what this folder's scripts were actually checked against)

With the Crowmem FastAPI service running locally (`uvicorn app.main:app`):

```sh
export CROWMEM_BASE_URL=http://127.0.0.1:8001   # or 8765 once a real install.sh ran
export MEMOFF_MEMORY_STORE=my-test-store
sh wipe.sh && sh wipe_check.sh
# ... POST /events and /recall against the running service ...
sh receipt.sh
sh usage.sh
```

For the hooks, pipe crafted JSON matching the schemas in Claude Code's hooks docs directly into each script, e.g.:

```sh
echo '{"session_id":"s1","hook_event_name":"UserPromptSubmit","user_input":"..."}' \
  | CROWMEM_BASE_URL=http://127.0.0.1:8001 MEMOFF_MEMORY_STORE=my-test-store python plugin/hooks/user_prompt_submit.py
```
