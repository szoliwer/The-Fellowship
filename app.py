"""The Fellowship: the shared app that joins the steps' screens, Step 0 to Step 6.

Run from the repo root:
    .venv/bin/streamlit run app.py

Each step keeps its logic and screens in its own folder; this file only decides which screen
to show. Glue between steps, and placeholders for unbuilt parts, live in pipeline/.
"""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
STEP_FOLDERS = ["0 - User Registration", "1 - Data Collection", "2 - Noise Filter",
                "3 - Idea Generation", "4 - Idea Ranking", "5 - Match Generation"]
for step_folder in STEP_FOLDERS:
    sys.path.insert(0, str(ROOT / step_folder))
sys.path.insert(0, str(ROOT))

import filter_ui  # noqa: E402  (Step 2)
import import_ui  # noqa: E402  (Step 1)
import signup_ui  # noqa: E402  (Step 0)
from pipeline import discover_page, ideas_page, matching_page  # noqa: E402  (Steps 3, 5, 6)

st.set_page_config(page_title="The Fellowship", page_icon="🔬")


@st.cache_resource
def _refresh_users_file():
    """Once per app start: rewrite data/users.json (read by later steps) in the current format."""
    signup_ui.reg.export_users()


_refresh_users_file()

user = signup_ui.current_user()
if user is None:
    st.session_state.pop("fellowship_logged_in_user", None)
    signup_ui.render()
    st.stop()

# Tells Step 4's page (its own file) who is logged in, so it never offers to switch user.
st.session_state["fellowship_logged_in_user"] = user["user_id"]


def import_chats():
    import_ui.render(user)


def privacy_screening():
    filter_ui.render(user)


def find_ideas():
    ideas_page.render(user)


def find_matches():
    matching_page.render(user)


def discover():
    discover_page.render(user)


pages = [
    st.Page(import_chats, title="1. Import chats", url_path="import", default=True),
    st.Page(privacy_screening, title="2. Privacy screening", url_path="screening"),
    st.Page(find_ideas, title="3. Find my ideas", url_path="ideas"),
    st.Page(ROOT / "4 - Idea Ranking" / "app.py", title="4. Review ideas", url_path="review"),
    st.Page(find_matches, title="5. Find matches", url_path="matching"),
    st.Page(discover, title="6. Discover", url_path="discover"),
]
nav = st.navigation(pages)

with st.sidebar:
    st.markdown(f"Logged in as **{user['pseudonym']}**")
    if user["is_demo_account"]:
        st.caption("Synthetic demo account")
    if st.button("Log out"):
        signup_ui.log_out()
        for key in ("fellowship_logged_in_user", "review"):
            st.session_state.pop(key, None)
        st.rerun()

nav.run()
