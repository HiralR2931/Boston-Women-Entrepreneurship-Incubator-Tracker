"""
Analytics layer. Every function returns a pandas DataFrame (or a small dict
of scalars) so it can be reused identically by:
  - the Streamlit dashboard pages
  - the PDF/Excel report generator
  - ad-hoc analysis in a notebook

Beyond the straightforward leaderboards (top startups, top mentors,
high-growth industries, investor engagement, event participation, funding
distribution), this module also provides:
  - funding_trend_over_time()      time-series, not just a static total
  - startup_health_score()         composite KPI: funding + mentorship + rating
  - mentor_matching_recommendations()  rule-based startup<->mentor matching
  - investor_portfolio_diversity()  how spread out each investor's bets are
  - event_roi()                     cost per attendee vs. downstream funding
  - mentor_load_balance()           flags over/under-utilized mentors
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_config import get_connection
from nosql.nosql_store import get_store


def _read(query, params=None):
    conn = get_connection()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Core table loaders
# ---------------------------------------------------------------------

def load_startups():
    return _read("SELECT * FROM startups")


def load_mentors():
    return _read("SELECT * FROM mentors")


def load_investors():
    return _read("SELECT * FROM investors")


def load_events():
    return _read("SELECT * FROM events")


def load_funding_rounds():
    return _read("SELECT * FROM funding_rounds")


def load_investments():
    return _read("SELECT * FROM investments")


def load_mentorship_sessions():
    return _read("SELECT * FROM mentorship_sessions")


def load_event_participation():
    return _read("SELECT * FROM event_participation")


# ---------------------------------------------------------------------
# KPI summary (dashboard header cards)
# ---------------------------------------------------------------------

def kpi_summary():
    startups = load_startups()
    funding = load_funding_rounds()
    sessions = load_mentorship_sessions()
    investors = load_investors()
    return {
        "total_startups": len(startups),
        "active_startups": int(startups["active"].sum()),
        "total_funding_raised": float(funding["amount_usd"].sum()),
        "total_funding_rounds": len(funding),
        "total_mentors": len(load_mentors()),
        "total_mentorship_sessions": len(sessions),
        "avg_session_rating": round(float(sessions["session_rating"].mean()), 2) if len(sessions) else 0,
        "total_investors": len(investors),
        "total_events": len(load_events()),
    }


# ---------------------------------------------------------------------
# Top performers
# ---------------------------------------------------------------------

def top_funded_startups(n=10):
    q = """
    SELECT s.startup_id, s.name, s.industry, s.stage,
           SUM(f.amount_usd) AS total_raised,
           COUNT(f.funding_round_id) AS rounds
    FROM startups s
    JOIN funding_rounds f ON f.startup_id = s.startup_id
    GROUP BY s.startup_id, s.name, s.industry, s.stage
    ORDER BY total_raised DESC
    LIMIT ?
    """
    return _read(q, (n,))


def top_mentors_by_rating(n=10, min_sessions=2):
    q = """
    SELECT m.mentor_id, m.name, m.expertise,
           COUNT(ms.session_id) AS sessions_logged,
           ROUND(AVG(ms.session_rating), 2) AS avg_logged_rating
    FROM mentors m
    JOIN mentorship_sessions ms ON ms.mentor_id = m.mentor_id
    GROUP BY m.mentor_id, m.name, m.expertise
    HAVING sessions_logged >= ?
    ORDER BY avg_logged_rating DESC, sessions_logged DESC
    LIMIT ?
    """
    return _read(q, (min_sessions, n))


def high_growth_industries():
    q = """
    SELECT s.industry,
           COUNT(DISTINCT s.startup_id) AS startup_count,
           SUM(f.amount_usd) AS total_funding,
           ROUND(AVG(s.employee_count), 1) AS avg_employees
    FROM startups s
    LEFT JOIN funding_rounds f ON f.startup_id = s.startup_id
    GROUP BY s.industry
    ORDER BY total_funding DESC
    """
    return _read(q)


def investor_engagement():
    q = """
    SELECT i.investor_id, i.name, i.investor_type,
           COUNT(DISTINCT inv.funding_round_id) AS rounds_participated,
           COUNT(DISTINCT fr.startup_id) AS distinct_startups_backed,
           ROUND(SUM(fr.amount_usd * inv.participation_share), 2) AS est_capital_deployed
    FROM investors i
    JOIN investments inv ON inv.investor_id = i.investor_id
    JOIN funding_rounds fr ON fr.funding_round_id = inv.funding_round_id
    GROUP BY i.investor_id, i.name, i.investor_type
    ORDER BY est_capital_deployed DESC
    """
    return _read(q)


def funding_distribution_by_stage():
    q = """
    SELECT round_type, COUNT(*) AS num_rounds,
           SUM(amount_usd) AS total_amount,
           ROUND(AVG(amount_usd), 2) AS avg_amount
    FROM funding_rounds
    GROUP BY round_type
    ORDER BY total_amount DESC
    """
    return _read(q)


# ---------------------------------------------------------------------
# NEW: time-series funding trend
# ---------------------------------------------------------------------

def funding_trend_over_time(resample_freq="QE", period_freq="Q"):
    """Total capital raised per period (default quarterly) across all startups."""
    fr = load_funding_rounds()
    if fr.empty:
        return pd.DataFrame(columns=["period", "total_amount", "num_rounds"])
    fr["round_date"] = pd.to_datetime(fr["round_date"])
    grouped = (
        fr.set_index("round_date")
        .resample(resample_freq)
        .agg(total_amount=("amount_usd", "sum"), num_rounds=("funding_round_id", "count"))
        .reset_index()
    )
    grouped["period"] = grouped["round_date"].dt.to_period(period_freq).astype(str)
    return grouped[["period", "total_amount", "num_rounds"]]


# ---------------------------------------------------------------------
# NEW: composite startup health score
# ---------------------------------------------------------------------

def startup_health_score():
    """
    Composite 0-100 score blending:
      - funding raised (normalized)
      - number of mentorship sessions (engagement)
      - average mentorship session rating (quality)
      - employee growth relative to stage baseline
    This is a heuristic score meant to help incubator staff triage attention,
    not a scientific valuation model -- documented as such in the app.
    """
    startups = load_startups()
    funding = load_funding_rounds().groupby("startup_id")["amount_usd"].sum().rename("total_raised")
    sessions = load_mentorship_sessions()
    sess_agg = sessions.groupby("startup_id").agg(
        session_count=("session_id", "count"),
        avg_rating=("session_rating", "mean"),
    )

    df = startups.set_index("startup_id").join(funding).join(sess_agg)
    df["total_raised"] = df["total_raised"].fillna(0)
    df["session_count"] = df["session_count"].fillna(0)
    df["avg_rating"] = df["avg_rating"].fillna(0)

    def norm(s):
        rng = (s.max() - s.min())
        return (s - s.min()) / rng if rng > 0 else s * 0

    df["funding_score"] = norm(df["total_raised"]) * 40
    df["engagement_score"] = norm(df["session_count"]) * 30
    df["quality_score"] = (df["avg_rating"] / 5.0).fillna(0) * 20
    df["impact_component"] = norm(df["impact_score"].fillna(0)) * 10

    df["health_score"] = (
        df["funding_score"] + df["engagement_score"] + df["quality_score"] + df["impact_component"]
    ).round(1)

    result = df.reset_index()[[
        "startup_id", "name", "industry", "stage", "total_raised",
        "session_count", "avg_rating", "health_score"
    ]].sort_values("health_score", ascending=False)
    return result


# ---------------------------------------------------------------------
# NEW: mentor <-> startup matching recommendations
# ---------------------------------------------------------------------

# Which mentor expertise areas best serve which startup stage
STAGE_TO_PRIORITY_EXPERTISE = {
    "Idea": ["Product Strategy", "UX Design", "Legal"],
    "Pre-Seed": ["Product Strategy", "Fundraising", "Financial Modeling"],
    "Seed": ["Fundraising", "Sales", "Growth Hacking", "Marketing"],
    "Series A": ["Sales", "Operations", "HR & Talent", "Growth Hacking"],
    "Series B": ["Operations", "M&A", "Supply Chain", "Public Relations"],
    "Growth": ["M&A", "Operations", "Public Relations", "Supply Chain"],
}


def mentor_matching_recommendations(startup_id, top_n=5):
    """
    Rule-based recommender: for a given startup, rank mentors by
      + expertise match with that startup's stage-appropriate needs
      + not already over-booked (fewer than 12 sessions logged)
      + higher historical average session rating
    Returns a DataFrame of the top N recommended mentors with a match_reason.
    """
    startups = load_startups()
    mentors = load_mentors()
    sessions = load_mentorship_sessions()

    row = startups[startups["startup_id"] == startup_id]
    if row.empty:
        return pd.DataFrame()
    stage = row.iloc[0]["stage"]
    priority = STAGE_TO_PRIORITY_EXPERTISE.get(stage, [])

    load_per_mentor = sessions.groupby("mentor_id")["session_id"].count().rename("current_load")
    rating_per_mentor = sessions.groupby("mentor_id")["session_rating"].mean().rename("historical_avg_rating")

    m = mentors.set_index("mentor_id").join(load_per_mentor).join(rating_per_mentor).reset_index()
    m["current_load"] = m["current_load"].fillna(0)
    m["historical_avg_rating"] = m["historical_avg_rating"].fillna(m["avg_rating"])

    m["expertise_match"] = m["expertise"].isin(priority)
    m["match_score"] = (
        m["expertise_match"].astype(int) * 50
        + (m["historical_avg_rating"].fillna(0) / 5.0) * 30
        + (1 - (m["current_load"].clip(upper=20) / 20)) * 20
    )
    m["match_reason"] = m.apply(
        lambda r: (
            f"{'Expertise fits ' + stage + ' stage needs; ' if r['expertise_match'] else ''}"
            f"rated {r['historical_avg_rating']:.1f}/5 avg; "
            f"currently {int(r['current_load'])} active sessions"
        ),
        axis=1,
    )
    return m.sort_values("match_score", ascending=False).head(top_n)[[
        "mentor_id", "name", "expertise", "historical_avg_rating", "current_load",
        "match_score", "match_reason"
    ]]


# ---------------------------------------------------------------------
# NEW: mentor load balance (over/under-utilized)
# ---------------------------------------------------------------------

def mentor_load_balance():
    mentors = load_mentors()
    sessions = load_mentorship_sessions()
    load = sessions.groupby("mentor_id")["session_id"].count().rename("session_count")
    df = mentors.set_index("mentor_id").join(load).reset_index()
    df["session_count"] = df["session_count"].fillna(0)
    median_load = df["session_count"].median()
    df["status"] = df["session_count"].apply(
        lambda x: "Overloaded" if x > median_load * 2 else ("Underutilized" if x < median_load * 0.3 else "Balanced")
    )
    return df[["mentor_id", "name", "expertise", "session_count", "status"]].sort_values(
        "session_count", ascending=False
    )


# ---------------------------------------------------------------------
# NEW: investor portfolio diversity
# ---------------------------------------------------------------------

def investor_portfolio_diversity():
    """
    For each investor: how many distinct industries/stages they've backed,
    a simple diversification signal for program staff courting new capital.
    """
    q = """
    SELECT i.investor_id, i.name, i.investor_type,
           s.industry, s.stage, fr.amount_usd
    FROM investors i
    JOIN investments inv ON inv.investor_id = i.investor_id
    JOIN funding_rounds fr ON fr.funding_round_id = inv.funding_round_id
    JOIN startups s ON s.startup_id = fr.startup_id
    """
    df = _read(q)
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby(["investor_id", "name", "investor_type"]).agg(
        distinct_industries=("industry", "nunique"),
        distinct_stages=("stage", "nunique"),
        total_deployed=("amount_usd", "sum"),
        total_investments=("amount_usd", "count"),
    ).reset_index()
    grouped["diversification_index"] = (
        grouped["distinct_industries"] * 0.6 + grouped["distinct_stages"] * 0.4
    ).round(2)
    return grouped.sort_values("diversification_index", ascending=False)


# ---------------------------------------------------------------------
# NEW: event ROI
# ---------------------------------------------------------------------

def event_roi():
    """
    Cost per attendee, and funding raised by startups within 60 days
    after attending each event -- a simple, transparent proxy for event ROI.
    (Correlation, not proven causation -- surfaced as a signal for program
    staff, not a hard metric, and documented that way in the UI.)
    """
    events = load_events()
    participation = load_event_participation()
    funding = load_funding_rounds()
    funding["round_date"] = pd.to_datetime(funding["round_date"])
    events["event_date"] = pd.to_datetime(events["event_date"])

    rows = []
    for _, ev in events.iterrows():
        attendees = participation[participation["event_id"] == ev["event_id"]]
        n_attendees = len(attendees)
        startup_attendees = attendees[attendees["attendee_type"] == "startup"]["attendee_id"].unique()
        window_end = ev["event_date"] + pd.Timedelta(days=60)
        follow_on = funding[
            (funding["startup_id"].isin(startup_attendees))
            & (funding["round_date"] >= ev["event_date"])
            & (funding["round_date"] <= window_end)
        ]
        rows.append({
            "event_id": ev["event_id"],
            "name": ev["name"],
            "event_type": ev["event_type"],
            "cost_usd": ev["cost_usd"],
            "attendees": n_attendees,
            "cost_per_attendee": round(ev["cost_usd"] / n_attendees, 2) if n_attendees else None,
            "startups_that_raised_within_60d": len(follow_on["startup_id"].unique()),
            "follow_on_funding_60d": round(follow_on["amount_usd"].sum(), 2),
        })
    return pd.DataFrame(rows).sort_values("follow_on_funding_60d", ascending=False)


# ---------------------------------------------------------------------
# NoSQL-backed lookups
# ---------------------------------------------------------------------

def startup_profile_with_pressure(startup_id):
    """Combines relational + NoSQL data for a single startup's full 360 view."""
    store = get_store()
    profile = store["startup_profiles"].find_one({"startup_id": startup_id})
    press = store["press_mentions"].find({"startup_id": startup_id})
    engagement = store["social_engagement"].find_one({"startup_id": startup_id})
    return {"profile": profile, "press_mentions": press, "social_engagement": engagement}
