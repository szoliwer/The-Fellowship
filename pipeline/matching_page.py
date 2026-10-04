"""Page 5 "Find matches": runs Step 5 (Oliver + Colin's match_generation.py) across everyone
who approved ideas in Step 4. Inputs: data/ideas.json (Step 4, approved ideas only) and
data/users.json (Step 0: pseudonyms, consent). Output: data/matches.json."""

import json
from datetime import datetime

import streamlit as st

import registration as reg        # Step 0 (refreshes data/users.json)
from pipeline import brand
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
    st.title("Find your matches")
    brand.lead("Matching compares <b>only the ideas people approved</b>, never their chats. People see each "
               "other by username, and anyone who declined consent is left out.")
    people = _approved_people()
    me = people.get(user_id, 0)
    if not me:
        brand.empty_state("You haven't approved any ideas yet",
                          "Choose which of your ideas may be used for matching first. Until then, nobody "
                          "can be matched with you.", go_to="Review", go_label="Go to Review")
    st.markdown(f"**{brand.plural(len(people), 'researcher')}** "
                f"{'has' if len(people) == 1 else 'have'} approved ideas for matching"
                + (f", including you ({brand.plural(me, 'idea')})." if me else "."))

    if mt.MATCHES_FILE.exists():
        data = json.loads(mt.MATCHES_FILE.read_text(encoding="utf-8"))
        when = datetime.fromisoformat(data["generated_at"]).astimezone().strftime("%-d %b at %H:%M")
        mine = len(mt.my_matches(user_id))
        st.caption(f"Last run {when} · {brand.plural(mine, 'match', 'matches')} for you.")

    if len(people) < 2:
        st.caption("Matching can run once at least two researchers have approved ideas.")
        return
    st.caption("Runs for everyone at once and takes about a minute.")
    if st.button("Find matches", type="primary"):
        _run()
