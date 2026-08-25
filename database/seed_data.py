"""
Seed data generator for the Boston Women Entrepreneurship Incubator Tracker.

Generates:
  - 150 startups
  - 90  mentors
  - 70  investors
  - 80  events
  - funding_rounds       (time series funding history per startup)
  - mentorship_sessions  (logged mentor <-> startup sessions with ratings)
  - event_participation  (who attended which event)
  - investments          (junction: investor <-> funding_round)

No internet / external packages required - pure Python `random` module,
seeded for reproducibility.
"""
import random
import csv
import os
import datetime as dt

from _namebank import (
    FIRST_NAMES, LAST_NAMES, STARTUP_WORDS_1, STARTUP_WORDS_2, INDUSTRIES,
    STAGES, NEIGHBORHOODS, MENTOR_EXPERTISE, INVESTOR_TYPES, EVENT_TYPES, COMPANIES
)

random.seed(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT_DIR, exist_ok=True)

N_STARTUPS = 150
N_MENTORS = 90
N_INVESTORS = 70
N_EVENTS = 80

START_DATE = dt.date(2021, 1, 1)
END_DATE = dt.date(2026, 8, 1)


def random_date(start=START_DATE, end=END_DATE):
    delta = (end - start).days
    return start + dt.timedelta(days=random.randint(0, delta))


def full_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def startup_name(used):
    while True:
        name = f"{random.choice(STARTUP_WORDS_1)}{random.choice(STARTUP_WORDS_2)}"
        if name not in used:
            used.add(name)
            return name


def write_csv(filename, header, rows):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {len(rows):>5} rows -> {filename}")


def gen_startups():
    used = set()
    rows = []
    for sid in range(1, N_STARTUPS + 1):
        founded = random_date(dt.date(2018, 1, 1), dt.date(2026, 1, 1))
        stage = random.choices(STAGES, weights=[8, 20, 30, 25, 12, 5])[0]
        employees = {
            "Idea": random.randint(1, 3), "Pre-Seed": random.randint(1, 5),
            "Seed": random.randint(3, 15), "Series A": random.randint(10, 40),
            "Series B": random.randint(30, 90), "Growth": random.randint(60, 200),
        }[stage]
        rows.append([
            sid,
            startup_name(used) + " " + random.choice(["Inc.", "Co.", "PBC", "LLC"]),
            random.choice(INDUSTRIES),
            stage,
            founded.isoformat(),
            random.choice(NEIGHBORHOODS),
            full_name(),                         # founder_name
            employees,
            round(random.uniform(2.5, 4.9), 1),   # founder_diversity_score (composite, illustrative)
            random.choice([0, 1]),                # active (1) vs inactive/graduated (0)
        ])
    write_csv(
        "startups.csv",
        ["startup_id", "name", "industry", "stage", "founded_date", "neighborhood",
         "founder_name", "employee_count", "impact_score", "active"],
        rows,
    )
    return rows


def gen_mentors():
    rows = []
    for mid in range(1, N_MENTORS + 1):
        rows.append([
            mid,
            full_name(),
            random.choice(MENTOR_EXPERTISE),
            random.randint(2, 30),                # years_experience
            round(random.uniform(3.0, 5.0), 2),    # avg_rating (will be recomputed from sessions too)
            random.choice(["Volunteer", "Paid Advisor", "Board Member"]),
            random_date(dt.date(2019, 1, 1), dt.date(2026, 1, 1)).isoformat(),  # joined_date
        ])
    write_csv(
        "mentors.csv",
        ["mentor_id", "name", "expertise", "years_experience", "avg_rating",
         "mentor_type", "joined_date"],
        rows,
    )
    return rows


def gen_investors():
    rows = []
    for iid in range(1, N_INVESTORS + 1):
        rows.append([
            iid,
            f"{random.choice(COMPANIES)} #{iid}" if random.random() < 0.3 else full_name(),
            random.choice(INVESTOR_TYPES),
            random.choice(INDUSTRIES),            # focus_industry
            random.randint(1, 25),                # portfolio_size (self-reported, outside program)
            random_date(dt.date(2019, 1, 1), dt.date(2026, 1, 1)).isoformat(),
        ])
    write_csv(
        "investors.csv",
        ["investor_id", "name", "investor_type", "focus_industry", "portfolio_size", "joined_date"],
        rows,
    )
    return rows


def gen_events():
    rows = []
    for eid in range(1, N_EVENTS + 1):
        etype = random.choice(EVENT_TYPES)
        rows.append([
            eid,
            f"{etype} - {random_date().strftime('%B %Y')}",
            etype,
            random_date().isoformat(),
            random.randint(15, 200),              # capacity
            round(random.uniform(500, 15000), 2), # cost_usd (NEW: for ROI analysis)
        ])
    write_csv(
        "events.csv",
        ["event_id", "name", "event_type", "event_date", "capacity", "cost_usd"],
        rows,
    )
    return rows


def gen_funding_rounds(startups):
    """NEW table: time-series funding history, 0-4 rounds per startup."""
    rows = []
    fid = 1
    round_types_by_stage_idx = ["Pre-Seed", "Seed", "Series A", "Series B"]
    for s in startups:
        sid, _, _, stage, founded, *_ = s
        stage_idx = STAGES.index(stage)
        n_rounds = min(stage_idx, 4)
        founded_date = dt.date.fromisoformat(founded)
        last_date = founded_date
        raised_so_far = 0
        for r in range(n_rounds):
            round_type = round_types_by_stage_idx[min(r, 3)]
            gap_days = random.randint(120, 500)
            last_date = last_date + dt.timedelta(days=gap_days)
            if last_date > END_DATE:
                break
            amount = {
                "Pre-Seed": random.uniform(25_000, 250_000),
                "Seed": random.uniform(250_000, 2_000_000),
                "Series A": random.uniform(2_000_000, 12_000_000),
                "Series B": random.uniform(10_000_000, 40_000_000),
            }[round_type]
            raised_so_far += amount
            rows.append([fid, sid, round_type, round(amount, 2), last_date.isoformat()])
            fid += 1
    write_csv(
        "funding_rounds.csv",
        ["funding_round_id", "startup_id", "round_type", "amount_usd", "round_date"],
        rows,
    )
    return rows


def gen_investments(funding_rounds, investors):
    """Junction: which investor(s) participated in which funding round."""
    rows = []
    inv_id = 1
    for fr in funding_rounds:
        fr_id = fr[0]
        n_investors_in_round = random.randint(1, 4)
        chosen = random.sample(investors, min(n_investors_in_round, len(investors)))
        for inv in chosen:
            rows.append([inv_id, fr_id, inv[0], round(random.uniform(0.05, 1.0), 2)])
            inv_id += 1
    write_csv(
        "investments.csv",
        ["investment_id", "funding_round_id", "investor_id", "participation_share"],
        rows,
    )
    return rows


def gen_mentorship_sessions(startups, mentors):
    """NEW table: logged sessions with feedback ratings, replaces a flat junction table."""
    rows = []
    sess_id = 1
    for s in startups:
        sid = s[0]
        n_sessions = random.randint(0, 8)
        chosen_mentors = random.sample(mentors, min(n_sessions, len(mentors)))
        for m in chosen_mentors:
            rows.append([
                sess_id, sid, m[0],
                random_date().isoformat(),
                random.randint(30, 120),                 # duration_minutes
                round(random.uniform(2.5, 5.0), 1),       # session_rating
                random.choice(["Fundraising", "Product", "Marketing", "Operations", "Legal", "Hiring"]),
            ])
            sess_id += 1
    write_csv(
        "mentorship_sessions.csv",
        ["session_id", "startup_id", "mentor_id", "session_date", "duration_minutes",
         "session_rating", "topic"],
        rows,
    )
    return rows


def gen_event_participation(events, startups, mentors, investors):
    """NEW table: attendance across all three stakeholder types, for ROI + engagement analysis."""
    rows = []
    pid = 1
    for e in events:
        eid, name, etype, edate, capacity, cost = e
        n_attendees = random.randint(int(capacity * 0.2), capacity)
        pool = (
            [("startup", s[0]) for s in startups] +
            [("mentor", m[0]) for m in mentors] +
            [("investor", i[0]) for i in investors]
        )
        attendees = random.sample(pool, min(n_attendees, len(pool)))
        for attendee_type, attendee_id in attendees:
            rows.append([pid, eid, attendee_type, attendee_id])
            pid += 1
    write_csv(
        "event_participation.csv",
        ["participation_id", "event_id", "attendee_type", "attendee_id"],
        rows,
    )
    return rows


def main():
    print("Generating seed data ...")
    startups = gen_startups()
    mentors = gen_mentors()
    investors = gen_investors()
    events = gen_events()
    funding_rounds = gen_funding_rounds(startups)
    gen_investments(funding_rounds, investors)
    gen_mentorship_sessions(startups, mentors)
    gen_event_participation(events, startups, mentors, investors)
    print("Done. CSVs written to:", os.path.abspath(OUT_DIR))


if __name__ == "__main__":
    main()
