"""PulseTrade — login: email/password + Google Sign-In (Supabase Auth)."""

from __future__ import annotations

import html
import re
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

import auth
import theme as T

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_SCROLL_TOP_JS = """
<script>
try { if (window.frameElement) window.frameElement.style.height = '0px'; } catch (e) {}
// Start at the top, not wherever the landing page was scrolled to.
try {
  var main = window.parent.document.querySelector('section.stMain');
  if (main) main.scrollTop = 0;
} catch (e) {}
</script>
"""


MIN_AGE = 13  # COPPA floor for collecting personal data; raise to 18 if you want adults only.

_GOOGLE_G = (
    "<svg width='18' height='18' viewBox='0 0 48 48'>"
    "<path fill='#FFC107' d='M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z'/>"
    "<path fill='#FF3D00' d='M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z'/>"
    "<path fill='#4CAF50' d='M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z'/>"
    "<path fill='#1976D2' d='M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z'/>"
    "</svg>"
)


def _app_base_url() -> str:
    """The public origin Google redirects back to. Must exactly match an entry
    in Supabase's redirect allow-list."""
    return auth._secret("APP_BASE_URL") or "http://localhost:8501"


def _heading(title: str, sub: str) -> None:
    st.markdown(
        f"<div style='text-align:center;margin:4px 0 16px'>"
        f"<div style='font-size:27px;font-weight:600;letter-spacing:-0.03em;color:{T.TEXT}'>{title}</div>"
        f"<div style='font-size:14px;color:{T.TEXT_3};margin-top:7px'>{sub}</div></div>",
        unsafe_allow_html=True,
    )


def _go_to_app() -> None:
    st.session_state["page"] = "app"
    st.session_state["view"] = "dashboard"
    st.rerun()


def _render_login_form() -> None:
    _heading("Welcome back", "Log in with your email and password.")
    with st.form("login_form", border=False):
        email = st.text_input("Email", placeholder="you@example.com", key="li_email")
        password = st.text_input("Password", type="password", placeholder="Your password", key="li_pw")
        submitted = st.form_submit_button("Log in", type="primary", width="stretch",
                                          icon=":material/login:")
    if submitted:
        if not EMAIL_RE.match(email or ""):
            st.error("Enter a valid email address.")
        elif not password:
            st.error("Enter your password.")
        else:
            with st.spinner("Logging in…"):
                ok, msg = auth.sign_in(email.strip(), password)
            if ok and auth.is_logged_in():
                _go_to_app()
            else:
                st.error(msg)


def _render_signup_form() -> None:
    _heading("Create your account", "Free, and takes about a minute.")

    # Not wrapped in st.form on purpose: the age field updates live as the
    # date of birth changes, which a form would defer until submit.
    email = st.text_input("Email", placeholder="you@example.com", key="su_email")
    c1, c2 = st.columns(2)
    with c1:
        password = st.text_input("Password", type="password",
                                 placeholder="8+ characters", key="su_pw")
    with c2:
        confirm = st.text_input("Confirm password", type="password",
                                placeholder="Repeat it", key="su_pw2")

    today = date.today()
    d1, d2 = st.columns([2, 1])
    with d1:
        dob = st.date_input(
            "Date of birth", value=None, key="su_dob",
            min_value=date(today.year - 120, 1, 1), max_value=today,
            format="MM/DD/YYYY",
        )
    age = auth.age_on(dob, today) if dob else None
    with d2:
        st.text_input("Age", value="" if age is None else str(age),
                      placeholder="Auto", disabled=True, key=f"su_age_{age}",
                      help="Calculated from your date of birth.")

    if st.button("Create account", type="primary", width="stretch",
                 icon=":material/person_add:", key="su_submit"):
        problems = []
        if not EMAIL_RE.match(email or ""):
            problems.append("Enter a valid email address.")
        if len(password or "") < 8:
            problems.append("Password must be at least 8 characters.")
        elif password != confirm:
            problems.append("Passwords don't match.")
        if dob is None:
            problems.append("Enter your date of birth.")
        elif age < MIN_AGE:
            problems.append(f"You must be at least {MIN_AGE} to create an account.")

        if problems:
            for p in problems:
                st.error(p)
            return

        with st.spinner("Creating your account…"):
            ok, msg = auth.sign_up(email.strip(), password, dob)
        if ok and auth.is_logged_in():
            _go_to_app()
        elif ok:
            st.success(msg)
        else:
            st.error(msg)


def _render_google_button() -> None:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:14px;margin:18px 0 14px'>"
        f"<div style='flex:1;height:1px;background:{T.BORDER}'></div>"
        f"<span style='font-size:11px;font-weight:600;letter-spacing:0.1em;"
        f"text-transform:uppercase;color:{T.TEXT_3}'>or</span>"
        f"<div style='flex:1;height:1px;background:{T.BORDER}'></div></div>",
        unsafe_allow_html=True,
    )
    url = auth.get_google_oauth_url(redirect_to=_app_base_url())
    if not url:
        st.caption("Google sign-in isn't available right now.")
        return
    # A plain same-tab link: Google redirects back to this window, and app.py
    # finishes the login. st.link_button would open a new tab instead.
    st.markdown(
        f"<a class='pt-google' href='{html.escape(url, quote=True)}' target='_self'>"
        f"{_GOOGLE_G}<span>Continue with Google</span></a>",
        unsafe_allow_html=True,
    )


def render_login_page() -> None:
    components.html(_SCROLL_TOP_JS, height=0)

    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.markdown(
            f"<div style='display:flex;justify-content:center;margin:4px 0 20px'>"
            f"{T.logo_lockup_html(26)}</div>",
            unsafe_allow_html=True,
        )

        if not auth.is_configured():
            st.error(
                "Auth isn't configured yet — add `SUPABASE_URL` and "
                "`SUPABASE_ANON_KEY` to `.streamlit/secrets.toml`.",
                icon="🔒",
            )
            return

        err = st.session_state.pop("login_error", None)
        if err:
            st.error(err)

        mode = st.segmented_control(
            "mode", ["Log in", "Sign up"], default="Log in",
            key="auth_mode", label_visibility="collapsed", width="stretch",
        ) or "Log in"

        if mode == "Log in":
            _render_login_form()
        else:
            _render_signup_form()

        _render_google_button()
