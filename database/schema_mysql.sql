-- =====================================================================
-- Boston Women Entrepreneurship Incubator Tracker -- Relational Schema
-- Core tables:
--   startups, mentors, investors, events   (the four stakeholder entities)
--   funding_rounds        (time-series funding history, not just totals)
--   investments           (investor <-> funding_round, many-to-many, with share %)
--   mentorship_sessions   (logged sessions with ratings & topics)
--   event_participation   (single polymorphic table across startups/mentors/investors)
-- Plus indexes and foreign keys for referential integrity and query performance.
-- Target: MySQL 8+. (Demo build in this repo runs on SQLite for zero-setup;
-- see database/init_db.py -- schema is written to be MySQL-compatible so
-- swapping DATABASE_URL to a MySQL DSN is a drop-in change.)
-- =====================================================================

CREATE TABLE startups (
    startup_id      INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(150) NOT NULL,
    industry        VARCHAR(60)  NOT NULL,
    stage           VARCHAR(20)  NOT NULL,
    founded_date    DATE         NOT NULL,
    neighborhood    VARCHAR(60),
    founder_name    VARCHAR(100),
    employee_count  INT DEFAULT 0,
    impact_score    DECIMAL(3,1),
    active          TINYINT(1) DEFAULT 1
);

CREATE TABLE mentors (
    mentor_id       INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    expertise       VARCHAR(60),
    years_experience INT,
    avg_rating      DECIMAL(3,2),
    mentor_type     VARCHAR(30),
    joined_date     DATE
);

CREATE TABLE investors (
    investor_id     INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(150) NOT NULL,
    investor_type   VARCHAR(30),
    focus_industry  VARCHAR(60),
    portfolio_size  INT,
    joined_date     DATE
);

CREATE TABLE events (
    event_id        INT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(150) NOT NULL,
    event_type      VARCHAR(40),
    event_date      DATE,
    capacity        INT,
    cost_usd        DECIMAL(10,2)
);

-- NEW: replaces a single "funding" total column with proper time-series history
CREATE TABLE funding_rounds (
    funding_round_id INT PRIMARY KEY AUTO_INCREMENT,
    startup_id       INT NOT NULL,
    round_type       VARCHAR(20),
    amount_usd       DECIMAL(14,2),
    round_date       DATE,
    FOREIGN KEY (startup_id) REFERENCES startups(startup_id) ON DELETE CASCADE
);

-- NEW: many-to-many between investors and funding rounds, with participation share
CREATE TABLE investments (
    investment_id     INT PRIMARY KEY AUTO_INCREMENT,
    funding_round_id  INT NOT NULL,
    investor_id       INT NOT NULL,
    participation_share DECIMAL(4,2),
    FOREIGN KEY (funding_round_id) REFERENCES funding_rounds(funding_round_id) ON DELETE CASCADE,
    FOREIGN KEY (investor_id) REFERENCES investors(investor_id) ON DELETE CASCADE
);

-- mentor<->startup junction, carrying session-level detail & ratings
CREATE TABLE mentorship_sessions (
    session_id      INT PRIMARY KEY AUTO_INCREMENT,
    startup_id      INT NOT NULL,
    mentor_id       INT NOT NULL,
    session_date    DATE,
    duration_minutes INT,
    session_rating  DECIMAL(2,1),
    topic           VARCHAR(40),
    FOREIGN KEY (startup_id) REFERENCES startups(startup_id) ON DELETE CASCADE,
    FOREIGN KEY (mentor_id)  REFERENCES mentors(mentor_id)   ON DELETE CASCADE
);

-- NEW: single polymorphic attendance table (startup / mentor / investor) per event
CREATE TABLE event_participation (
    participation_id INT PRIMARY KEY AUTO_INCREMENT,
    event_id         INT NOT NULL,
    attendee_type    VARCHAR(10) NOT NULL,  -- 'startup' | 'mentor' | 'investor'
    attendee_id      INT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

-- Indexes for the query patterns used by the analytics layer
CREATE INDEX idx_funding_startup     ON funding_rounds(startup_id);
CREATE INDEX idx_invest_round        ON investments(funding_round_id);
CREATE INDEX idx_invest_investor     ON investments(investor_id);
CREATE INDEX idx_session_startup     ON mentorship_sessions(startup_id);
CREATE INDEX idx_session_mentor      ON mentorship_sessions(mentor_id);
CREATE INDEX idx_participation_event ON event_participation(event_id);
CREATE INDEX idx_startups_industry   ON startups(industry);
CREATE INDEX idx_startups_stage      ON startups(stage);
