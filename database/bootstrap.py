"""
First-run dataset bootstrap.

Only source is tracked in git -- the generated CSVs, the SQLite database, and
the NoSQL JSON collections are all produced by the seed scripts and ignored.
That keeps the repository clean, but it means a fresh checkout (a clone, or a
deploy on a hosting platform that builds straight from the repo) starts with no
data at all.

ensure_data() closes that gap: if the dataset is missing it runs the same three
seed steps `setup.sh` runs, so the app comes up with a working dataset on first
launch and is a no-op on every launch after that.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "incubator.db")
COLLECTIONS_DIR = os.path.join(BASE_DIR, "nosql", "collections")

EXPECTED_COLLECTIONS = [
    "startup_profiles", "mentor_feedback", "press_mentions",
    "social_engagement", "investor_notes",
]


def data_ready():
    """True when both the SQL and NoSQL sides are already populated."""
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        return False
    return all(
        os.path.exists(os.path.join(COLLECTIONS_DIR, f"{name}.json"))
        for name in EXPECTED_COLLECTIONS
    )


def ensure_data(log=print):
    """
    Build the dataset if it isn't there yet. Returns True if it generated
    anything, False if there was nothing to do.

    Skipped entirely when DATABASE_URL points at a real MySQL instance, since
    in that case the data lives in the external database rather than in the
    bundled SQLite file.
    """
    if os.environ.get("DATABASE_URL", "").strip().startswith("mysql"):
        return False
    if data_ready():
        return False

    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    log("No dataset found -- generating it (first run only)...")

    # Each module seeds `random` at import time (seed_data with 42, seed_nosql
    # with 7), so import each one immediately before running it. Importing them
    # all up front would let a later seed() reset the generator before an
    # earlier main() runs, producing a different dataset than the documented
    # reproducible one.
    from database import seed_data
    seed_data.main()

    from database import init_db
    init_db.main()

    from nosql import seed_nosql
    seed_nosql.main()

    log("Dataset ready.")
    return True


if __name__ == "__main__":
    if not ensure_data():
        print("Dataset already present -- nothing to do.")
