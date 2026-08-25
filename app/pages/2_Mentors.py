import streamlit as st
from _shared import inject_base_css, PAGE_ICON, BRAND_COLOR
from analytics import queries as q
import plotly.express as px

st.set_page_config(page_title="Mentors", page_icon=PAGE_ICON, layout="wide")
inject_base_css(st)
st.title("🧑‍🏫 Mentors")

mentors = q.load_mentors()
load_balance = q.mentor_load_balance()

tab1, tab2 = st.tabs(["Directory", "Load Balance (who's overbooked?)"])

with tab1:
    with st.sidebar:
        st.header("Filters")
        expertise = st.multiselect("Expertise", sorted(mentors["expertise"].unique()))
    filtered = mentors.copy()
    if expertise:
        filtered = filtered[filtered["expertise"].isin(expertise)]
    st.caption(f"Showing {len(filtered)} of {len(mentors)} mentors")
    st.dataframe(
        filtered.rename(columns={
            "name": "Mentor", "expertise": "Expertise", "years_experience": "Years Experience",
            "avg_rating": "Self-Reported Rating", "mentor_type": "Type", "joined_date": "Joined",
        }).drop(columns=["mentor_id"]),
        width="stretch", height=500,
    )

    st.subheader("Top Rated Mentors (from logged sessions)")
    top = q.top_mentors_by_rating(15)
    fig = px.bar(top, x="avg_logged_rating", y="name", orientation="h",
                 color_discrete_sequence=[BRAND_COLOR],
                 labels={"avg_logged_rating": "Avg Session Rating", "name": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch")

with tab2:
    st.caption(
        "Flags mentors who are logging far more or far fewer sessions than the "
        "network median, so program staff can rebalance mentor assignments."
    )
    status_filter = st.multiselect("Status", ["Overloaded", "Balanced", "Underutilized"],
                                    default=["Overloaded", "Underutilized"])
    lb = load_balance[load_balance["status"].isin(status_filter)] if status_filter else load_balance
    st.dataframe(
        lb.rename(columns={
            "name": "Mentor", "expertise": "Expertise",
            "session_count": "Sessions Logged", "status": "Status",
        }).drop(columns=["mentor_id"]),
        width="stretch", height=450,
    )
    counts = load_balance["status"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    fig2 = px.pie(counts, names="status", values="count", hole=0.4,
                  color_discrete_sequence=px.colors.sequential.Purples_r)
    st.plotly_chart(fig2, width="stretch")
