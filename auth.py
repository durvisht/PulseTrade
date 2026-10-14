"""PulseTrade — authentication via Supabase Auth.

Handles email/password sign-up/sign-in and Google OAuth, plus session
persistence across Streamlit reruns (via st.session_state) and, where
possible, across a hard browser refresh (via a client-side cookie holding
the refresh token).

Honest limitation: Streamlit has no first-party server-side session/cookie
API. Cross-refresh persistence here uses a JS-set cookie (not httponly)
via a small embedded component. This is a reasonable tradeoff for a
student project, not bank-grade session security — a stolen cookie could
be replayed. Do not reuse this pattern for anything handling sensitive
financial actions.
"""

from __future__ import annotations

import os
import secrets
import time

import streamlit as st
from datetime import date
from urllib.parse import urlencode

from supabase import Client, create_client
from supabase_auth.helpers import generate_pkce_challenge, generate_pkce_verifier

COOKIE_NAME = "pulsetrade_refresh_token"


def _secret(name: str) -> str | None:
    """Config from .streamlit/secrets.toml locally, or the environment when
    hosted (Render, Railway, Fly and friends all inject env vars)."""
    try:
        val = st.secrets[name]
        if val:
            return str(val)
    except Exception:
        pass
    val = os.environ.get(name)
    return val if val else None


def get_client() -> Client | None:
    """One Supabase client per browser session.

    Deliberately NOT @st.cache_resource: a cached client is shared by every
    visitor to the process, and since the client carries the signed-in user's
    token, whoever logged in last would own all database reads and writes.
    Per-session clients keep each user's token (and so each user's
    row-level-security identity) to themselves.
    """
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    client = st.session_state.get("_supabase_client")
    if client is None:
        client = create_client(url, key)
        st.session_state["_supabase_client"] = client
    return client


def is_configured() -> bool:
    return get_client() is not None


def _friendly(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "invalid login credentials" in low:
        return "That email and password don't match an account."
    if "email not confirmed" in low:
        return "Confirm your email first — check your inbox for the link."
    if "already registered" in low or "already been registered" in low:
        return "An account with that email already exists. Try logging in."
    if "rate limit" in low:
        return "Too many attempts. Wait a minute and try again."
    return msg


def _store_session(session) -> None:
    meta = session.user.user_metadata or {}
    st.session_state["auth_user"] = {
        "id": session.user.id,
        "email": session.user.email,
        "name": meta.get("full_name") or meta.get("name"),
        "date_of_birth": meta.get("date_of_birth"),
    }
    st.session_state["auth_access_token"] = session.access_token
    st.session_state["auth_refresh_token"] = session.refresh_token


def age_on(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def sign_up(email: str, password: str, date_of_birth: date) -> tuple[bool, str]:
    client = get_client()
    if client is None:
        return False, "Auth is not configured (missing Supabase credentials)."
    try:
        # Date of birth lives in the user's auth metadata — no extra table.
        # Age isn't stored: it's derived, so it can never go stale or disagree.
        res = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"date_of_birth": date_of_birth.isoformat()}},
        })
        if res.session:
            _store_session(res.session)
            return True, "Account created."
        return True, "Account created — check your email for a confirmation link, then log in."
    except Exception as exc:
        return False, _friendly(exc)


def sign_in(email: str, password: str) -> tuple[bool, str]:
    client = get_client()
    if client is None:
        return False, "Auth is not configured (missing Supabase credentials)."
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.session:
            _store_session(res.session)
            return True, "Signed in."
        return False, "Sign-in failed."
    except Exception as exc:
        return False, _friendly(exc)


# --------------------------------------------------------------------------
# Google sign-in (OAuth with PKCE)
# --------------------------------------------------------------------------
# Google sends the user back to  <app>/?code=...&pt_flow=...  — a normal query
# string the server can read, so no browser-side script is involved. (An
# earlier version received tokens in the URL #fragment and relied on an
# embedded script to redirect the page; Streamlit's iframe sandbox forbids
# that redirect, so the login silently never completed.)
#
# PKCE needs the verifier from the *start* of the login to finish it, but
# the redirect arrives in a brand-new Streamlit session. So pending
# verifiers live in a process-wide store, keyed by a random flow id that
# rides along in the redirect URL.

_FLOW_TTL_SECONDS = 15 * 60


@st.cache_resource
def _pending_flows() -> dict:
    return {}


def _prune_flows(flows: dict) -> None:
    cutoff = time.time() - _FLOW_TTL_SECONDS
    for fid in [f for f, (_, ts) in flows.items() if ts < cutoff]:
        flows.pop(fid, None)


def get_google_oauth_url(redirect_to: str) -> str | None:
    """Build the Google sign-in URL. One flow per browser session, so page
    reruns don't mint a new verifier each time."""
    url = _secret("SUPABASE_URL")
    if not url:
        return None

    flows = _pending_flows()
    _prune_flows(flows)
    fid = st.session_state.get("oauth_flow_id")
    if not fid or fid not in flows:
        fid = secrets.token_urlsafe(16)
        flows[fid] = (generate_pkce_verifier(), time.time())
        st.session_state["oauth_flow_id"] = fid
    verifier, _ = flows[fid]

    back = f"{redirect_to.rstrip('/')}/?{urlencode({'pt_flow': fid})}"
    query = urlencode({
        "provider": "google",
        "redirect_to": back,
        "code_challenge": generate_pkce_challenge(verifier),
        "code_challenge_method": "s256",
    })
    return f"{url.rstrip('/')}/auth/v1/authorize?{query}"


def complete_oauth_from_query_params() -> tuple[bool, str | None]:
    """If this page load is Google's redirect back, finish the login.
    Returns (signed_in, error_message)."""
    params = st.query_params
    if "error" in params or "error_description" in params:
        msg = params.get("error_description") or params.get("error")
        st.query_params.clear()
        return False, f"Google sign-in didn't complete: {msg}"

    code = params.get("code")
    if not code:
        return False, None

    client = get_client()
    if client is None:
        return False, None

    flows = _pending_flows()
    fid = params.get("pt_flow")
    candidates = []
    if fid and fid in flows:
        candidates.append(fid)
    else:
        # If Supabase fell back to the bare Site URL (dropping pt_flow), try
        # the most recent pending flows instead — correct for one user,
        # and a code can only be redeemed once anyway.
        candidates = sorted(flows, key=lambda f: flows[f][1], reverse=True)[:3]

    st.query_params.clear()
    for f in candidates:
        verifier, _ = flows[f]
        try:
            res = client.auth.exchange_code_for_session(
                {"auth_code": code, "code_verifier": verifier}
            )
        except Exception:
            continue
        flows.pop(f, None)
        if res.session:
            _store_session(res.session)
            return True, None
    return False, "Google sign-in expired or was already used. Please try again."


def try_restore_session_from_refresh_token(refresh_token: str) -> bool:
    """Attempt to restore a session using a previously-issued refresh token
    (used for cross-refresh persistence via the browser cookie)."""
    client = get_client()
    if client is None or not refresh_token:
        return False
    try:
        res = client.auth.refresh_session(refresh_token)
        if res.session:
            _store_session(res.session)
            return True
    except Exception:
        pass
    return False


def sign_out() -> None:
    client = get_client()
    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass
    for key in ("auth_user", "auth_access_token", "auth_refresh_token",
                "_supabase_client"):
        st.session_state.pop(key, None)


def is_logged_in() -> bool:
    return st.session_state.get("auth_user") is not None


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def current_user_id() -> str | None:
    user = current_user()
    return user["id"] if user else None
