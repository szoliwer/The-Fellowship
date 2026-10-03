"""Step 4 review screen ("Your ideas"). Run from the repo root:

    .venv/bin/streamlit run "4 - Idea Ranking/app.py" --server.address localhost --browser.gatherUsageStats false

Shows the signed-in user's ranked ideas, most central first, all checked.
They uncheck or remove anything they don't want used for matching, then press
the one button at the bottom. Only checked ideas and details are saved for Step 5.
All the rules live in review.py; this file only draws the screen.
"""

import re

import streamlit as st

import review as rv

st.set_page_config(page_title="Your ideas", page_icon="🔬", initial_sidebar_state="collapsed")


# ---------- Small helpers ----------

def md(text):
    """Show idea text literally (a '$' or '*' from a chat must not turn into maths or bold)."""
    return re.sub(r"([\\`*_\[\]$~<>#|])", r"\\\1", text)


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def short(text, n=48):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def entry():
    return st.session_state["review"]


def card(idea_id):
    return next(c for c in entry()["cards"] if c["idea_id"] == idea_id)


def wkey(kind, item_id):
    return f"{entry()['user_id']}:{kind}:{item_id}"


# ---------- Who is signed in (placeholder until the steps are joined) ----------

users = rv.available_users()
current = st.session_state.get("user_id") or (users[0] if users else "user_a")
with st.sidebar:
    st.caption("Demo controls")
    if users:
        current = st.selectbox(
            "Signed-in user",
            users,
            index=users.index(current) if current in users else 0,
            help="Temporary: this will come from the sign-up screen (Step 0) once the steps are joined.",
        )
st.session_state["user_id"] = current

if st.session_state.get("review", {}).get("user_id") != current:
    try:
        rows, is_sample = rv.load_ranked_rows(current)
        cards = rv.build_cards(rows)
        st.session_state["review"] = {
            "user_id": current,
            "cards": cards,
            "is_sample": is_sample,
            "state": rv.start_state(current, cards),
            "saved": rv.load_saved_record(current),
            "open": set(),
            "error": None,
        }
    except rv.ReviewError as e:
        st.error(e.message)
        st.stop()


# ---------- What each click does (the rules are in review.py) ----------

def on_idea(idea_id):
    rv.toggle_idea(entry()["state"], card(idea_id))


def on_sub(idea_id, sub_id):
    rv.toggle_sub(entry()["state"], card(idea_id), sub_id)


def on_remove_idea(idea_id):
    rv.remove_idea(entry()["state"], card(idea_id))


def on_remove_sub(idea_id, sub_id):
    rv.remove_sub(entry()["state"], card(idea_id), sub_id)


def on_undo():
    rv.undo(entry()["state"])


def on_restore_all():
    rv.restore_all(entry()["state"], entry()["cards"])


def on_open(idea_id):
    entry()["open"] ^= {idea_id}  # show / hide the details


def on_save():
    e = entry()
    try:
        rv.save_approved(e["user_id"], e["state"], e["cards"])
    except rv.ReviewError as err:
        e["error"] = err.message
        return
    e["saved"] = rv.review_record(e["state"], e["cards"])
    e["error"] = None


# ---------- The screen ----------

e = entry()
state, cards = e["state"], e["cards"]
pending = (state.get("undo") or {}).get("id")

st.title("Your ideas")
st.caption("From your chats, most central first. People you match with see only what's checked, never your chats.")


def draw_removed(label, idea_id, sub=False):
    """The 'Removed · Undo' line shown in place of what was just removed."""
    cols = st.columns([0.05, 0.80, 0.15] if sub else [0.85, 0.15], vertical_alignment="center")
    cols[-2].caption(f"Removed “{md(short(label))}”")
    cols[-1].button("Undo", key=wkey("undo", idea_id), on_click=on_undo, type="tertiary")


for c in rv.visible_cards(state, cards):
    idea_id = c["idea_id"]
    with st.container(border=True):
        if state["ideas"][idea_id]["removed"]:
            draw_removed(c["title"], idea_id)
            continue

        status = rv.idea_status(state, c)
        live = rv.live_subs(state, c)
        is_open = idea_id in e["open"]

        top = st.columns([0.74, 0.18, 0.08], vertical_alignment="center")
        k = wkey("idea", idea_id)
        st.session_state[k] = status != "none"
        top[0].checkbox(f"**{md(c['title'])}**" if status != "none" else f":gray[{md(c['title'])}]",
                        key=k, on_change=on_idea, args=(idea_id,))
        if live:
            n_on = sum(rv.sub_is_on(state, c, s["sub_id"]) for s in live)
            label = f"{n_on} of {len(live)} details" if status == "some" else plural(len(live), "detail")
            arrow = ":material/expand_less:" if is_open else ":material/expand_more:"
            top[1].button(f"{label} {arrow}", key=wkey("open", idea_id), on_click=on_open, args=(idea_id,),
                          type="tertiary", help="Hide details" if is_open else "Show details")
        top[2].button(":material/delete:", key=wkey("del", idea_id), on_click=on_remove_idea, args=(idea_id,),
                      type="tertiary", help="Remove this idea")

        if not is_open:
            continue
        for s in c["subs"]:
            sub_id = s["sub_id"]
            if state["subs"][sub_id]["removed"]:
                if sub_id == pending:
                    draw_removed(s["text"], sub_id, sub=True)
                continue
            row = st.columns([0.05, 0.87, 0.08], vertical_alignment="center")
            k = wkey("sub", sub_id)
            on = rv.sub_is_on(state, c, sub_id)
            st.session_state[k] = on
            row[1].checkbox(md(s["text"]) if on else f":gray[{md(s['text'])}]",
                            key=k, on_change=on_sub, args=(idea_id, sub_id))
            row[2].button(":material/delete:", key=wkey("delsub", sub_id), on_click=on_remove_sub,
                          args=(idea_id, sub_id), type="tertiary", help="Remove this detail")

if all(state["ideas"][c["idea_id"]]["removed"] for c in cards):
    if cards:
        st.info("You removed every idea, so there is nothing to use for matching yet.")
        st.button("Restore removed ideas", on_click=on_restore_all)
    else:
        st.info("No ideas yet. They appear here once your chats have been imported and analysed.")

# ---------- The one button ----------

ideas, details = rv.counts(state, cards)
saved = e["saved"]
if e["error"]:
    st.error(e["error"])
if cards and saved == rv.review_record(state, cards):
    if ideas:
        st.success(f"Saved. {plural(ideas, 'idea')} and {plural(details, 'detail')} will be used for matching. "
                   "You can change this any time.")
    else:
        st.success("Saved. None of your ideas will be used for matching.")
elif ideas:
    st.button(f"Use {plural(ideas, 'idea')} for matching", type="primary", on_click=on_save)
elif saved and saved.get("approved"):
    # Ideas were shared earlier and now nothing is checked: let them withdraw in one click.
    st.button("Stop using my ideas for matching", on_click=on_save)
elif cards:
    st.button("Check at least one idea to continue", disabled=True)

if e["is_sample"]:
    st.caption("Demo: these ideas are synthetic sample data, not anyone's real chats.")
