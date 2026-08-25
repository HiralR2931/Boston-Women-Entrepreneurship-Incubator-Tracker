import streamlit as st
from _shared import inject_base_css, PAGE_ICON, BRAND_COLOR
from analytics import queries as q
import plotly.express as px

st.set_page_config(page_title="Funding Analytics", page_icon=PAGE_ICON, layout="wide")
inject_base_css(st)
st.title("📈 Funding Analytics")

trend = q.funding_trend_over_time()
by_stage = q.funding_distribution_by_stage()
by_industry = q.high_growth_industries()

st.subheader("Funding Raised Over Time")
fig = px.area(trend, x="period", y="total_amount", color_discrete_sequence=[BRAND_COLOR],
              labels={"period": "Quarter", "total_amount": "Total Raised ($)"})
st.plotly_chart(fig, width="stretch")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Funding by Round Type")
    fig2 = px.bar(by_stage, x="round_type", y="total_amount", color="round_type",
                  labels={"round_type": "Round Type", "total_amount": "Total Amount ($)"})
    st.plotly_chart(fig2, width="stretch")
    st.dataframe(by_stage.rename(columns={
        "round_type": "Round Type", "num_rounds": "# Rounds",
        "total_amount": "Total ($)", "avg_amount": "Avg Round Size ($)"
    }), width="stretch")

with col2:
    st.subheader("Funding by Industry")
    fig3 = px.treemap(by_industry, path=["industry"], values="total_funding",
                       color="total_funding", color_continuous_scale="Purples")
    st.plotly_chart(fig3, width="stretch")
    st.dataframe(by_industry.rename(columns={
        "industry": "Industry", "startup_count": "# Startups",
        "total_funding": "Total Funding ($)", "avg_employees": "Avg Employees"
    }), width="stretch")

st.divider()
st.subheader("Startup Health Score Leaderboard")
st.caption(
    "Composite score (0-100) blending capital raised, mentorship engagement, "
    "session ratings, and impact score. Meant to help staff triage attention -- "
    "not a valuation or investment recommendation."
)
health = q.startup_health_score()
industry_filter = st.multiselect("Filter by industry", sorted(health["industry"].unique()))
filtered_health = health[health["industry"].isin(industry_filter)] if industry_filter else health
st.dataframe(
    filtered_health.rename(columns={
        "name": "Startup", "industry": "Industry", "stage": "Stage",
        "total_raised": "Total Raised ($)", "session_count": "Mentorship Sessions",
        "avg_rating": "Avg Session Rating", "health_score": "Health Score",
    }).drop(columns=["startup_id"]),
    width="stretch", height=450,
)
