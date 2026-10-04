"""Step 2 screen: screen imported chats, see what's used and what's held back (and why).

Used by the shared app (app.py at the repo root) after the user has logged in.
"""

import streamlit as st

import screening as sc
from pipeline import brand  # shared look (intro text, cards, plurals)

POINTS = [
    ("Held back", "Mostly personal or off-topic chats, and any with passwords, card or ID numbers."),
    ("Cleaned", "Research chats with personal parts: those parts are blanked out and checked again."),
    ("Who reads them", "Chats with obvious secrets never leave this laptop. The rest are screened by "
                       "Anthropic's Claude."),
]


def _run_screening(user_id, total, retry_held_back=False):
    bar = st.progress(0.0, text=f"Screening 0 of {total}…")

    def progress(done, n):
        bar.progress(done / n, text=f"Screening {done} of {n}…")

    try:
        sc.screen_user(user_id, on_progress=progress, retry_held_back=retry_held_back)
    except sc.ScreeningError as e:
        st.error(e.message)
        return
    except ImportError:
        st.error("The Anthropic library isn't installed. Run: .venv/bin/pip install -r requirements.txt")
        return
    st.rerun()


def render(user):
    user_id = user["user_id"]
    st.title("Privacy check")
    brand.lead("Every chat is checked for personal information before anything is used.")
    brand.points(POINTS)
    with st.expander("What counts as personal"):
        st.markdown("Your name, record or applications; your health, money or private life; other people's "
                    "details; email drafts; ID numbers.")

    sources = sc.load_sources(user_id)
    if not sources:
        brand.empty_state("Nothing to check yet", "Import some chats first, then come back here.",
                          go_to="Import", go_label="Go to Import")
        return

    pending = sc.pending_sources(user_id)
    if pending:
        est = sc.estimate_cost(pending)
        st.markdown(f"**{brand.plural(len(pending), 'chat')} waiting to be screened.**")
        st.caption(f"{est['chats_to_send']} will be sent to Claude · estimated cost about ${est['dollars']:.2f}")
        if not sc.api_key_available():
            st.warning(
                "No AI key set up yet. Copy `.env.example` (repo root) to `.env` and paste your "
                "Anthropic API key after `ANTHROPIC_API_KEY=`, then restart the app.",
                icon=":material/key:",
            )
        elif st.button(f"Screen {brand.plural(len(pending), 'chat')}", type="primary"):
            _run_screening(user_id, len(pending))

    report = sc.load_report(user_id)
    screened = [(s, report[s["source_id"]]) for s in sources
                if s["source_id"] in report and not sc.needs_screening(s, report[s["source_id"]])]
    if not screened:
        return

    used = [(s, e) for s, e in screened if sc.is_eligible(e)]
    held = [(s, e) for s, e in screened if not sc.is_eligible(e)]
    failed = [e for _, e in held if e["status"] == "failed"]
    if failed:
        st.error(f"{brand.plural(len(failed), 'chat')} couldn't be screened: {failed[0]['explanation']} "
                 "They are held back until screening succeeds.")

    st.subheader(f"Used for ideas ({len(used)})")
    st.caption("Only these are read in the next step.")
    for s, e in used:
        cleaned = e["decision"] == "cleaned"
        blanked, removed = sc.cleaning_counts(e) if cleaned else (0, 0)
        label = f"{':material/cleaning_services:' if cleaned else ':material/check_circle:'} {e['title']}"
        if cleaned:
            label += (f" · {brand.plural(blanked, 'detail')} blanked, "
                      f"{removed} of {brand.plural(e['total_messages'], 'message')} removed")
        with st.expander(label):
            if cleaned:
                st.markdown(f"**{sc.cleaning_summary(e)}.** Only the cleaned copy is used "
                            f"(checked {len(e['recheck']) + 1} times). Please look it over below.")
            st.caption(e["explanation"])
            if cleaned and st.toggle("Show the cleaned copy (only you can see this)", key=f"show_{e['source_id']}"):
                st.text(sc.used_version(s, e)["raw_text"])
            if st.button("Hold this back", key=f"hold_{e['source_id']}"):
                sc.set_owner_excluded(user_id, e["source_id"], True)
                st.rerun()

    st.subheader(f"Held back ({len(held)})")
    st.caption("Never used or shown to anyone.")
    retry = sc.retry_candidates(user_id)
    if retry and not pending and sc.api_key_available():
        est = sc.estimate_cost(retry)
        st.caption(f"You can give held-back chats another try (about ${est['dollars']:.2f}).")
        if st.button(f"Try {brand.plural(len(retry), 'held-back chat')} again"):
            _run_screening(user_id, len(retry), retry_held_back=True)
    for s, e in held:
        with st.expander(f":material/block: {e['title']} · {sc.display_reason(e)}"):
            st.caption(e["explanation"])
            rechecks = e.get("recheck") if isinstance(e.get("recheck"), list) else []
            for n, r in enumerate(rechecks, start=1):
                st.caption(f"Check {n + 1} of the cleaned copy: {r['explanation']}")
            if e["owner_excluded"] and st.button("Undo: let screening decide", key=f"undo_{e['source_id']}"):
                sc.set_owner_excluded(user_id, e["source_id"], False)
                st.rerun()
