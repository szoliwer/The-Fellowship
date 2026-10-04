"""Step 1 screen: upload or paste chats, see upload history and imported conversations.

Used by the shared app (app.py at the repo root) after the user has logged in.
"""

import streamlit as st

import importer as im
from pipeline import brand  # shared look (labels, intro text, plurals)


def _show_result(name, result):
    n, skipped = len(result["sources"]), result["skipped"]
    st.success(f"**{name}**: imported {brand.plural(n, 'conversation')}.")
    if skipped:
        with st.expander(f"{brand.plural(len(skipped), 'item')} skipped in {name}"):
            for s in skipped:
                st.markdown(f"- **{s['title']}**: {s['reason']}")


def _ask_removal(source_ids):
    st.session_state["pending_removal"] = list(source_ids)


def _confirm_removal(user_id, sources, on_removed):
    """Ask once before deleting; nothing is removed until the owner confirms."""
    pending = st.session_state.get("pending_removal")
    titles = {s["source_id"]: s["provenance"]["title"] for s in sources}
    ids = [i for i in pending or [] if i in titles]
    if not ids:
        st.session_state.pop("pending_removal", None)
        return
    what = f"“{titles[ids[0]]}”" if len(ids) == 1 else f"all {len(ids)} imported chats"
    with st.container(border=True):
        st.warning(f"Remove {what}? It is deleted, together with its screening result. "
                   "This can't be undone.", icon=":material/delete:")
        yes, no = st.columns(2)
        if yes.button("Yes, remove", type="primary", use_container_width=True):
            result = im.remove_sources(user_id, ids)
            if on_removed:
                on_removed(user_id)
            st.session_state.pop("pending_removal", None)
            st.session_state["removal_result"] = result
            st.rerun()
        if no.button("Cancel", use_container_width=True):
            st.session_state.pop("pending_removal", None)
            st.rerun()


def _removal_message():
    result = st.session_state.pop("removal_result", None)
    if not result:
        return
    text = f"Removed {brand.plural(result['removed'], 'chat')}."
    if result["files_deleted"]:
        text += (f" Also deleted {brand.plural(result['files_deleted'], 'original uploaded file')} "
                 "that held no other chats.")
    st.success(text)
    for name in result["files_kept"]:
        st.info(f"The original file **{name}** is still stored, because other chats from it are still "
                "imported. Remove those too to delete the file.")
    st.caption("If you already found ideas from these chats, find them again on the Ideas page so the removed "
               "chats aren't used, and review them on the Review page.")


def render(user, on_removed=None):
    """on_removed(user_id) is called after chats are removed, so later steps can forget them."""
    user_id = user["user_id"]
    st.title("Import your research chats")
    brand.lead("Bring in the conversations you want to be matched on. Only you can see them.")

    is_demo = user_id in im.DEMO_FIXTURES
    tabs = st.tabs(["Upload files", "Paste a chat"] + (["Demo history"] if is_demo else []))
    upload_tab, paste_tab = tabs[:2]

    with upload_tab:
        st.markdown(
            "- **ChatGPT export:** Settings → Data controls → Export data. Upload the .zip from the email.\n"
            "- **Claude export:** Settings → Privacy → Export data. Upload the .zip from the email.\n"
            "- **Notes or saved chats:** .md or .txt files, or a .zip of them."
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

    if is_demo:  # only demo researchers have a synthetic history to load
        with tabs[2]:
            st.caption("A **synthetic** research history written for this demo researcher. "
                       "It is not anyone's real chats.")
            if st.button("Load demo history", type="primary"):
                try:
                    _show_result("Demo history", im.import_demo(user_id))
                except im.ImportFailed as e:
                    st.error(e.message)

    st.divider()
    sources = im.load_sources(user_id)
    st.subheader(f"Your chats ({len(sources)})")
    _removal_message()
    _confirm_removal(user_id, sources, on_removed)
    if not sources:
        st.caption("Nothing imported yet. Upload a file or paste a chat above.")
    for s in reversed(sources):
        p = s["provenance"]
        date = (p["created_at"] or p["imported_at"] or "")[:10]
        with st.expander(f"{p['title']} · {brand.plural(len(s['messages']), 'message')} · {date}"):
            st.button("Remove this chat", key=f"remove_{s['source_id']}", icon=":material/delete:",
                      on_click=_ask_removal, args=([s["source_id"]],))
            st.text(s["raw_text"])
    if len(sources) > 1:
        st.button("Remove all my chats", icon=":material/delete_sweep:",
                  on_click=_ask_removal, args=([s["source_id"] for s in sources],))

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
