"""Page 6 "Discover": PLACEHOLDER for Step 6 (Oliver + Colin) so the whole flow can be tested.
Replace with Step 6's own render(user) when it exists (see the mockups in 6 - Matching Interface/)."""

import streamlit as st

from pipeline import matches as mt

TYPE_LABELS = {"similar": "Similar work", "complementary": "Complementary", "both": "Similar and complementary"}


def render(user):
    user_id = user["user_id"]
    st.title("Discover")
    st.caption("Placeholder screen until Step 6's own page is built. Uses the real matches and decisions.")

    mine = mt.my_matches(user_id)
    if not mt.MATCHES_FILE.exists():
        st.info("No matches yet. Run **5. Find matches** first.")
        return
    if not mine:
        st.info("No matches for you in the latest run. That's better than a weak match: "
                "add more chats or approve more ideas, then run matching again.")
        return

    order = {"connected": 0, "new": 1, "waiting": 2, "passed": 3}
    for m in sorted(mine, key=lambda m: order[m["state"]]):
        with st.container(border=True):
            st.markdown(f"### {m['other_name']}")
            st.caption(TYPE_LABELS.get(m["match_type"], "Match"))
            if m["state"] == "connected":
                st.success("You both said yes 🎉")
                st.markdown(f"**Warm introduction:** {m['intro']}")
                st.caption("Pseudonymous: neither of you sees the other's name or contact details unless "
                           "you choose to share them.")
            if m["reason"]:
                st.markdown(f"**Why you match:** {m['reason']}")
            if m["they_can_offer"]:
                st.markdown(f"**What they've explored that may help you:** {m['they_can_offer']}")
                st.caption("Based on what each of you approved; absence from your chats doesn't mean you "
                           "haven't thought about it.")
            if m["you_can_offer"]:
                st.markdown(f"**What you might add for them:** {m['you_can_offer']}")
            for yours, theirs in m["linked"]:
                st.markdown(f"- Your idea *{yours}* ↔ their idea *{theirs}*")

            if m["state"] == "new":
                left, right = st.columns(2)
                left.button("Connect", key=f"connect_{m['other_id']}", type="primary", use_container_width=True,
                            on_click=mt.decide, args=(user_id, m["other_id"], "connect"))
                right.button("Pass", key=f"pass_{m['other_id']}", use_container_width=True,
                             on_click=mt.decide, args=(user_id, m["other_id"], "pass"))
            elif m["state"] == "waiting":
                st.info("You said yes. If they say yes too, you'll both see a warm introduction here.")
            elif m["state"] == "passed":
                st.caption("You passed on this match.")
