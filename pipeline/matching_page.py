"""Page 5 "Find matches": runs Step 5 (Oliver + Colin's match_generation.py) across everyone
who approved ideas in Step 4. Inputs: data/ideas.json (Step 4, approved ideas only) and
data/users.json (Step 0: pseudonyms, consent). Output: data/matches.json."""

import json
from datetime import datetime

import streamlit as st

import registration as reg        # Step 0 (refreshes data/users.json)
from pipeline import matches as mt

USERS_FILE = reg.USERS_EXPORT_FILE


def _approved_people():
    if not mt.IDEAS_FILE.exists():
        return {}
    data = json.loads(mt.IDEAS_FILE.read_text(encoding="utf-8"))
    people = {}
    for row in data.get("ideas", []) if isinstance(data, dict) else data:
        people[row.get("user_id")] = people.get(row.get("user_id"), 0) + 1
    return people


def _run():
    import match_generation as mg  # Step 5; imported here so the rest of the app works without numpy/sklearn

    reg.export_users()
    with st.spinner("Comparing everyone's approved ideas… this can take a minute."):
        try:
            mg.run(str(mt.IDEAS_FILE), str(mt.MATCHES_FILE), mg.Settings(), users_path=str(USERS_FILE))
        except Exception as e:  # show the kind of error, never idea text
            st.error(f"Matching failed ({type(e).__name__}). Try again in a moment.")
            return
    st.rerun()


def render(user):
    user_id = user["user_id"]
    st.title("Find matches")
    st.info(
        "Matching compares **only ideas people approved** on page 4, never chats. People are shown "
        "to each other by pseudonym, and anyone who declined consent is left out.",
        icon="🤝",
    )
    people = _approved_people()
    me = people.get(user_id, 0)
    st.markdown(f"**{len(people)} researcher(s)** have approved ideas for matching"
                + (f", including you ({me} idea(s))." if me else ". You haven't approved any yet (page 4)."))

    if mt.MATCHES_FILE.exists():
        data = json.loads(mt.MATCHES_FILE.read_text(encoding="utf-8"))
        when = datetime.fromisoformat(data["generated_at"]).strftime("%d %b %H:%M UTC")
        mine = len(mt.my_matches(user_id))
        st.caption(f"Last run: {when} ({data.get('mode', '?')} mode) · {len(data.get('matches', []))} match(es) "
                   f"in total · {mine} for you.")

    if len(people) < 2:
        st.warning("At least two researchers need approved ideas before matching can run.")
        return
    st.caption("Runs for everyone at once. With an AI key it uses Claude (a few cents); without one, "
               "a simpler offline comparison.")
    if st.button("Find matches", type="primary"):
        _run()
    if mt.MATCHES_FILE.exists():
        st.success("Next: **6. Discover**: see your matches and say yes or pass.")
