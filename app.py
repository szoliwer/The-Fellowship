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
for step_folder in ["0 - User Registration", "1 - Data Collection"]:
    sys.path.insert(0, str(ROOT / step_folder))

import import_ui  # noqa: E402  (Step 1)
import signup_ui  # noqa: E402  (Step 0)

st.set_page_config(page_title="The Fellowship", page_icon="🔬")

user = signup_ui.current_user()
if user is None:
    signup_ui.render()
    st.stop()

with st.sidebar:
    st.markdown(f"Logged in as **{user['pseudonym']}**")
    if user["is_demo_account"]:
        st.caption("Synthetic demo account")
    if st.button("Log out"):
        signup_ui.log_out()
        st.rerun()

import_ui.render(user)
