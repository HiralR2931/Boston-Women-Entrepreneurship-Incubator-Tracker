import streamlit as st
from _shared import inject_base_css, PAGE_ICON
from analytics import queries as q

st.set_page_config(page_title="Mentor Matching", page_icon=PAGE_ICON, layout="wide")
inject_base_css(st)
st.title("🤝 Mentor Matching Recommender")

st.caption(
    "Rule-based recommender: ranks mentors for a chosen startup by expertise fit "
    "for that startup's funding stage, historical session ratings, and current "
    "mentor workload (so busy mentors aren't over-assigned). This is a decision-support "
    "tool for program staff, not an automated assignment system."
)

startups = q.load_startups()
selected_name = st.selectbox("Choose a startup", startups["name"].sort_values())
top_n = st.slider("Number of recommendations", 3, 10, 5)

if selected_name:
    startup_id = int(startups[startups["name"] == selected_name].iloc[0]["startup_id"])
    stage = startups[startups["name"] == selected_name].iloc[0]["stage"]
    st.write(f"**Stage:** {stage}")

    recs = q.mentor_matching_recommendations(startup_id, top_n=top_n)
    if recs.empty:
        st.warning("No mentors found.")
    else:
        for _, r in recs.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{r['name']}** — *{r['expertise']}*")
                    st.caption(r["match_reason"])
                with c2:
                    st.metric("Match Score", f"{r['match_score']:.0f}/100")
