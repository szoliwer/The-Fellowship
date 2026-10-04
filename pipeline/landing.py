"""The page people see before signing in, laid out like the Lovable website
(hero + example match, how it works, privacy, call to action, footer). The forms are Step 0's
own (signup_ui), opened in pop-up windows as on the Lovable site. Presentation only."""

import streamlit as st

import signup_ui  # Step 0
from pipeline import brand


@st.dialog("Create your account", width="medium")
def _create_account():
    brand.eyebrow("Join The Fellowship")
    st.html('<div class="fs-section"><h2 style="font-size:2.1rem;margin:0">Start with the essentials.</h2></div>')
    st.caption("Your username is public. Your email and password stay private.")
    signup_ui.create_account_form()


@st.dialog("Log in", width="small")
def _log_in():
    signup_ui.login_form()


@st.dialog("Try a demo", width="small")
def _try_demo():
    signup_ui.demo_picker()


def _gap(rem=4):
    st.html(f'<div style="height:{rem}rem"></div>')


def render():
    brand.page_style(wide=True)

    left, right = st.columns([1.05, 0.95], gap="large", vertical_alignment="center")
    with left:
        st.html(brand.hero_html())
        with st.container(horizontal=True, gap="small"):
            if st.button("Create your account", key="hero_join", type="primary",
                         icon=":material/arrow_forward:", icon_position="right"):
                _create_account()
            if st.button("Log in", key="hero_login"):
                _log_in()
            if st.button("Try a demo", key="hero_demo", type="tertiary"):
                _try_demo()
        st.caption("Username, email and password. No biography required.")
    with right:
        st.html(brand.example_card_html())

    _gap(5)
    head, rows = brand.how_it_works_html()
    left, right = st.columns([0.8, 1.2], gap="large")
    left.html(head)
    right.html(rows)

    _gap(5)
    head, items = brand.privacy_html()
    left, right = st.columns(2, gap="large")
    left.html(head)
    with right:
        st.html(items)
        signup_ui.privacy_details()

    _gap(5)
    with st.container(key="fs_cta"):
        st.html('<p class="fs-eyebrow">Your next connection is thinking now</p>'
                '<div class="fs-section"><h2>Join the people behind the ideas.</h2></div>')
        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.button("Create your account", key="cta_join", icon=":material/arrow_forward:",
                         icon_position="right"):
                _create_account()

    _gap(3)
    st.html(brand.footer_html())
    st.caption("Prototype: accounts are stored on this computer only, and refreshing the page signs you out.")
