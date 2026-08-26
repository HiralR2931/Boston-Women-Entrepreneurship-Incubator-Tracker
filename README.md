# Boston Women Entrepreneurship Incubator Tracker

**▶ Live demo: [boston-women-entrepreneurship-incubator-tracker.streamlit.app](https://boston-women-entrepreneurship-incubator-tracker.streamlit.app)**

A live **Streamlit dashboard** for tracking startups, mentors, investors, and
events across a women-focused startup incubator — backed by a pluggable data
layer, with analytics for program staff and **on-demand exportable reports**
(PDF + Excel).

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-app-FF4B4B)
![Tests](https://img.shields.io/badge/tests-32%20passing-brightgreen)

## Features

- **Multi-page web dashboard** — eight pages covering startups, mentors,
  investors, events, funding analytics, and mentor matching.
- **Time-series funding analysis** — quarterly funding trend, breakdowns by
  round type and industry, not just static totals.
- **Composite startup health score** — a 0–100 signal blending capital raised,
  mentorship engagement, session ratings, and impact score, to help staff
  triage where attention is needed.
- **Mentor–startup matching recommender** — ranks mentors for a chosen startup
  by expertise fit, historical ratings, and current workload, with a
  plain-English reason attached to every recommendation.
- **Mentor load balancing** — flags overloaded and underutilized mentors.
- **Investor portfolio diversification index** — how widely each investor has
  spread their bets across industries and stages.
- **Event ROI** — cost per attendee alongside follow-on funding raised by
  attending startups within 60 days.
- **One-click reports** — a board-ready PDF and an Excel workbook with native
  charts, both generated fresh from live data.
- **Pluggable storage** — SQLite + JSON files out of the box with zero setup,
  or real MySQL + MongoDB by setting one environment variable each.

## Architecture

```
database/     SQL schema (MySQL-flavored) + seed data generator + SQLite builder
nosql/        Mongo-compatible document store (JSON files locally, real MongoDB in prod)
analytics/    All pandas-based analytics functions (the "smart" layer)
reports/      PDF (reportlab) + Excel (openpyxl) report generators
app/          Streamlit multi-page dashboard
data/         Generated CSVs + the SQLite database file
```

Generated artifacts — `data/`, `nosql/collections/`, `sample_reports/`, and
`generated_reports/` — are produced by the setup scripts and are not tracked in
version control. Everything in the repository is source.

Every layer above talks to the one below it through a narrow interface
(`analytics/queries.py` is the only thing the app imports for data access),
so any layer can be swapped without touching the others. In particular:

- **SQL engine:** defaults to a bundled SQLite file at `data/incubator.db`.
  To point at real MySQL instead, set `DATABASE_URL=mysql+pymysql://user:pass@host/db`
  and run `database/schema_mysql.sql` against it — no code changes required elsewhere.
- **NoSQL engine:** defaults to JSON files under `nosql/collections/`.
  To point at real MongoDB instead, set `MONGO_URI=mongodb://...` (and optionally
  `MONGO_DB=your_db_name`) — again, no code changes elsewhere.

## Data model

**Relational (SQL):**
`startups`, `mentors`, `investors`, `events`, `funding_rounds`,
`investments` (investor ↔ funding round), `mentorship_sessions` (mentor ↔ startup,
with ratings), `event_participation` (polymorphic attendance across all three
stakeholder types). See `database/schema_mysql.sql` for full DDL with foreign keys
and indexes.

**Semi-structured (NoSQL):**
`startup_profiles` (tags, pitch deck links, social handles),
`mentor_feedback` (free-text session feedback), `press_mentions`,
`social_engagement` (follower/traffic snapshots), `investor_notes`
(due-diligence notes). See `nosql/seed_nosql.py`.

## Getting started

```bash
git clone https://github.com/HiralR2931/Boston-Women-Entrepreneurship-Incubator-Tracker.git
cd Boston-Women-Entrepreneurship-Incubator-Tracker
bash setup.sh
```

That installs dependencies, generates the seed dataset, builds the SQLite
database and NoSQL JSON collections, and launches the app at
`http://localhost:8501`.

`setup.sh` creates a virtualenv in `.venv/` and installs into that. A venv is
required rather than optional on Homebrew and other PEP 668 "externally managed"
Pythons, where a bare `pip install` refuses to run.

Manual steps (if you prefer not to use `setup.sh`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python database/seed_data.py       # generate synthetic CSV data
python database/init_db.py         # build SQLite DB from those CSVs
python nosql/seed_nosql.py         # seed the NoSQL/JSON collections
streamlit run app/Home.py          # launch the dashboard
```

The seed scripts are idempotent — re-running any of them rebuilds that dataset
from scratch instead of appending a second copy.

To generate the reports from the command line without the UI:

```bash
python reports/report_generator.py
# writes sample_reports/incubator_board_report.pdf
#        sample_reports/incubator_analytics_workbook.xlsx
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite covers the analytics layer — health scores stay in range, funding
trend totals reconcile against the underlying rounds, derived indices match
their documented formulas, recommenders stay ordered and bounded — plus the two
properties of the seed pipeline that are easy to break silently: the dataset is
reproducible (`random.seed(42)`) and re-seeding is idempotent rather than
additive.

## App pages

- **Home** — KPI cards, quarterly funding trend, stage mix, top performers
- **Startups** — filterable directory, health-score leaderboard, per-startup 360 view (SQL + NoSQL merged)
- **Mentors** — directory, top-rated mentors, load-balance flags (overloaded / underutilized)
- **Investors** — capital deployed, portfolio diversification index
- **Events** — cost-per-attendee and 60-day follow-on funding ROI proxy
- **Funding Analytics** — trend, by round type, by industry, health-score leaderboard
- **Mentor Matching** — pick a startup, get ranked mentor recommendations with reasons
- **Reports** — one-click PDF / Excel export of everything above

## Notes on the synthetic data

All names, companies, and figures are synthetically generated (`database/seed_data.py`,
seeded with `random.seed(42)` for reproducibility) — there is no real personal or
financial data anywhere in this repo. Swap in your own real data by replacing the
CSVs in `data/` (matching the column headers) and re-running `init_db.py`, or by
pointing `DATABASE_URL` / `MONGO_URI` at your real databases.

## Honest caveats (documented in-app too)

- **Health Score** is a heuristic 0–100 composite (funding + mentorship engagement +
  session ratings + impact score), meant to help program staff triage attention —
  not a valuation model.
- **Event ROI** shows a correlation (attendance → funding raised in the following
  60 days), not a proven causal effect of the event itself.
- **Mentor Matching** is a transparent rule-based recommender (expertise fit +
  historical rating + current workload), not a machine-learned model — every
  recommendation comes with a plain-English reason.
