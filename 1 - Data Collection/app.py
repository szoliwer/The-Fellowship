"""Step 1 import screen. Run from the repo root:

    .venv/bin/streamlit run "1 - Data Collection/app.py" --server.address localhost --browser.gatherUsageStats false

Until the steps are joined into one app, pick the signed-in user here
(Step 0 creates them; the demo users are user_a and user_b).
"""

import streamlit as st

import importer as im

st.set_page_config(page_title="Import your chats", page_icon="🔬")

st.title("Import your research chats")
st.info(
    "Importing is **private**. Your chats are stored only on this laptop and nobody else sees them. "
    "Next, personal or sensitive conversations are held back, and nothing is shared until you "
    "approve specific ideas later.",
    icon="🔒",
)

user_id = st.text_input(
    "Signed-in user ID",
    value=st.session_state.get("user_id", "user_a"),
    help="Temporary: this will come from the sign-up screen (Step 0) once the steps are joined.",
).strip()
st.session_state["user_id"] = user_id


def run_import(action):
    try:
        sources, skipped = action()
        all_sources = im.save_sources(user_id, sources)
    except im.ImportFailed as e:
        st.error(e.message)
        return
    st.success(f"Imported {len(sources)} conversation(s). You now have {len(all_sources)} in total.")
    if skipped:
        with st.expander(f"{len(skipped)} conversation(s) skipped"):
            for s in skipped:
                st.markdown(f"- **{s['title']}**: {s['reason']}")


upload_tab, paste_tab, demo_tab = st.tabs(["Upload ChatGPT export", "Paste a chat", "Demo history"])

with upload_tab:
    st.caption(
        "In ChatGPT: Settings → Data controls → Export data. Upload the zip from the email, "
        "or the conversations.json inside it."
    )
    upload = st.file_uploader("ChatGPT export", type=["zip", "json"])
    if upload and st.button("Import file", type="primary"):
        run_import(lambda: im.import_chatgpt_export(upload.getvalue(), upload.name, user_id))

with paste_tab:
    st.caption("Start lines with “User:” and “Assistant:” (or “ChatGPT:” / “Claude:”) to keep who said what.")
    paste_title = st.text_input("Title (optional)")
    pasted = st.text_area("Conversation", height=200)
    if st.button("Import pasted chat", type="primary"):
        run_import(lambda: im.import_pasted_text(pasted, user_id, title=paste_title))

with demo_tab:
    st.caption(
        f"A **synthetic** research history for the demo researcher `{im.DEMO_FIXTURE_OWNER}`. "
        "It is not anyone's real chats."
    )
    if st.button("Load demo history", type="primary", disabled=user_id != im.DEMO_FIXTURE_OWNER):
        run_import(lambda: im.import_demo_history(user_id))

st.divider()
st.subheader("Your imported chats (only you can see these)")
try:
    sources = im.load_sources(user_id)
except im.ImportFailed as e:
    st.error(e.message)
    sources = []

if not sources:
    st.caption("Nothing imported yet.")
for s in sources:
    p = s["provenance"]
    date = (p["created_at"] or "")[:10] or "no date"
    with st.expander(f"{p['title']} · {len(s['messages'])} messages · {date}"):
        st.caption(f"Source `{s['source_id']}` · {s['source_type']}")
        st.text(s["raw_text"])
