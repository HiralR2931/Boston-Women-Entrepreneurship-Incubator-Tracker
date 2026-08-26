"""
Tests for the analytics layer.

These run against whatever dataset is currently built, so they assert on
invariants and internal consistency (scores stay in range, totals agree with
their source tables, rankings are actually ordered) rather than on hard-coded
figures that would break the moment the seed parameters change.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import queries as q
from database.bootstrap import ensure_data

ensure_data(log=lambda *a, **k: None)


LOADERS = [
    q.load_startups, q.load_mentors, q.load_investors, q.load_events,
    q.load_funding_rounds, q.load_investments, q.load_mentorship_sessions,
    q.load_event_participation,
]

ANALYTICS = [
    q.top_funded_startups, q.top_mentors_by_rating, q.high_growth_industries,
    q.investor_engagement, q.funding_distribution_by_stage,
    q.funding_trend_over_time, q.startup_health_score, q.mentor_load_balance,
    q.investor_portfolio_diversity, q.event_roi,
]


@pytest.mark.parametrize("fn", LOADERS, ids=lambda f: f.__name__)
def test_loaders_return_populated_frames(fn):
    df = fn()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty, f"{fn.__name__} returned no rows"


@pytest.mark.parametrize("fn", ANALYTICS, ids=lambda f: getattr(f, "__name__", str(f)))
def test_analytics_return_populated_frames(fn):
    df = fn()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty, f"{fn.__name__} returned no rows"


def test_kpi_summary_is_internally_consistent():
    kpi = q.kpi_summary()
    assert kpi["total_startups"] == len(q.load_startups())
    assert kpi["total_funding_rounds"] == len(q.load_funding_rounds())
    assert kpi["total_mentors"] == len(q.load_mentors())
    assert 0 <= kpi["active_startups"] <= kpi["total_startups"]
    assert kpi["total_funding_raised"] > 0
    assert 0 <= kpi["avg_session_rating"] <= 5


def test_health_score_stays_in_range_and_covers_every_startup():
    hs = q.startup_health_score()
    assert len(hs) == len(q.load_startups())
    assert hs["health_score"].between(0, 100).all()
    assert hs["startup_id"].is_unique
    # Documented as a descending leaderboard.
    assert hs["health_score"].is_monotonic_decreasing


def test_funding_trend_totals_match_the_underlying_rounds():
    trend = q.funding_trend_over_time()
    expected = q.load_funding_rounds()["amount_usd"].sum()
    assert trend["total_amount"].sum() == pytest.approx(expected)
    assert trend["num_rounds"].sum() == len(q.load_funding_rounds())


def test_mentor_matching_respects_top_n_and_explains_itself():
    startup_id = int(q.load_startups().iloc[0]["startup_id"])
    recs = q.mentor_matching_recommendations(startup_id, top_n=3)
    assert len(recs) == 3
    assert recs["match_score"].is_monotonic_decreasing
    # Every recommendation carries a plain-English reason, as the UI promises.
    assert recs["match_reason"].str.len().gt(0).all()
    assert recs["mentor_id"].is_unique


def test_mentor_matching_handles_an_unknown_startup():
    recs = q.mentor_matching_recommendations(-1)
    assert isinstance(recs, pd.DataFrame)
    assert recs.empty


def test_mentor_load_balance_labels_are_valid():
    lb = q.mentor_load_balance()
    assert len(lb) == len(q.load_mentors())
    assert set(lb["status"]).issubset({"Overloaded", "Underutilized", "Balanced"})
    assert (lb["session_count"] >= 0).all()


def test_event_roi_cost_per_attendee_is_arithmetically_right():
    roi = q.event_roi()
    with_attendees = roi[roi["attendees"] > 0]
    expected = with_attendees["cost_usd"] / with_attendees["attendees"]
    assert with_attendees["cost_per_attendee"].values == pytest.approx(expected.values, abs=0.01)
    # Events nobody attended must not divide by zero.
    assert roi[roi["attendees"] == 0]["cost_per_attendee"].isna().all()


def test_investor_diversity_index_matches_its_formula():
    div = q.investor_portfolio_diversity()
    expected = div["distinct_industries"] * 0.6 + div["distinct_stages"] * 0.4
    assert div["diversification_index"].values == pytest.approx(expected.values, abs=0.01)
    assert (div["distinct_industries"] >= 1).all()


def test_startup_360_merges_sql_and_nosql():
    startup_id = int(q.load_startups().iloc[0]["startup_id"])
    view = q.startup_profile_with_pressure(startup_id)
    assert set(view) == {"profile", "press_mentions", "social_engagement"}
    assert view["profile"]["startup_id"] == startup_id
    assert isinstance(view["press_mentions"], list)
