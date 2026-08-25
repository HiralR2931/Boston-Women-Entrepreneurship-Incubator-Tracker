import streamlit as st
from _shared import inject_base_css, PAGE_ICON, BRAND_COLOR
from analytics import queries as q
import plotly.express as px

st.set_page_config(page_title="Investors", page_icon=PAGE_ICON, layout="wide")
inject_base_css(st)
st.title("💰 Investors")

engagement = q.investor_engagement()
diversity = q.investor_portfolio_diversity()

tab1, tab2 = st.tabs(["Engagement & Capital Deployed", "Portfolio Diversity"])

with tab1:
    st.caption("Ranked by estimated capital deployed into the incubator's startups.")
    st.dataframe(
        engagement.rename(columns={
            "name": "Investor", "investor_type": "Type",
            "rounds_participated": "Rounds Participated",
            "distinct_startups_backed": "Startups Backed",
            "est_capital_deployed": "Est. Capital Deployed ($)",
        }).drop(columns=["investor_id"]),
        width="stretch", height=450,
    )
    fig = px.bar(engagement.head(15), x="est_capital_deployed", y="name", orientation="h",
                 color="investor_type", labels={"est_capital_deployed": "Capital Deployed ($)", "name": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with tab2:
    st.caption(
        "Diversification Index blends how many distinct industries and stages "
        "each investor has backed -- higher means a more spread-out portfolio."
    )
    st.dataframe(
        diversity.rename(columns={
            "name": "Investor", "investor_type": "Type",
            "distinct_industries": "Industries Backed", "distinct_stages": "Stages Backed",
            "total_deployed": "Total Deployed ($)", "total_investments": "# Investments",
            "diversification_index": "Diversification Index",
        }).drop(columns=["investor_id"]),
        width="stretch", height=450,
    )
    fig2 = px.scatter(diversity, x="distinct_industries", y="total_deployed",
                       size="total_investments", color="investor_type", hover_name="name",
                       labels={"distinct_industries": "Distinct Industries Backed", "total_deployed": "Total Deployed ($)"})
    st.plotly_chart(fig2, width="stretch")
