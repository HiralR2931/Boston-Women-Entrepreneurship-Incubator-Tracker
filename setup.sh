#!/usr/bin/env bash
# One-command setup: creates a virtualenv, installs deps, generates seed data,
# builds the SQLite DB and NoSQL JSON collections, then launches the Streamlit app.
set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON="${PYTHON:-python3}"

# A venv keeps this working on Homebrew/system Pythons, which refuse a bare
# `pip install` with "error: externally-managed-environment" (PEP 668).
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Creating virtualenv in $VENV_DIR ..."
  "$PYTHON" -m venv "$VENV_DIR"
fi
VENV_PY="$VENV_DIR/bin/python"

echo "Installing Python dependencies..."
"$VENV_PY" -m pip install --upgrade pip --quiet
"$VENV_PY" -m pip install -r requirements.txt --quiet

echo "Generating seed data..."
(cd database && "../$VENV_PY" seed_data.py)

echo "Building SQLite database..."
(cd database && "../$VENV_PY" init_db.py)

echo "Seeding NoSQL collections..."
"$VENV_PY" nosql/seed_nosql.py

echo ""
echo "Setup complete. Launching the app at http://localhost:8501 ..."
exec "$VENV_DIR/bin/streamlit" run app/Home.py
