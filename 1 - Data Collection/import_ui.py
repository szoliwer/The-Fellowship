"""Step 1 screen: upload or paste chats, see upload history and imported conversations.

Used by the shared app (app.py at the repo root) after the user has logged in.
"""

import streamlit as st

import importer as im


def _show_result(name, result):
    n, skipped = len(result["sources"]), result["skipped"]
    st.success(f"**{name}**: imported {n} conversation{'s' if n != 1 else ''}.")
    if skipped:
        with st.expander(f"{len(skipped)} item(s) skipped in {name}"):
            for s in skipped:
                st.markdown(f"- **{s['title']}**: {s['reason']}")


def render(user):
    user_id = user["user_id"]
    st.title("Import your research chats")
    st.info(
        "Importing is **private**. Your files are stored only on this laptop and nobody else sees "
        "them. Next, personal or sensitive conversations are held back, and nothing is shared "
        "until you approve specific ideas later.",
        icon="🔒",
    )

    upload_tab, paste_tab, demo_tab = st.tabs(["Upload files", "Paste a chat", "Demo history"])

    with upload_tab:
        st.markdown(
            "- **ChatGPT export:** Settings → Data controls → Export data. Upload the .zip from the email.\n"
            "- **Claude export:** Settings → Privacy → Export data. Upload the .zip from the email.\n"
            "- **Notes or saved chats:** .md or .txt files, or a .zip of them. Lines starting "
            "`User:` / `Assistant:` (also `You said:`, `ChatGPT:`, `## Claude`, …) keep who said what."
        )
        files = st.file_uploader("Choose files", type=im.ACCEPTED_EXTENSIONS, accept_multiple_files=True)
        if files and st.button("Import files", type="primary"):
            for f in files:
                try:
                    _show_result(f.name, im.import_file(user_id, f.getvalue(), f.name))
                except im.ImportFailed as e:
                    st.error(f"**{f.name}**: {e.message}")

    with paste_tab:
        with st.form("paste", clear_on_submit=True):
            title = st.text_input("Title (optional)")
            text = st.text_area("Conversation or notes", height=220,
                                placeholder="User: …\nAssistant: …")
            submitted = st.form_submit_button("Import pasted text", type="primary")
        if submitted:
            try:
                _show_result(title or "Pasted text", im.import_paste(user_id, text, title=title))
            except im.ImportFailed as e:
                st.error(e.message)

    with demo_tab:
        if user_id in im.DEMO_FIXTURES:
            st.caption("A **synthetic** research history written for this demo researcher. "
                       "It is not anyone's real chats.")
            if st.button("Load demo history", type="primary"):
                try:
                    _show_result("Demo history", im.import_demo(user_id))
                except im.ImportFailed as e:
                    st.error(e.message)
        else:
            st.caption("Synthetic demo histories are only available to the demo researchers.")

    st.divider()
    sources = im.load_sources(user_id)
    st.subheader(f"Your imported chats ({len(sources)}), only you can see these")
    if not sources:
        st.caption("Nothing imported yet.")
    for s in reversed(sources):
        p = s["provenance"]
        date = (p["created_at"] or p["imported_at"] or "")[:10]
        with st.expander(f"{p['title']} · {len(s['messages'])} messages · {date}"):
            st.caption(f"Source `{s['source_id']}` · {s['source_type']}")
            st.text(s["raw_text"])

    log = im.load_upload_log(user_id)
    if log:
        with st.expander(f"Upload history ({len(log)})"):
            st.dataframe(
                [{
                    "When": e["uploaded_at"].replace("T", " ").rstrip("Z"),
                    "What": e["filename"],
                    "Result": (f"{e['imported_count']} imported" if e["status"] == "imported"
                               else f"Failed: {e['error']['message']}"),
                    "Skipped": len(e["skipped"]),
                } for e in reversed(log)],
                hide_index=True,
            )
