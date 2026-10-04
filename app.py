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
import screening  # noqa: E402  (Step 2: forgets chats removed in Step 1)
import signup_ui  # noqa: E402  (Step 0)
from pipeline import brand, discover_page, ideas_page, landing, matching_page  # noqa: E402  (look; Steps 3, 5, 6)

st.set_page_config(page_title=brand.NAME, page_icon=str(brand.ICON))
st.logo(str(brand.LOGO), icon_image=str(brand.ICON), size="large")


@st.cache_resource
def _refresh_users_file():
    """Once per app start: rewrite data/users.json (read by later steps) in the current format."""
    signup_ui.reg.export_users()


_refresh_users_file()

user = signup_ui.current_user()
if user is None:
    st.session_state.pop("fellowship_logged_in_user", None)
    landing.render()
    st.stop()

# Tells Step 4's page (its own file) who is logged in, so it never offers to switch user.
st.session_state["fellowship_logged_in_user"] = user["user_id"]


def import_chats():
    import_ui.render(user, on_removed=screening.sync_with_sources)


def privacy_screening():
    filter_ui.render(user)


def find_ideas():
    ideas_page.render(user)


def find_matches():
    matching_page.render(user)


def discover():
    discover_page.render(user)


def account():
    signup_ui.render_account(user)


pages = [
    st.Page(import_chats, title="Import", icon=":material/upload_file:", url_path="import", default=True),
    st.Page(privacy_screening, title="Privacy", icon=":material/shield:", url_path="screening"),
    st.Page(find_ideas, title="Ideas", icon=":material/lightbulb:", url_path="ideas"),
    st.Page(ROOT / "4 - Idea Ranking" / "app.py", title="Review", icon=":material/fact_check:", url_path="review"),
    st.Page(find_matches, title="Matches", icon=":material/hub:", url_path="matching"),
    st.Page(discover, title="Discover", icon=":material/handshake:", url_path="discover"),
    st.Page(account, title=user["pseudonym"], icon=":material/account_circle:", url_path="account"),
]
nav = st.navigation(pages, position="top")
brand.page_style()
if st.session_state.get("just_signed_in"):  # first few redraws after signing in: start at the top
    st.session_state["just_signed_in"] = st.session_state.get("_scroll_runs", 0) < 2
    st.session_state["_scroll_runs"] = st.session_state.get("_scroll_runs", 0) + 1
    brand.scroll_to_top()
brand.step_eyebrow(nav.title)
nav.run()
brand.next_step_button(nav.title, {page.title: page for page in pages})
