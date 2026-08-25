import streamlit as st
from _shared import inject_base_css, PAGE_ICON, BRAND_COLOR
from analytics import queries as q
import plotly.express as px

st.set_page_config(page_title="Startups", page_icon=PAGE_ICON, layout="wide")
inject_base_css(st)
st.title("🏢 Startups")

startups = q.load_startups()
health = q.startup_health_score()[["startup_id", "health_score", "total_raised", "session_count", "avg_rating"]]
merged = startups.merge(health, on="startup_id", how="left")

with st.sidebar:
    st.header("Filters")
    industries = st.multiselect("Industry", sorted(startups["industry"].unique()))
    stages = st.multiselect("Stage", sorted(startups["stage"].unique()))
    active_only = st.checkbox("Active only", value=False)
    search = st.text_input("Search by name")

filtered = merged.copy()
if industries:
    filtered = filtered[filtered["industry"].isin(industries)]
if stages:
    filtered = filtered[filtered["stage"].isin(stages)]
if active_only:
    filtered = filtered[filtered["active"] == 1]
if search:
    filtered = filtered[filtered["name"].str.contains(search, case=False, na=False)]

st.caption(f"Showing {len(filtered)} of {len(merged)} startups")

col1, col2 = st.columns([2, 1])
with col1:
    st.dataframe(
        filtered[["name", "industry", "stage", "founder_name", "employee_count",
                  "total_raised", "health_score", "avg_rating"]]
        .rename(columns={
            "name": "Startup", "industry": "Industry", "stage": "Stage",
            "founder_name": "Founder", "employee_count": "Employees",
            "total_raised": "Total Raised ($)", "health_score": "Health Score",
            "avg_rating": "Avg Mentor Rating",
        })
        .sort_values("Health Score", ascending=False),
        width="stretch", height=520,
    )
with col2:
    st.subheader("Health Score Distribution")
    fig = px.histogram(filtered, x="health_score", nbins=20, color_discrete_sequence=[BRAND_COLOR])
    fig.update_layout(margin=dict(t=10, b=10), xaxis_title="Health Score", yaxis_title="Count")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Employees vs. Funding")
    fig2 = px.scatter(filtered, x="employee_count", y="total_raised", color="stage",
                       hover_name="name", labels={"employee_count": "Employees", "total_raised": "Total Raised ($)"})
    fig2.update_layout(margin=dict(t=10, b=10))
    st.plotly_chart(fig2, width="stretch")

st.divider()
st.subheader("Startup 360 View")
selected_name = st.selectbox("Select a startup for full profile", filtered["name"].sort_values())
if selected_name:
    row = filtered[filtered["name"] == selected_name].iloc[0]
    profile_data = q.startup_profile_with_pressure(int(row["startup_id"]))
    c1, c2, c3 = st.columns(3)
    c1.metric("Health Score", f"{row['health_score']:.1f}/100")
    c1.metric("Total Raised", f"${row['total_raised']:,.0f}")
    c2.metric("Mentorship Sessions", int(row["session_count"]))
    c2.metric("Avg Mentor Rating", f"{row['avg_rating']:.1f}/5" if row["avg_rating"] == row["avg_rating"] else "n/a")
    c3.metric("Stage", row["stage"])
    c3.metric("Employees", int(row["employee_count"]))

    profile = profile_data["profile"]
    if profile:
        st.write("**Tags:**", ", ".join(profile.get("tags", [])))
        st.write("**Website:**", profile.get("website"))
    press = profile_data["press_mentions"]
    if press:
        st.write("**Press mentions:**")
        for p in press:
            st.write(f"- *{p['outlet']}*: {p['headline']} ({p['published_date']}, {p['sentiment']})")
    else:
        st.caption("No press mentions on file.")
