import streamlit as st
from _shared import inject_base_css, PAGE_ICON, BRAND_COLOR
from analytics import queries as q
import plotly.express as px

st.set_page_config(page_title="Events", page_icon=PAGE_ICON, layout="wide")
inject_base_css(st)
st.title("📅 Events & ROI")

st.caption(
    "Event ROI is a proxy signal: cost per attendee, and how much funding "
    "attending startups raised within 60 days of the event. This is a "
    "correlation, not a proven causal effect -- use it to prioritize which "
    "event formats to repeat, not as a hard financial metric."
)

roi = q.event_roi()

col1, col2 = st.columns(2)
with col1:
    st.metric("Total Events", len(roi))
    st.metric("Total Event Spend", f"${roi['cost_usd'].sum():,.0f}")
with col2:
    st.metric("Total Follow-on Funding (60d window)", f"${roi['follow_on_funding_60d'].sum():,.0f}")
    st.metric("Avg Cost per Attendee", f"${roi['cost_per_attendee'].dropna().mean():,.0f}")

event_type_filter = st.multiselect("Event type", sorted(roi["event_type"].unique()))
filtered = roi[roi["event_type"].isin(event_type_filter)] if event_type_filter else roi

st.dataframe(
    filtered.rename(columns={
        "name": "Event", "event_type": "Type", "cost_usd": "Cost ($)",
        "attendees": "Attendees", "cost_per_attendee": "Cost/Attendee ($)",
        "startups_that_raised_within_60d": "Startups Funded (60d)",
        "follow_on_funding_60d": "Follow-on Funding, 60d ($)",
    }).drop(columns=["event_id"]),
    width="stretch", height=450,
)

fig = px.bar(filtered.sort_values("follow_on_funding_60d", ascending=False).head(15),
             x="follow_on_funding_60d", y="name", orientation="h", color="event_type",
             labels={"follow_on_funding_60d": "Follow-on Funding, 60d ($)", "name": ""})
fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=10, b=10))
st.plotly_chart(fig, width="stretch")

fig2 = px.scatter(filtered, x="cost_per_attendee", y="follow_on_funding_60d",
                   color="event_type", size="attendees", hover_name="name",
                   labels={"cost_per_attendee": "Cost per Attendee ($)",
                           "follow_on_funding_60d": "Follow-on Funding, 60d ($)"})
st.plotly_chart(fig2, width="stretch")
