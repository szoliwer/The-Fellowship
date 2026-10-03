"""The Fellowship: the shared app that joins the steps' screens.

Run from the repo root:
    .venv/bin/streamlit run app.py

Each step keeps its logic and screens in its own folder; this file only decides
which screen to show. Add later steps' screens here the same way.
"""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
for step_folder in ["0 - User Registration", "1 - Data Collection", "2 - Noise Filter"]:
    sys.path.insert(0, str(ROOT / step_folder))

import filter_ui  # noqa: E402  (Step 2)
import import_ui  # noqa: E402  (Step 1)
import signup_ui  # noqa: E402  (Step 0)

st.set_page_config(page_title="The Fellowship", page_icon="🔬")


@st.cache_resource
def _refresh_users_file():
    """Once per app start: rewrite data/users.json (read by later steps) in the current format."""
    signup_ui.reg.export_users()


_refresh_users_file()

user = signup_ui.current_user()
if user is None:
    signup_ui.render()
    st.stop()

PAGES = {"1. Import chats": import_ui.render, "2. Privacy screening": filter_ui.render}

with st.sidebar:
    st.markdown(f"Logged in as **{user['pseudonym']}**")
    if user["is_demo_account"]:
        st.caption("Synthetic demo account")
    page = st.radio("Go to", list(PAGES), label_visibility="collapsed")
    if st.button("Log out"):
        signup_ui.log_out()
        st.rerun()

PAGES[page](user)
