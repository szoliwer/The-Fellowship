"""Page 3 "Find my ideas": runs Step 3 (Aman's idea_generation.py) for the logged-in user on
their screened chats (Step 2's handoff files), then the placeholder ranking for Step 4."""

import json

import streamlit as st

import idea_generation as ig      # Step 3
import screening as sc            # Step 2 (where the screened chats are, and the API key check)
from pipeline import brand, ranking

TYPE_LABELS = {"project": "Working on", "interest": "Curious about", "skill": "Can offer", "need": "Looking for"}


def _screened_chats(user_id):
    folder = sc.OUTPUT_DIR / user_id
    return sorted(p.stem for p in folder.glob("*.md")) if folder.exists() else []


def _saved_result(user_id):
    path = ig.DEFAULT_OUTPUT_DIR / f"{user_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _run(user_id):
    with st.spinner("Reading your screened chats and finding your ideas… this can take a minute or two."):
        try:
            ig.run_user(user_id)
            ranking.rank_user(user_id)
        except ig.ModelDeclined:
            st.error("The AI service declined to analyse these chats. Nothing was saved.")
            return
        except Exception as e:  # API/network errors from the step: show the kind, never chat text
            st.error(f"Finding ideas failed ({type(e).__name__}). Try again in a moment.")
            return
    st.session_state.pop("review", None)  # make page 4 reload the new ideas
    st.rerun()


def render(user):
    user_id = user["user_id"]
    st.title("Find your ideas")
    brand.lead("Claude reads the chats that passed the privacy check and lists your ideas, questions, "
               "skills and needs. Nothing is shared yet.")

    chats = _screened_chats(user_id)
    result = _saved_result(user_id)
    if not chats:
        brand.empty_state("No checked chats yet", "Import some chats and run the privacy check first. "
                          "Only chats that pass it are read here.", go_to="Privacy", go_label="Go to Privacy check")
        return

    stale = result is not None and sorted(result.get("chats_read", [])) != chats
    st.markdown(f"**{brand.plural(len(chats), 'checked chat')}** ready."
                + (" Some have changed since your ideas were found, so find them again." if stale else ""))
    if not sc.api_key_available():
        st.warning("Finding ideas isn't set up on this computer yet (it needs an Anthropic API key).",
                   icon=":material/key:")
    else:
        label = "Find my ideas" if result is None else "Find my ideas again"
        st.caption("Takes a minute or two.")
        if st.button(label, type="primary" if result is None or stale else "secondary"):
            _run(user_id)

    if result is None:
        return
    ideas = result.get("ideas", [])
    st.subheader(f"Your ideas ({len(ideas)})")
    if not ideas:
        st.caption("No ideas found in these chats.")
    for row in ranking.score_rows(ideas):
        with st.expander(f"{TYPE_LABELS.get(row.get('type'), 'Idea')}: {row.get('summary', '')}"):
            for insight in row.get("insights") or []:
                st.markdown(f"- {insight}")
            st.caption(f"From {brand.plural(row.get('chat_count', 0), 'chat')}, "
                       f"last seen {row.get('last_seen', 'unknown')}")
    adjacent = result.get("adjacent_ideas") or []
    if adjacent:
        with st.expander(f"Suggestions that connect your ideas ({len(adjacent)}): speculative, not yours"):
            for a in adjacent:
                st.markdown(f"- **{a.get('handle', '')}**: {a.get('claim', '')}")
