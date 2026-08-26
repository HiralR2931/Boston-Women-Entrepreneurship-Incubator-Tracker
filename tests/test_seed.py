"""
Tests for the seed pipeline.

Two properties matter here and both have bitten this project before:

  - Reproducibility. The README promises `random.seed(42)` makes the dataset
    reproducible. That only holds if nothing reseeds the generator partway
    through, which is easy to break by importing the seed modules in the wrong
    order (seed_nosql seeds with 7 at import time).
  - Idempotency. setup.sh runs the seeders, so running setup twice must not
    append a second copy of every row and document.
"""
import hashlib
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from database import bootstrap

DATA_DIR = os.path.join(ROOT, "data")
CSV_TABLES = [
    "startups", "mentors", "investors", "events",
    "funding_rounds", "investments", "mentorship_sessions", "event_participation",
]


def _digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _run(*args):
    result = subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result


@pytest.fixture(scope="module", autouse=True)
def dataset():
    bootstrap.ensure_data(log=lambda *a, **k: None)


def test_dataset_is_reported_ready():
    assert bootstrap.data_ready()


def test_seed_data_is_reproducible():
    """Re-seeding must reproduce byte-identical CSVs."""
    before = {t: _digest(os.path.join(DATA_DIR, f"{t}.csv")) for t in CSV_TABLES}
    _run("database/seed_data.py")
    after = {t: _digest(os.path.join(DATA_DIR, f"{t}.csv")) for t in CSV_TABLES}
    assert before == after


def test_bootstrap_reproduces_the_same_dataset_as_the_seed_scripts():
    """
    The app bootstraps a fresh checkout by importing the seed modules rather
    than shelling out to them. Each module seeds `random` at import time
    (seed_data with 42, seed_nosql with 7), so importing them in the wrong
    order lets a later seed() reset the generator before an earlier main()
    runs -- silently producing a different dataset than the documented one.

    Deleting the database first is what makes this a real test: ensure_data()
    short-circuits when the data is already present, so without this the
    bootstrap path would never actually run.
    """
    before = {t: _digest(os.path.join(DATA_DIR, f"{t}.csv")) for t in CSV_TABLES}

    os.remove(bootstrap.DB_PATH)
    assert not bootstrap.data_ready(), "removing the DB should force a rebuild"

    try:
        _run("-c", "import database.bootstrap as b; b.ensure_data(log=lambda *a, **k: None)")
        after = {t: _digest(os.path.join(DATA_DIR, f"{t}.csv")) for t in CSV_TABLES}
        assert before == after
    finally:
        if not os.path.exists(bootstrap.DB_PATH):
            _run("database/init_db.py")


def test_nosql_seeding_is_idempotent():
    """Running the NoSQL seeder twice must not duplicate documents."""
    collections_dir = os.path.join(ROOT, "nosql", "collections")

    def counts():
        out = {}
        for name in bootstrap.EXPECTED_COLLECTIONS:
            with open(os.path.join(collections_dir, f"{name}.json")) as f:
                out[name] = len(json.load(f))
        return out

    _run("nosql/seed_nosql.py")
    first = counts()
    _run("nosql/seed_nosql.py")
    second = counts()

    assert first == second
    assert all(v > 0 for v in first.values())


def test_every_startup_has_exactly_one_profile_document():
    """A duplicated seed run would show up here first."""
    import csv

    with open(os.path.join(DATA_DIR, "startups.csv")) as f:
        startup_ids = {int(r["startup_id"]) for r in csv.DictReader(f)}

    with open(os.path.join(ROOT, "nosql", "collections", "startup_profiles.json")) as f:
        profiles = json.load(f)

    assert len(profiles) == len(startup_ids)
    assert {p["startup_id"] for p in profiles} == startup_ids
