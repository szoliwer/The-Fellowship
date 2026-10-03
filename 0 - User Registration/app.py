"""Step 0 sign-up screen. Run from the repo root:

    .venv/bin/streamlit run "0 - User Registration/app.py"
"""

import streamlit as st

import registration as reg

st.set_page_config(page_title="Sign up", page_icon="🔬")

st.title("Join the research network")
st.info(
    "**Demo:** there is no real login. Accounts are stored only on this laptop.",
    icon="ℹ️",
)

with st.expander("How your information is handled", expanded=True):
    for question, answer in reg.CONSENT_TEXT.items():
        st.markdown(f"**{question}:** {answer}")


def show_signed_in(user):
    st.success(f"Signed in as **{user['pseudonym']}**")
    label = "Synthetic demo account" if user["is_demo_account"] else "Your account"
    st.caption(f"{label} · user ID `{user['user_id']}` · intent: {user['connection_intent']}")
    st.markdown("**What other people can see:**")
    st.json(reg.public_view(user))
    if st.button("Sign out"):
        del st.session_state["user_id"]
        st.rerun()


user_id = st.session_state.get("user_id")
if user_id and (user := reg.get_user(user_id)):
    show_signed_in(user)
    st.stop()

demo_tab, create_tab = st.tabs(["Use a demo account", "Create an account"])

with demo_tab:
    st.caption("These researchers and their histories are synthetic, for the demo.")
    demos = reg.demo_users()
    choice = st.selectbox(
        "Demo researcher",
        demos,
        format_func=lambda u: f"{u['pseudonym']} ({u['user_id']})",
    )
    if st.button("Continue as this demo researcher", type="primary"):
        st.session_state["user_id"] = choice["user_id"]
        st.rerun()

with create_tab:
    with st.form("sign_up"):
        pseudonym = st.text_input(
            "Pseudonym",
            placeholder="e.g. neuro_lab_17",
            help="This is the only name other people see. Don't use your real name.",
        )
        with st.expander("Private details (optional, never shown to other users)"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            affiliation = st.text_input("Affiliation", placeholder="e.g. university or lab")
        consent = st.checkbox(reg.CONSENT_CHECKBOX)
        submitted = st.form_submit_button("Create account", type="primary")

    if submitted:
        try:
            user = reg.create_user(pseudonym, consent, name=name, email=email, affiliation=affiliation)
        except reg.RegistrationError as e:
            st.error(e.message)
        else:
            st.session_state["user_id"] = user["user_id"]
            st.rerun()
