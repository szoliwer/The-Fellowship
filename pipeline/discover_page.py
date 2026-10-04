"""Page 6 "Discover": PLACEHOLDER for Step 6 (Oliver + Colin) so the whole flow can be tested.
Replace with Step 6's own render(user) when it exists (see the mockups in 6 - Matching Interface/).
Each match is shown as the Lovable website's match card; the logic lives in pipeline/matches.py."""

import streamlit as st

from pipeline import brand
from pipeline import matches as mt

FOOTNOTES = {
    "new": "A conversation worth starting →",
    "waiting": "You said yes. Waiting for them",
    "connected": "You both said yes",
    "passed": "You passed on this match",
}


def render(user):
    user_id = user["user_id"]
    st.title("People you should know")
    st.caption("Placeholder screen until Step 6's own page is built. Uses the real matches and decisions.")

    mine = mt.my_matches(user_id)
    if not mt.MATCHES_FILE.exists():
        st.info("No matches yet. Run matching on the **Matches** page first.")
        return
    if not mine:
        st.info("No matches for you in the latest run. That's better than a weak match: "
                "add more chats or approve more ideas, then run matching again.")
        return

    order = {"connected": 0, "new": 1, "waiting": 2, "passed": 3}
    for m in sorted(mine, key=lambda m: order[m["state"]]):
        yours, theirs = m["linked"][0] if m["linked"] else ("Your approved ideas", m["other_summary"])
        st.html(brand.match_card_html(
            m["other_name"], m["other_name"], theirs, user["pseudonym"], yours, m["match_type"],
            "Meet. Learn. Collaborate.", m["reason"], FOOTNOTES[m["state"]]))

        if m["state"] == "connected":
            st.success(f"**Warm introduction:** {m['intro']}", icon=":material/celebration:")
            st.caption("Pseudonymous: neither of you sees the other's name or contact details unless "
                       "you choose to share them.")
        if m["they_can_offer"]:
            st.markdown(f"**What they've explored that may help you:** {m['they_can_offer']}")
            st.caption("Based on what each of you approved; absence from your chats doesn't mean you "
                       "haven't thought about it.")
        if m["you_can_offer"]:
            st.markdown(f"**What you might add for them:** {m['you_can_offer']}")
        for mine_idea, their_idea in m["linked"][1:]:
            st.markdown(f"- Your idea *{mine_idea}* ↔ their idea *{their_idea}*")

        if m["state"] == "new":
            with st.container(horizontal=True, gap="small"):
                st.button("Connect", key=f"connect_{m['other_id']}", type="primary",
                          icon=":material/handshake:", on_click=mt.decide, args=(user_id, m["other_id"], "connect"))
                st.button("Pass", key=f"pass_{m['other_id']}", on_click=mt.decide,
                          args=(user_id, m["other_id"], "pass"))
        st.html('<div style="height:2.5rem"></div>')
