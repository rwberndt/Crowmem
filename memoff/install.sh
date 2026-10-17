#!/bin/sh
# Installs Crowmem on a clean Linux container. Idempotent: safe to re-run.
#
# UNVERIFIED on the real Mem Off runner image -- written to the documented
# entrant contract and Debian/Ubuntu conventions, never executed against
# the actual container. See memoff/README.md.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

echo "[crowmem] install.sh starting"

SUDO=""
if [ "$(id -u)" != "0" ] && command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
fi

mkdir -p "$CROWMEM_HOME"

# --- system packages ---
if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update -y
  $SUDO apt-get install -y git build-essential curl postgresql postgresql-contrib postgresql-server-dev-all \
    python3.12 python3.12-venv \
    || $SUDO apt-get install -y git build-essential curl postgresql postgresql-contrib postgresql-server-dev-all \
       python3 python3-venv
else
  echo "[crowmem] WARNING: apt-get not found; assuming git/python3/postgresql are already present" >&2
fi

PYTHON_BIN="$(command -v python3.12 || command -v python3)"
echo "[crowmem] using python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

if ! command -v uv >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi

# --- pgvector: try the packaged extension, else build from source ---
if ! $SUDO -u postgres psql -tAc "SELECT 1 FROM pg_available_extensions WHERE name='vector'" 2>/dev/null | grep -q 1; then
  echo "[crowmem] pgvector package not available; building from source"
  if [ ! -d "$CROWMEM_HOME/pgvector" ]; then
    git clone --depth 1 https://github.com/pgvector/pgvector.git "$CROWMEM_HOME/pgvector"
  fi
  ( cd "$CROWMEM_HOME/pgvector" && (make clean >/dev/null 2>&1 || true) && make && $SUDO make install )
fi

# --- postgres service (best-effort across init systems) ---
$SUDO service postgresql start 2>/dev/null \
  || $SUDO pg_ctlcluster "$(pg_lsclusters -h 2>/dev/null | awk 'NR==1{print $1}')" \
            "$(pg_lsclusters -h 2>/dev/null | awk 'NR==1{print $2}')" start 2>/dev/null \
  || echo "[crowmem] WARNING: could not confirm postgresql service start; assuming it's already running" >&2

# --- role + database (idempotent) ---
$SUDO -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='corvid'" | grep -q 1 \
  || $SUDO -u postgres psql -c "CREATE ROLE corvid LOGIN PASSWORD 'corvid';"
$SUDO -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='crowmem_memoff'" | grep -q 1 \
  || $SUDO -u postgres psql -c "CREATE DATABASE crowmem_memoff OWNER corvid;"

# --- pinned engine checkout ---
if [ ! -d "$CROWMEM_ENGINE_DIR" ]; then
  git clone "$CROWMEM_REPO_URL" "$CROWMEM_ENGINE_DIR"
fi
(
  cd "$CROWMEM_ENGINE_DIR"
  git fetch origin
  git checkout "$CROWMEM_PINNED_COMMIT"
)

# --- venv + deps ---
if [ ! -d "$CROWMEM_VENV" ]; then
  uv venv --python "$PYTHON_BIN" "$CROWMEM_VENV"
fi
( cd "$CROWMEM_ENGINE_DIR" && uv pip install --python "$CROWMEM_VENV/bin/python" -e . )

# --- engine environment, read by migrations and the service below ---
cat > "$CROWMEM_HOME/engine.env" <<EOF
DATABASE_URL=postgresql+psycopg://corvid:corvid@127.0.0.1:5432/crowmem_memoff
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
ANTHROPIC_EXTRACTION_MODEL=claude-haiku-4-5
EMBEDDING_PROVIDER=fastembed
EMBEDDING_DIM=384
SCORING_CONFIG_PATH=$CROWMEM_ENGINE_DIR/config/scoring.yaml
EOF

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "[crowmem] WARNING: ANTHROPIC_API_KEY is not set -- extraction will silently no-op" >&2
fi

# --- migrations ---
(
  cd "$CROWMEM_ENGINE_DIR"
  set -a
  . "$CROWMEM_HOME/engine.env"
  set +a
  "$CROWMEM_VENV/bin/python" -m alembic upgrade head
)

# --- start the service (idempotent) ---
if [ -f "$CROWMEM_PIDFILE" ] && kill -0 "$(cat "$CROWMEM_PIDFILE")" 2>/dev/null; then
  echo "[crowmem] engine already running (pid $(cat "$CROWMEM_PIDFILE"))"
else
  (
    cd "$CROWMEM_ENGINE_DIR"
    set -a
    . "$CROWMEM_HOME/engine.env"
    set +a
    nohup "$CROWMEM_VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port "$CROWMEM_PORT" \
      > "$CROWMEM_HOME/uvicorn.log" 2>&1 &
    echo $! > "$CROWMEM_PIDFILE"
  )
fi

i=0
while [ "$i" -lt 15 ]; do
  if curl -sf "$CROWMEM_BASE_URL/health" >/dev/null 2>&1; then
    echo "[crowmem] engine is up at $CROWMEM_BASE_URL"
    exit 0
  fi
  i=$((i + 1))
  sleep 1
done

echo "[crowmem] ERROR: engine did not become healthy at $CROWMEM_BASE_URL -- see $CROWMEM_HOME/uvicorn.log" >&2
exit 1
