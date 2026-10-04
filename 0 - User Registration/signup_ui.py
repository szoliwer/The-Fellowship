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
    """Forget everything about this browser session (who is logged in, page state)."""
    st.session_state.clear()


def _sign_in(user):
    st.session_state["user_id"] = user["user_id"]
    st.session_state["just_signed_in"] = True  # lets the app start the first page at the top
    st.rerun()


def login_form():
    """Email + password. Signs the user in on success."""
    with st.form("log_in"):
        email = st.text_input("Email", autocomplete="email")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
    if submitted:
        try:
            _sign_in(reg.log_in(email, password))
        except reg.RegistrationError as e:
            st.error(e.message)


def create_account_form():
    """Username (public), email + password (private), optional private details, consent."""
    with st.form("sign_up"):
        pseudonym = st.text_input(
            "Username (public)", placeholder="e.g. neuro_lab_17",
            help="The only name other people see. 3–30 lowercase letters, numbers or underscores. "
                 "Don't use your real name.",
        )
        email = st.text_input("Email (private, used to log in)", autocomplete="email")
        password = st.text_input(f"Password (at least {reg.MIN_PASSWORD_LENGTH} characters)",
                                 type="password", autocomplete="new-password")
        password2 = st.text_input("Repeat password", type="password", autocomplete="new-password")
        with st.expander("Optional private details (never shown to other users)"):
            name = st.text_input("Name")
            affiliation = st.text_input("Affiliation", placeholder="e.g. university or lab")
        consent = st.checkbox(reg.CONSENT_CHECKBOX)
        submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
    if submitted:
        if password != password2:
            st.error("The two passwords don't match.")
        else:
            try:
                _sign_in(reg.create_account(pseudonym, email, password, consent,
                                            name=name, affiliation=affiliation))
            except reg.RegistrationError as e:
                st.error(e.message)


def demo_picker():
    """Sign in as one of the synthetic demo researchers (no password)."""
    st.caption("These researchers and their histories are synthetic, for the demo. No password needed.")
    demos = reg.demo_users()
    choice = st.selectbox("Demo researcher", demos, format_func=lambda u: u["pseudonym"])
    if st.button("Continue as this demo researcher", type="primary", use_container_width=True):
        _sign_in(choice)


def privacy_details():
    with st.expander("How your information is handled"):
        for question, answer in reg.CONSENT_TEXT.items():
            st.markdown(f"**{question}:** {answer}")


def render():
    """A plain sign-in screen (log in / create an account / demo). The shared app shows a fuller
    landing page around the same forms."""
    st.title("Join the research network")
    login_tab, create_tab, demo_tab = st.tabs(["Log in", "Create an account", "Try a demo"])
    with login_tab:
        login_form()
    with create_tab:
        create_account_form()
    with demo_tab:
        demo_picker()
    privacy_details()


def render_account(user):
    """The account page: who you are, what other people can see, and log out."""
    st.title("Your account")
    with st.container(border=True):
        st.markdown(f"**Username:** {user['pseudonym']}")
        if user["is_demo_account"]:
            st.caption("Synthetic demo account")
        elif user["private"]["email"]:
            st.caption(f"Signed in with {user['private']['email']} (private)")
    st.markdown("**What other people can see about you**")
    st.markdown(f"Your username, **{user['pseudonym']}**, and only the ideas you approve on the Review page. "
                "Never your chats, your email or your name.")
    if st.button("Log out", icon=":material/logout:"):
        log_out()
        st.rerun()
