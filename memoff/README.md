# Crowmem — Mem Off adapter

Wraps the [Crowmem](https://github.com/rwberndt/Crowmem) memory engine (a standalone FastAPI service) as a Claude Code plugin + the five entrant-contract scripts, so it can run as a Track 1 entrant in [Mem Off](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-mem-off-hackathon-YYYY-MM-DD) (no dated event is scheduled yet — the folder name is still a `YYYY-MM-DD` template placeholder — but the harness code inside it (`harness/`, `challenge/`, `examples/`) is real and runnable).

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

| Piece | Status |
|---|---|
| `memory.yml` | **Validated for real.** Fetched the actual `harness/memoff/manifest.py` + `memory.schema.json` from the hackathon repo and ran `manifest.load_arm("memoff/memory.yml")` against them directly (both files are dependency-free stdlib+jsonschema+pyyaml, no Docker/harness install needed) — passes schema validation, and every script it references (`install`, `wipe`, `wipe_check`, `wait`, `receipt`, `usage`) resolves to a real file. |
| `check_submission.py`'s folder-level checks | **Ran for real** (fetched `check_submission.py` + `__init__.py`, called `check_folder()` directly against `memoff/`). One finding: `SUBMISSION.md` is missing, which short-circuits the check before it reaches the `report/memoff-report.{md,json}` checks — those are separately known-missing (see below). |
| `wipe.sh`, `wipe_check.sh`, `wait.sh` | Verified live against the real running Crowmem service: seeded a project, confirmed `wipe_check` fails non-empty, wiped, confirmed it passes empty. |
| `receipt.sh` (both the stashed-id and most-recent-retrieval fallback paths) | Verified live against real recall data. |
| `usage.sh` (since-timestamp tracking across repeated calls) | Verified live: two calls, second call only reports the delta. |
| All five hook scripts (`session_start.py` … `session_end.py`) | Verified by feeding each one crafted stdin JSON matching the hook schema confirmed from Claude Code's docs (not from running inside an actual session), piped against the live API. Full chain confirmed: a memory's `utility_score`/`successful_use_count` moved after a simulated `SessionStart → UserPromptSubmit → PostToolUse → Stop → SessionEnd` sequence. |
| `plugin/.claude-plugin/plugin.json`, `plugin/hooks/hooks.json` | Written to the exact schema Claude Code's plugin-components docs show, **not loaded into a real Claude Code session** (`claude --plugin-dir plugin` was never run here). |
| `install.sh` | **Not run anywhere.** Linux-only (apt/postgresql/pgvector build steps); this session is Windows. Written to documented Debian/Ubuntu conventions and the entrant contract, with explicit fallbacks (package pgvector → build from source; `python3.12` → generic `python3`), but genuinely unverified. |
| `cognee-report` / `memoff-memory-report` skill integration | **Not implemented at all.** These are organiser-provided skills referenced by the contract; `harness/` doesn't vendor them (they come from the separate `cognee-integrations` plugin), so their actual install/invocation shape is still unknown. |
| `harness/arms/{claude-mem,cognee}` reference entrants | Not read. Worth diffing our `memory.yml`/scripts against these for conventions before a real submission. |
| The full `memoff run`/`memoff pilot` sequencer, `harness/tests/test_harness.py` | Not run. Would need the harness installed (`cd harness && uv venv && uv pip install -e ".[dev]"`) plus xitkit and Docker (per `harness/Dockerfile`) — not attempted in this session. |

### Reproducing the manifest/submission check

```sh
# fetch the two dependency-free files (needs the gh CLI + a GitHub token)
gh api repos/topoteretes/cognee-hackathons/contents/cognee-mem-off-hackathon-YYYY-MM-DD/harness/memoff/manifest.py --jq '.content' | base64 -d > /tmp/memoff/memoff/manifest.py
gh api repos/topoteretes/cognee-hackathons/contents/cognee-mem-off-hackathon-YYYY-MM-DD/harness/memoff/memory.schema.json --jq '.content' | base64 -d > /tmp/memoff/memoff/memory.schema.json
gh api repos/topoteretes/cognee-hackathons/contents/cognee-mem-off-hackathon-YYYY-MM-DD/harness/memoff/check_submission.py --jq '.content' | base64 -d > /tmp/memoff/memoff/check_submission.py
gh api repos/topoteretes/cognee-hackathons/contents/cognee-mem-off-hackathon-YYYY-MM-DD/harness/memoff/__init__.py --jq '.content' | base64 -d > /tmp/memoff/memoff/__init__.py
pip install jsonschema pyyaml

python -c "
import sys; sys.path.insert(0, '/tmp/memoff')
from memoff import manifest, check_submission
from pathlib import Path
print(manifest.load_arm('memoff/memory.yml'))
print(check_submission.check_folder(Path('memoff').resolve(), Path('.').resolve()))
"
```

## Known, stated limitation: the outcome signal

Hooks never see the private grader's verdict — `SessionEnd`'s payload is just `{"reason": ...}`. The reinforcement signal comes from `Stop`'s `last_assistant_message`, parsed for a `STATUS: implemented|not_implemented` line (the same self-report the harness's own claim-scoring reads). A confidently-wrong agent could reinforce a memory that didn't actually help. This is a best-effort proxy, not ground truth — stated in `memory.yml`'s `notes`, not hidden.

## Before actually submitting

1. Pin `memory.yml`'s `version` and `_common.sh`'s `CROWMEM_PINNED_COMMIT` to a real Crowmem commit SHA (left as `PIN_ME` during active development since it would go stale every commit).
2. Run `install.sh` on an actual clean Linux container and fix whatever it gets wrong — it has not been executed anywhere.
3. Load `plugin/` into a real Claude Code session (`claude --plugin-dir plugin`) and confirm hooks actually fire and inject context as expected — the hook scripts were only tested by hand-feeding them JSON, not by an actual session invoking them.
4. Install and wire in the `cognee-report` and `memoff-memory-report` skills per `CONTRACT.md` point 5/6 — currently entirely missing.
5. Copy `templates/SUBMISSION.md` into this folder and fill it (team name, handles, links — only you can fill these honestly) — confirmed via `check_submission.py` as the one missing piece on the folder-structure side.
6. Run the `memoff-memory-report` skill's wrap-up to produce `report/memoff-report.md` + `.json` — `check_submission.py` requires both and checks the JSON carries `type: memoff-memory-report`.
7. Actually run `memoff run` / `memoff pilot` (the real sequencer, `harness/` installed with `uv`, Docker per `harness/Dockerfile`, xitkit checked out) at least once — everything above is still pre-flight checks, not an end-to-end benchmark run.

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
