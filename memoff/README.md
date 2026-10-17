# Crowmem — Mem Off adapter

Wraps the [Crowmem](https://github.com/rwberndt/Crowmem) memory engine (a standalone FastAPI service) as a Claude Code plugin + the five entrant-contract scripts, so it can run as a Track 1 entrant in [Mem Off](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-mem-off-hackathon-YYYY-MM-DD). The organiser folder still has a `YYYY-MM-DD` placeholder name, but the harness code inside it (`harness/`, `challenge/`, `examples/`) is real.

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
      user_prompt_submit.py  # goal-conditioned recall on the actual issue text
      post_tool_use.py       # selected code edits and explicit tool failures
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
| Registered hooks (`UserPromptSubmit`, `PostToolUse`, `Stop`, `SessionEnd`) | The original five-hook plugin ran in a real Claude Code session for public Issue 1 on 2026-10-17: 34 episodes, 5 durable memories, and no context injection on the cold store. The current plugin skips SessionStart's redundant empty-query recall, sends selected code edits and explicit failures, and ignores routine reads and successful shell output. A second local Issue 1 Claude Code run completed with the optimized plugin; see the evidence below. |
| `plugin/.claude-plugin/plugin.json`, `plugin/hooks/hooks.json` | `claude plugin validate` passed, and `claude --plugin-dir` loaded the hooks in the Issue 1 run on Windows. This has not been repeated in the organiser's Linux image. |
| `install.sh` | **Passed a clean Linux container test** using `python:3.14-slim`, the current installer, and a temporary local commit of this engine. It installed Python 3.12 via uv, PostgreSQL and the packaged pgvector, ran all migrations, and reached `/health`. The organiser's full harness image remains untested. |
| `cognee-report` / `memoff-memory-report` skill integration | **Not implemented.** The reporting skill is in the hackathon repository and `cognee-report` comes with the cognee plugin; neither has been installed into this repo for a submission. |
| `harness/arms/{claude-mem,cognee}` reference entrants | Not read. Worth diffing our `memory.yml`/scripts against these for conventions before a real submission. |
| The full `memoff run`/`memoff pilot` sequencer, `harness/tests/test_harness.py` | Not run. Would need the harness installed (`cd harness && uv venv && uv pip install -e ".[dev]"`) plus xitkit and Docker (per `harness/Dockerfile`) — not attempted in this session. |

## Local optimization evidence

The original Issue 1 run sent all 34 tool calls to `/events` (15 Bash, 10 Read, 5 Grep, 4 Edit). Five events reached extraction, causing 10 Haiku calls and $0.025841 of memory-system spend. Its later manual Issue 8 recall mostly returned transient test and deprecation notes.

The current hook runs only for edit tools and Bash, and sends an event only for a code edit or an explicitly reported failure. It extracts code changes as a short unified diff and skips the separate belief model call because `/recall` does not return beliefs. In a fresh local probe, one representative path-resolution edit took 4.1 seconds through the hook, cost $0.002624 for one Haiku call, and yielded two memories about absolute paths and deterministic sorting. A manual Issue 8 recall returned both. This is an isolated probe, not a new agent run or an official benchmark comparison.

A later local Issue 1 agent run with the optimized plugin met the Linux visible target (6 failed / 774 passed) in 33 turns. It produced one tool episode, two memories, one Haiku extraction call ($0.002867), and no cold-start injection. Agent reported cost was $0.662285 and combined reported cost $0.665152, compared with $0.670104 combined for the earlier Crowmem run. The new agent changed only `xitkit/services.py` while the earlier agent also added three tests. These are single runs with different agent paths and authentication routes, so the small total-cost difference is not a reliable benchmark delta. A separate Issue 8 recall returned the two path-resolution memories, but no Issue 8 agent was run. The diff formatter was tightened after this completed run to drop whitespace-only hunks; tests cover that final change.

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
2. Run `install.sh` in the organiser's full harness image. A plain `python:3.14-slim` clean install and health check passed, but the full image may differ.
3. Repeat the optimized plugin run on the organiser's Linux harness and confirm a later issue receives relevant injected context. A local single-edit probe produced a memory and a manual Issue 8 recall retrieved it; no Issue 8 agent or grader was run.
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
