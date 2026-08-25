"""Shared setup imported by every Streamlit page: path bootstrap + theme constants."""
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

BRAND_COLOR = "#7A2E8E"
ACCENT_COLOR = "#F2A541"
PAGE_ICON = "🚀"


def inject_base_css(st):
    st.markdown(
        f"""
        <style>
        .kpi-card {{
            background: linear-gradient(135deg, {BRAND_COLOR} 0%, #4B1A57 100%);
            padding: 18px; border-radius: 12px; color: white; text-align: center;
        }}
        .kpi-value {{ font-size: 28px; font-weight: 700; margin: 0; }}
        .kpi-label {{ font-size: 13px; opacity: 0.85; margin: 0; }}
        h1, h2, h3 {{ color: {BRAND_COLOR}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(st, col, value, label):
    with col:
        st.markdown(
            f"""<div class="kpi-card"><p class="kpi-value">{value}</p>
            <p class="kpi-label">{label}</p></div>""",
            unsafe_allow_html=True,
        )
