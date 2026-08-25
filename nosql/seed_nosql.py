"""
Seeds the semi-structured ("NoSQL") side of the data model:

  startup_profiles     - free-form tags, pitch deck links, social handles
  mentor_feedback      - open-text feedback tied to a mentorship_session
  press_mentions       - unstructured news/press hits per startup
  social_engagement     - time-series-ish social metrics snapshots per startup
  investor_notes       - free-text due-diligence notes per investor/startup pair

These pair with the relational tables (join by startup_id / mentor_id /
investor_id) and represent the kind of variable-shape data that's a poor
fit for rigid SQL columns, which is why it lives in a document store.

Run: python nosql/seed_nosql.py
"""
import random
import csv
import os
import sys
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nosql.nosql_store import get_store

random.seed(7)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

TAGS_POOL = [
    "women-led", "first-gen-founder", "climate-focused", "AI-enabled", "B2B",
    "B2C", "community-driven", "underrepresented-founder", "veteran-owned",
    "immigrant-founded", "remote-first", "bootstrapped", "revenue-positive",
]
PRESS_OUTLETS = ["Boston Globe", "BostInno", "TechCrunch", "Boston Business Journal", "WBUR", "Axios Boston"]
FEEDBACK_SNIPPETS = [
    "Founder came in with a clear ask and left with a concrete next step.",
    "Session ran long because the pitch deck needed a full narrative rework.",
    "Strong grasp of the market, needs help translating that into a financial model.",
    "Great energy, but customer acquisition costs are still not well understood.",
    "Follow-up requested on legal structure before next fundraising conversation.",
    "Mentor flagged a possible investor introduction after this session.",
    "Founder was well prepared; conversation moved quickly into growth tactics.",
    "Recommended narrowing target customer segment before the next demo day.",
]


def read_ids(table):
    path = os.path.join(DATA_DIR, f"{table}.csv")
    with open(path) as f:
        reader = csv.DictReader(f)
        return list(reader)


COLLECTIONS = [
    "startup_profiles", "mentor_feedback", "press_mentions",
    "social_engagement", "investor_notes",
]


def main():
    store = get_store()
    startups = read_ids("startups")
    sessions = read_ids("mentorship_sessions")
    investors = read_ids("investors")

    # Wipe first so re-running the seeder (or setup.sh) is idempotent rather
    # than appending a duplicate copy of every document.
    for name in COLLECTIONS:
        store[name].delete_many({})

    # startup_profiles
    profiles = []
    for s in startups:
        profiles.append({
            "startup_id": int(s["startup_id"]),
            "tags": random.sample(TAGS_POOL, k=random.randint(2, 5)),
            "pitch_deck_url": f"https://decks.example.com/{s['name'].lower().replace(' ', '-')}.pdf",
            "website": f"https://www.{s['name'].split()[0].lower()}.com",
            "social_handles": {
                "linkedin": f"linkedin.com/company/{s['name'].split()[0].lower()}",
                "instagram": f"@{s['name'].split()[0].lower()}"
            },
        })
    store["startup_profiles"].insert_many(profiles)

    # mentor_feedback (tied to a subset of mentorship sessions)
    feedback_docs = []
    for sess in random.sample(sessions, k=min(400, len(sessions))):
        feedback_docs.append({
            "session_id": int(sess["session_id"]),
            "startup_id": int(sess["startup_id"]),
            "mentor_id": int(sess["mentor_id"]),
            "feedback_text": random.choice(FEEDBACK_SNIPPETS),
            "flagged_for_followup": random.random() < 0.2,
        })
    store["mentor_feedback"].insert_many(feedback_docs)

    # press_mentions (sparse - not every startup gets covered)
    press_docs = []
    for s in random.sample(startups, k=int(len(startups) * 0.4)):
        for _ in range(random.randint(1, 3)):
            press_docs.append({
                "startup_id": int(s["startup_id"]),
                "outlet": random.choice(PRESS_OUTLETS),
                "headline": f"{s['name']} raises eyebrows in the {s['industry']} space",
                "published_date": (
                    dt.date.fromisoformat(s["founded_date"]) +
                    dt.timedelta(days=random.randint(30, 900))
                ).isoformat(),
                "sentiment": random.choice(["positive", "neutral", "positive", "mixed"]),
            })
    store["press_mentions"].insert_many(press_docs)

    # social_engagement snapshots
    engagement_docs = []
    for s in startups:
        engagement_docs.append({
            "startup_id": int(s["startup_id"]),
            "snapshot_date": dt.date(2026, 8, 1).isoformat(),
            "followers": {
                "linkedin": random.randint(50, 12000),
                "instagram": random.randint(20, 25000),
            },
            "monthly_website_visits": random.randint(100, 50000),
        })
    store["social_engagement"].insert_many(engagement_docs)

    # investor_notes (sparse due-diligence notes)
    notes_docs = []
    for inv in random.sample(investors, k=int(len(investors) * 0.6)):
        for s in random.sample(startups, k=random.randint(1, 3)):
            notes_docs.append({
                "investor_id": int(inv["investor_id"]),
                "startup_id": int(s["startup_id"]),
                "note": random.choice([
                    "Strong founding team, watching for traction in next 2 quarters.",
                    "Passed for now - market too early, revisit post Series A.",
                    "Requested updated cap table before next conversation.",
                    "Very interested, scheduling partner meeting.",
                ]),
                "logged_date": dt.date(2026, random.randint(1, 8), random.randint(1, 28)).isoformat(),
            })
    store["investor_notes"].insert_many(notes_docs)

    print("NoSQL collections seeded:")
    for name in COLLECTIONS:
        print(f"  {name}: {store[name].count_documents()} documents")


if __name__ == "__main__":
    main()
