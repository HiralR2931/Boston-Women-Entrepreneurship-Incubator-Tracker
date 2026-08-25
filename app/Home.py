import streamlit as st
from _shared import inject_base_css, kpi_card, PAGE_ICON, BRAND_COLOR
from analytics import queries as q
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Incubator Tracker", page_icon=PAGE_ICON, layout="wide")
inject_base_css(st)

st.title(f"{PAGE_ICON} Boston Women Entrepreneurship Incubator Tracker")
st.caption("Program dashboard — analytics, mentor matching, and exportable reports")

kpis = q.kpi_summary()

cols = st.columns(5)
kpi_card(st, cols[0], kpis["active_startups"], "Active Startups")
kpi_card(st, cols[1], f"${kpis['total_funding_raised']/1e6:,.1f}M", "Total Capital Raised")
kpi_card(st, cols[2], kpis["total_mentors"], "Mentors in Network")
kpi_card(st, cols[3], kpis["total_mentorship_sessions"], "Mentorship Sessions")
kpi_card(st, cols[4], kpis["total_investors"], "Investors Engaged")

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Quarterly Funding Trend")
    trend = q.funding_trend_over_time()
    fig = px.bar(trend, x="period", y="total_amount",
                 labels={"period": "Quarter", "total_amount": "Total Raised ($)"},
                 color_discrete_sequence=[BRAND_COLOR])
    fig.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Startups by Stage")
    startups = q.load_startups()
    stage_counts = startups["stage"].value_counts().reset_index()
    stage_counts.columns = ["stage", "count"]
    fig2 = px.pie(stage_counts, names="stage", values="count", hole=0.4,
                  color_discrete_sequence=px.colors.sequential.Purples_r)
    fig2.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig2, width="stretch")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Top 10 Funded Startups")
    st.dataframe(
        q.top_funded_startups(10).rename(columns={
            "name": "Startup", "industry": "Industry", "stage": "Stage",
            "total_raised": "Total Raised ($)", "rounds": "Rounds"
        }).set_index("startup_id"),
        width="stretch",
    )
with col2:
    st.subheader("Funding by Industry")
    ind = q.high_growth_industries()
    fig3 = px.bar(ind, x="total_funding", y="industry", orientation="h",
                  color_discrete_sequence=["#F2A541"])
    fig3.update_layout(margin=dict(t=10, b=10), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, width="stretch")

st.info(
    "Use the pages in the sidebar to explore Startups, Mentors, Investors, Events, "
    "Funding Analytics, Mentor Matching, and to generate exportable Reports.",
    icon="👈",
)
