# Corvid Memory Architecture

A goal-conditioned, adaptive memory engine for AI agents. Inspired by corvid cognition: it doesn't archive everything it sees — it decides what's worth remembering (salience gating), derives durable memories and beliefs from raw episodes, activates memories by goal/context rather than text similarity alone, and strengthens or decays them based on real outcomes.

Full design spec: `corvid_memory_architecture_implementation_guide.md` (the implementation guide this project follows).

## Architecture at a glance

```
event -> salience gate -> durable memory/belief extraction -> goal-conditioned
activation -> bounded working memory -> agent action -> outcome -> reinforcement/decay
```

- **FastAPI service** (`app/`) owns all state: Postgres + pgvector for episodes/memories/beliefs, Anthropic Claude for structured extraction/classification (never mutates state directly), fastembed for local embeddings.
- **MCP server** (`mcp_server/`) is a thin, stateless process that calls the FastAPI service over HTTP, exposing the same operations as tools for a coding agent (e.g. Claude Code) to use live.

## Setup

Prerequisites: Python 3.12, Docker Desktop.

```powershell
# 1. Install dependencies (uv)
py -3.12 -m pip install --user uv
py -3.12 -m uv sync

# 2. Start Postgres+pgvector
docker compose up -d

# 3. Configure environment
copy .env.example .env
# edit .env and set ANTHROPIC_API_KEY (required for real memory/belief extraction)

# 4. Run migrations
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Note: if port 5432 is already taken by another local Postgres install, `docker-compose.yml` maps the container to host port **5433** instead — already reflected in `.env.example`.

## Running the service

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

Endpoints: `POST /events`, `POST /recall`, `POST /outcomes`, `GET/PATCH /memories`, `GET /beliefs`, `GET /episodes`, `POST /admin/jobs/decay`.

## Running the MCP server

With the API running:

```powershell
$env:CORVID_API_BASE_URL = "http://localhost:8000"
.\.venv\Scripts\python.exe -m mcp_server
```

Exposes `remember_event`, `recall_memories`, `report_outcome`, `confirm_or_correct_memory`, `query_beliefs` as MCP tools (stdio transport) — point Claude Code's MCP config at this command to drive the memory engine live during a demo.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Unit tests (`tests/unit/`) exercise the salience/activation/decay/reinforcement/belief-transition formulas as pure functions with hand-built fixtures. Integration tests (`tests/integration/`) hit the API with a real test Postgres (`corvid_test`, auto-created/migrated by `tests/conftest.py`) and a fake, deterministic LLM client — no live Anthropic calls in CI. Scenario tests (`tests/scenarios/`) reproduce the implementation guide's three demos end-to-end.

## Demos

Each script hits the **live** running API and needs a real `ANTHROPIC_API_KEY` set on the server process (extraction otherwise gracefully no-ops and the demo won't have anything to recall).

```powershell
$env:CORVID_API_BASE_URL = "http://localhost:8000"
.\.venv\Scripts\python.exe scripts\demos\demo_1_production_migration.py   # context-triggered recall over semantic RAG
.\.venv\Scripts\python.exe scripts\demos\demo_2_utility_learning.py       # memories strengthen/weaken from real usage
.\.venv\Scripts\python.exe scripts\demos\demo_3_belief_supersession.py    # episodic + semantic belief integration
```

## Configuration

All tunable weights/thresholds (salience, activation, working-memory bounds, reinforcement deltas, decay rates, trust defaults) live in `config/scoring.yaml` — nothing is hardcoded. Env vars (`.env`): `DATABASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_EXTRACTION_MODEL` (default `claude-haiku-4-5`), `EMBEDDING_PROVIDER`/`EMBEDDING_DIM` (default `fastembed`/384), `CORVID_API_BASE_URL` (read by the MCP server).

## Core invariants

1. Episodes are immutable (no update/delete route exists for them).
2. Utility is not truth confidence — `/outcomes` only ever moves `utility_score`/`strength`; confidence only changes via `/memories/{id}/confirm|correct`.
3. The LLM never directly mutates memory state (`app/llm/` has zero imports of `app.db`/`app.repositories`) — it only returns validated Pydantic objects that deterministic service code applies.
4. Working memory is always bounded (`config/scoring.yaml: working_memory.max_slots/max_tokens`).
5. Retrieval ranking always considers goal/context, never similarity alone (`app/services/activation_service.py` combines eight weighted terms).
6. Every ranking decision is explainable — each `/recall` response includes `reason`s per memory, persisted in `retrieval_log` for audit.
7. High-risk memories decay slowly and never drop below a protected floor (`app/services/decay_service.py`).
