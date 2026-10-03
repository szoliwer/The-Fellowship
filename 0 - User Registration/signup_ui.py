"""Step 0 screens: log in, create an account, or try a demo account.

Used by the shared app (app.py at the repo root). `render()` draws the screens and
returns nothing; on success it puts the user's ID in st.session_state["user_id"].
"""

import streamlit as st

import registration as reg


def current_user():
    user_id = st.session_state.get("user_id")
    return reg.get_user(user_id) if user_id else None


def log_out():
    st.session_state.pop("user_id", None)


def _sign_in(user):
    st.session_state["user_id"] = user["user_id"]
    st.rerun()


def render():
    st.title("Join the research network")
    st.info(
        "**Demo build:** accounts are stored only on this laptop. "
        "Refreshing the page logs you out.",
        icon="ℹ️",
    )
    with st.expander("How your information is handled"):
        for question, answer in reg.CONSENT_TEXT.items():
            st.markdown(f"**{question}:** {answer}")

    login_tab, create_tab, demo_tab = st.tabs(["Log in", "Create an account", "Try a demo account"])

    with login_tab:
        with st.form("log_in"):
            email = st.text_input("Email", autocomplete="email")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            try:
                _sign_in(reg.log_in(email, password))
            except reg.RegistrationError as e:
                st.error(e.message)

    with create_tab:
        with st.form("sign_up"):
            pseudonym = st.text_input(
                "Pseudonym (public)",
                placeholder="e.g. neuro_lab_17",
                help="The only name other people see. Don't use your real name.",
            )
            email = st.text_input("Email (private, used to log in)", autocomplete="email")
            password = st.text_input(
                f"Password (at least {reg.MIN_PASSWORD_LENGTH} characters)",
                type="password",
                autocomplete="new-password",
            )
            password2 = st.text_input("Repeat password", type="password", autocomplete="new-password")
            with st.expander("Optional private details (never shown to other users)"):
                name = st.text_input("Name")
                affiliation = st.text_input("Affiliation", placeholder="e.g. university or lab")
            consent = st.checkbox(reg.CONSENT_CHECKBOX)
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            if password != password2:
                st.error("The two passwords don't match.")
            else:
                try:
                    _sign_in(reg.create_account(pseudonym, email, password, consent,
                                                name=name, affiliation=affiliation))
                except reg.RegistrationError as e:
                    st.error(e.message)

    with demo_tab:
        st.caption("These researchers and their histories are synthetic, for the demo. No password needed.")
        demos = reg.demo_users()
        choice = st.selectbox("Demo researcher", demos, format_func=lambda u: u["pseudonym"])
        if st.button("Continue as this demo researcher"):
            _sign_in(choice)
