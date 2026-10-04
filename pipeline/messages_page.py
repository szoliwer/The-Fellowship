"""Page "Messages": chat with the people you're connected with (both said yes on Discover).
PLACEHOLDER for Step 6's own chat (Oliver + Colin's desktop mockup in 6 - Matching Interface/):
your connections on the left, the conversation on the right, the warm intro pinned at the top.
Text only for now; voice notes, sharing a past AI chat, the AI's nudges and sounds aren't built yet.
The rules live in pipeline/messages.py."""

import html
from datetime import datetime

import streamlit as st

from pipeline import brand
from pipeline import messages as msg

KIND = {"both": "Similar and complementary", "similar": "Similar work", "complementary": "Complementary"}
REFRESH = "3s"  # how often an open page checks for new messages


def _when(iso):
    t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    return t.strftime("%H:%M") if t.date() == datetime.now().astimezone().date() else t.strftime("%-d %b, %H:%M")


def _bubble(m, me):
    """One message. Text is escaped: it was typed by a person."""
    side = "me" if m["from"] == me else "them"
    text = html.escape(m["text"]).replace("\n", "<br>")
    return f'<div class="fs-msg {side}"><div>{text}</div><span>{_when(m["at"])}</span></div>'


def _intro_html(c):
    kind = KIND.get(c["match_type"])
    head = "Warm introduction · both of you see this" + (f" · {kind}" if kind else "")
    body = c["intro"] or f"You and {c['other_name']} both said yes. Say hello and share what you're working on."
    return (f'<div class="fs-intro"><span class="fs-tag">{html.escape(head)}</span>'
            f'<p>{html.escape(body)}</p></div>')


def _select(other_id):
    st.session_state["msg_with"] = other_id


def _send(me):
    text = st.session_state.get("msg_draft")
    try:
        msg.send(me, st.session_state["msg_with"], text)
    except msg.MessageError as e:
        st.session_state["msg_error"] = e.message


@st.fragment(run_every=REFRESH)
def _people(me):
    """Left: everyone you're connected with, with a count of new messages."""
    for c in msg.conversations(me):
        chosen = c["other_id"] == st.session_state.get("msg_with")
        label = c["other_name"] + (f" · {c['unread']} new" if c["unread"] and not chosen else "")
        if st.button(label, key=f"with_{c['other_id']}", type="primary" if chosen else "secondary",
                     icon=":material/account_circle:", use_container_width=True):
            _select(c["other_id"])
            st.rerun(scope="app")  # the message box below the conversation changes too


@st.fragment(run_every=REFRESH)
def _conversation(me):
    """Right: the warm intro, then the messages, newest at the bottom. Checks for new ones by itself."""
    c = next((c for c in msg.conversations(me) if c["other_id"] == st.session_state.get("msg_with")), None)
    if c is None:
        return
    st.html(f'<div class="fs-chat-head"><b>{html.escape(c["other_name"])}</b>'
            f'<span class="fs-muted">Known to you by username only</span></div>')
    with st.container(height=400, autoscroll=True, key="fs_thread"):
        st.html(_intro_html(c) + "".join(_bubble(m, me) for m in c["messages"]))
        if not c["messages"]:
            st.caption("No messages yet. Either of you can write first.")
    if c["unread"]:
        msg.mark_read(me, c["other_id"])


def render(user):
    me = user["user_id"]
    brand.wide_page()
    brand.eyebrow("After you both say yes")
    st.title("Messages")

    convos = msg.conversations(me)
    if not convos:
        brand.empty_state("No conversations yet", "When you and a match both say yes on Discover, you can "
                          "message each other here.", go_to="Discover", go_label="Go to Discover")
        return
    if st.session_state.get("msg_with") not in [c["other_id"] for c in convos]:
        _select(convos[0]["other_id"])
    name = next(c["other_name"] for c in convos if c["other_id"] == st.session_state["msg_with"])

    left, right = st.columns([1, 2.4], gap="medium")
    with left:
        st.caption("Your connections")
        _people(me)
    with right:
        _conversation(me)
        st.chat_input(f"Message {name}", key="msg_draft", max_chars=msg.MAX_LENGTH, on_submit=_send, args=(me,))
        error = st.session_state.pop("msg_error", None)
        if error:
            st.error(error)
