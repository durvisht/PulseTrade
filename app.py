"""PulseTrade — main Streamlit application.

Router + dashboard. Combines deterministic yfinance analytics with real
Alpha Vantage news sentiment and a Gemini-synthesized 30-day directional
outlook. All visual tokens come from theme.py.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from pathlib import Path

import auth
import stock_data as sd
import theme as T
import watchlist as wl
from gemini_engine import get_full_analysis
from landing import render_landing_page
from login import render_login_page
from movers import MOVERS_CSS, render_movers_page
from sentiment_panel import PANEL_CSS, render_sentiment_panel

# --------------------------------------------------------------------------
# Design system — see theme.py
# --------------------------------------------------------------------------

BLUE = T.ACCENT
BLUE_LIGHT = T.ACCENT
PURPLE = T.ACCENT_DIM
MAGENTA = T.ACCENT
MAGENTA_LIGHT = T.ACCENT
GREEN = T.BULLISH
RED = T.BEARISH
TEXT_PRIMARY = T.TEXT
TEXT_SECONDARY = T.TEXT_2
CHART_TRANSPARENT = "rgba(0,0,0,0)"

_FAVICON = Path(__file__).parent / "assets" / "icon-256.png"

st.set_page_config(
    page_title="PulseTrade",
    page_icon=str(_FAVICON) if _FAVICON.exists() else "\u25b2",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(T.streamlit_css(), unsafe_allow_html=True)
st.markdown(f"<style>{PANEL_CSS}{MOVERS_CSS}</style>", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# API key resolution
# --------------------------------------------------------------------------


def _secret(name: str) -> str | None:
    """secrets.toml locally; environment variables when hosted."""
    try:
        val = st.secrets[name]
        if val:
            return str(val)
    except Exception:
        pass
    val = os.environ.get(name)
    return val if val else None


def resolve_api_key() -> str | None:
    return _secret("GEMINI_API_KEY") or st.session_state.get("manual_api_key") or None


def resolve_av_api_key() -> str | None:
    return _secret("ALPHA_VANTAGE_API_KEY") or st.session_state.get("manual_av_api_key") or None


_GEMINI_PRECONFIGURED = _secret("GEMINI_API_KEY") is not None
_AV_PRECONFIGURED = _secret("ALPHA_VANTAGE_API_KEY") is not None

# --------------------------------------------------------------------------
# Ticker universe — 30+ large caps, shown as a searchable scrolling dropdown
# --------------------------------------------------------------------------

TICKER_UNIVERSE = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corp.",
    "GOOGL": "Alphabet Inc. (Class A)",
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms Inc.",
    "AVGO": "Broadcom Inc.",
    "TSLA": "Tesla Inc.",
    "BRK-B": "Berkshire Hathaway Inc.",
    "LLY": "Eli Lilly and Co.",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "UNH": "UnitedHealth Group Inc.",
    "XOM": "Exxon Mobil Corp.",
    "MA": "Mastercard Inc.",
    "COST": "Costco Wholesale Corp.",
    "HD": "Home Depot Inc.",
    "PG": "Procter & Gamble Co.",
    "JNJ": "Johnson & Johnson",
    "ABBV": "AbbVie Inc.",
    "NFLX": "Netflix Inc.",
    "BAC": "Bank of America Corp.",
    "CRM": "Salesforce Inc.",
    "ORCL": "Oracle Corp.",
    "AMD": "Advanced Micro Devices Inc.",
    "KO": "Coca-Cola Co.",
    "PEP": "PepsiCo Inc.",
    "WMT": "Walmart Inc.",
    "DIS": "Walt Disney Co.",
    "ADBE": "Adobe Inc.",
    "MRK": "Merck & Co.",
    "CSCO": "Cisco Systems Inc.",
    "TMO": "Thermo Fisher Scientific Inc.",
    "ACN": "Accenture plc",
    "MCD": "McDonald's Corp.",
    "CVX": "Chevron Corp.",
    "ABT": "Abbott Laboratories",
    "LIN": "Linde plc",
    "INTC": "Intel Corp.",
    "QCOM": "Qualcomm Inc.",
}

# --------------------------------------------------------------------------
# View state — Dashboard vs About, switched via the persistent nav buttons
# --------------------------------------------------------------------------

if "view" not in st.session_state:
    st.session_state["view"] = "dashboard"

# --------------------------------------------------------------------------
# Page state — landing / login / app (post-login dashboard+about)
# --------------------------------------------------------------------------

if "page" not in st.session_state:
    st.session_state["page"] = "landing"

# Google sign-in returns here as ?code=... (see auth.py). It lands in a fresh
# session, which would otherwise start on the landing page — so finish the
# login before routing and send the user straight to the dashboard.
if not auth.is_logged_in():
    _oauth_ok, _oauth_err = auth.complete_oauth_from_query_params()
    if _oauth_ok:
        st.session_state["page"] = "app"
        st.session_state["view"] = "dashboard"
    elif _oauth_err:
        st.session_state["page"] = "login"
        st.session_state["login_error"] = _oauth_err

# Silent cross-refresh session restore: a browser cookie (set on login via
# a small JS snippet) holds the Supabase refresh token. Streamlit has no
# server-side session store, so without this a hard page refresh would log
# the user out even though their data is safe in the database.
if not auth.is_logged_in():
    try:
        _cookie_token = st.context.cookies.get(auth.COOKIE_NAME)
    except Exception:
        _cookie_token = None
    if _cookie_token and auth.try_restore_session_from_refresh_token(_cookie_token):
        st.session_state["page"] = "app"

if auth.is_logged_in() and st.session_state["page"] in ("landing", "login"):
    st.session_state["page"] = "app"

if not auth.is_logged_in() and st.session_state["page"] == "app":
    st.session_state["page"] = "login"


def _persist_login_cookie() -> None:
    """Write the refresh token into a browser cookie so a hard refresh
    doesn't lose the session. Not httponly (JS-set) — acceptable tradeoff
    for a student project, not for anything security-sensitive."""
    token = st.session_state.get("auth_refresh_token")
    if not token:
        return
    components.html(
        f"""<script>
        try {{ if (window.frameElement) window.frameElement.style.height = '0px'; }} catch (e) {{}}
        try {{
            var d = new Date(); d.setTime(d.getTime() + 30*24*60*60*1000);
            window.parent.document.cookie = "{auth.COOKIE_NAME}=" + "{token}" +
                "; path=/; expires=" + d.toUTCString() + "; SameSite=Lax";
        }} catch (e) {{}}
        </script>""",
        height=0,
    )


if auth.is_logged_in():
    _persist_login_cookie()

# --------------------------------------------------------------------------
# Sidebar — Navigation & Input
# --------------------------------------------------------------------------

# Defaults so downstream code has real values even when the sidebar's
# dashboard controls aren't rendered (landing/login pages).
active_ticker = None
time_horizon = "30 Days"
fetch_clicked = False
star_clicked = False

_HORIZONS = {"7D": "7 Days", "30D": "30 Days", "90D": "90 Days", "1Y": "1 Year"}


def _market_status() -> tuple[bool, str]:
    """US regular session, Mon–Fri 9:30–16:00 ET. Exchange holidays aren't
    modelled, so the caption says 'regular hours' rather than claiming more."""
    now = datetime.now(ZoneInfo("America/New_York"))
    mins = now.hour * 60 + now.minute
    is_open = now.weekday() < 5 and 570 <= mins < 960
    return is_open, now.strftime("%a %H:%M ET")


def _side_label(text: str) -> None:
    st.markdown(f"<div class='sb-label'>{text}</div>", unsafe_allow_html=True)


def _nav(label: str, key: str, icon: str, active: bool) -> bool:
    return st.button(
        label, key=f"nav_{key}", icon=icon, width="stretch",
        type="primary" if active else "secondary",
    )


with st.sidebar:
    st.markdown(
        f"<div class='sb-brand'>{T.logo_lockup_html(30, size=1.3)}"
        f"<div class='sb-tag'>Market data &middot; market mood</div></div>",
        unsafe_allow_html=True,
    )

    logged_in = auth.is_logged_in()
    in_app = st.session_state["page"] == "app"
    view = st.session_state["view"]

    _side_label("Navigate")
    if logged_in:
        if _nav("Dashboard", "dash", ":material/space_dashboard:", in_app and view == "dashboard"):
            st.session_state["page"] = "app"
            st.session_state["view"] = "dashboard"
            st.rerun()
        if _nav("Weekly movers", "movers", ":material/trending_up:", in_app and view == "movers"):
            st.session_state["page"] = "app"
            st.session_state["view"] = "movers"
            st.rerun()
        if _nav("About PulseTrade", "about", ":material/info:", in_app and view == "about"):
            st.session_state["page"] = "app"
            st.session_state["view"] = "about"
            st.rerun()
    else:
        if _nav("Home", "home", ":material/home:", st.session_state["page"] == "landing"):
            st.session_state["page"] = "landing"
            st.rerun()
        if _nav("Sign in", "signin", ":material/login:", st.session_state["page"] == "login"):
            st.session_state["page"] = "login"
            st.rerun()

    is_open, clock = _market_status()
    dot = T.BULLISH if is_open else T.TEXT_3
    _side_label("Market")
    st.markdown(
        f"<div class='sb-card'>"
        f"<div style='display:flex;align-items:center;justify-content:space-between'>"
        f"<span style='display:flex;align-items:center;gap:9px;font-size:14px;font-weight:600;color:{T.TEXT}'>"
        f"<span class='sb-dot' style='background:{dot};box-shadow:0 0 10px {dot}'></span>"
        f"US markets {'open' if is_open else 'closed'}</span>"
        f"<span style='font-size:11.5px;color:{T.TEXT_3}'>{clock}</span></div>"
        f"<div style='font-size:11.5px;color:{T.TEXT_3};margin-top:7px'>NYSE &middot; Nasdaq regular hours</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if in_app:
        # A jump (from the watchlist or the weekly movers) writes straight into
        # the ticker widgets' own state, so the choice sticks across reruns,
        # then flags an immediate analysis.
        jump = st.session_state.pop("pending_jump", None)
        if jump:
            if jump in TICKER_UNIVERSE:
                st.session_state["ticker_select"] = jump
                st.session_state["ticker_search"] = ""
            else:
                st.session_state["ticker_search"] = jump
            st.session_state["view"] = "dashboard"
            st.session_state["auto_analyze"] = True

        _side_label("Analyze")
        selected_key = st.selectbox(
            "Ticker",
            options=list(TICKER_UNIVERSE.keys()),
            format_func=lambda k: f"{k}  ·  {TICKER_UNIVERSE[k]}",
            label_visibility="collapsed", key="ticker_select",
        )
        custom_ticker = st.text_input(
            "Search", placeholder="Or search any ticker",
            icon=":material/search:", label_visibility="collapsed", key="ticker_search",
        )
        horizon_key = st.segmented_control(
            "Horizon", list(_HORIZONS), default="30D",
            key="horizon_seg", label_visibility="collapsed", width="stretch",
        ) or "30D"
        time_horizon = _HORIZONS[horizon_key]

        active_ticker = custom_ticker.strip().upper() if custom_ticker.strip() else selected_key

        fetch_clicked = st.button(
            f"Analyze {active_ticker}", key="analyze_btn", type="primary",
            icon=":material/insights:", width="stretch",
        ) or st.session_state.pop("auto_analyze", False)

        user_id = auth.current_user_id()
        if user_id:
            is_starred = wl.is_watchlisted(user_id, active_ticker)
            star_clicked = st.button(
                "Saved to watchlist" if is_starred else "Add to watchlist",
                key="star_toggle", width="stretch",
                icon=":material/star:" if is_starred else ":material/star_outline:",
            )

        # Only show raw API key fields when a key is genuinely missing — keeps
        # the sidebar clean once secrets.toml is configured.
        if not _GEMINI_PRECONFIGURED or not _AV_PRECONFIGURED:
            with st.expander("API setup required", icon=":material/key:", expanded=True):
                if not _GEMINI_PRECONFIGURED:
                    st.text_input("Gemini key", type="password", key="manual_api_key",
                                  placeholder="Gemini API key", label_visibility="collapsed")
                if not _AV_PRECONFIGURED:
                    st.text_input("News data key", type="password", key="manual_av_api_key",
                                  placeholder="Alpha Vantage API key", label_visibility="collapsed")
    else:
        _side_label("What you get")
        feats = [
            ("chart", T.ACCENT, "Live prices", "Moving averages and volatility"),
            ("pulse", T.BULLISH, "Sentiment", "Scored from cited news"),
            ("gauge", T.CYAN, "30-day outlook", "Direction and drivers"),
        ]
        rows = "".join(
            f"<div class='sb-feat'><span class='sb-ico' style='color:{c}'>{T.icon(i, 16, c)}</span>"
            f"<span><b>{t}</b><br><span>{d}</span></span></div>"
            for i, c, t, d in feats
        )
        st.markdown(f"<div class='sb-card' style='padding:6px 14px'>{rows}</div>",
                    unsafe_allow_html=True)

    st.markdown("<div class='sb-spacer'></div>", unsafe_allow_html=True)

    if logged_in:
        user = auth.current_user()
        email = user["email"]
        initial = (email[:1] or "?").upper()
        st.markdown(
            f"<div class='sb-card sb-account'>"
            f"<span class='sb-avatar'>{initial}</span>"
            f"<span style='min-width:0'><b>{email.split('@')[0]}</b>"
            f"<span class='sb-email'>{email}</span></span></div>",
            unsafe_allow_html=True,
        )
        if st.button("Log out", key="logout_btn", icon=":material/logout:",
                     type="tertiary", width="stretch"):
            auth.sign_out()
            st.session_state["page"] = "landing"
            st.rerun()

    st.markdown(
        "<div class='sb-foot'>Data from <span>yfinance</span><span>Alpha Vantage</span>"
        "<span>Gemini</span></div>",
        unsafe_allow_html=True,
    )

api_key = resolve_api_key()
av_api_key = resolve_av_api_key()

if st.session_state["page"] == "app" and active_ticker and star_clicked:
    user_id = auth.current_user_id()
    if user_id:
        if wl.is_watchlisted(user_id, active_ticker):
            wl.remove_from_watchlist(user_id, active_ticker)
        else:
            wl.add_to_watchlist(user_id, active_ticker)
        st.rerun()

# --------------------------------------------------------------------------
# Cached end-to-end fetch — repeated Analyze clicks on the same ticker
# within the TTL return instantly instead of re-hitting Gemini/Alpha
# Vantage, which also conserves free-tier quota.
# --------------------------------------------------------------------------


@st.cache_data(ttl=600, show_spinner=False)
def _run_full_pipeline(ticker: str, horizon: str, gemini_key: str, av_key: str):
    technical_data = sd.get_technical_summary(ticker, horizon)
    history_df = sd.get_stock_history(ticker, horizon)
    news_data = sd.get_news_sentiment_raw(ticker, av_key)
    ai_data = get_full_analysis(ticker, technical_data, news_data, gemini_key)
    return technical_data, history_df, news_data, ai_data


# --------------------------------------------------------------------------
# Session state — cache analysis so tab switches never re-fetch
# --------------------------------------------------------------------------

if "analysis_cache" not in st.session_state:
    st.session_state["analysis_cache"] = {}

cache_key = f"{active_ticker}_{time_horizon}"

if fetch_clicked:
    st.session_state["view"] = "dashboard"
    if not api_key or not av_api_key:
        st.session_state["analysis_error"] = "missing_key"
    else:
        st.session_state.pop("analysis_error", None)
        try:
            with st.status(f"Analyzing {active_ticker}...", expanded=False) as status:
                status.write("Fetching price history and computing technicals...")
                status.write("Fetching live news coverage...")
                status.write("Synthesizing sentiment narrative and 30-day outlook...")
                technical_data, history_df, news_data, ai_data = _run_full_pipeline(
                    active_ticker, time_horizon, api_key, av_api_key
                )
                status.update(label="Analysis complete", state="complete")
            st.session_state["analysis_cache"][cache_key] = {
                "technical": technical_data,
                "history": history_df,
                "news": news_data,
                "ai": ai_data,
                "fetched_at": datetime.now(timezone.utc),
            }
        except Exception as exc:  # surfaced to user, not silently swallowed
            st.session_state["analysis_error"] = str(exc)


def _render_watchlist_panel() -> None:
    st.markdown("<div class='pt-h' style='margin-top:6px'>Watchlist</div>", unsafe_allow_html=True)
    user_id = auth.current_user_id()
    tickers = wl.get_watchlist(user_id) if user_id else []
    if not tickers:
        st.markdown(
            f"<div style='font-size:13px;line-height:1.55;color:{T.TEXT_3};"
            f"border:1px dashed {T.BORDER_HI};border-radius:11px;padding:16px 14px'>"
            f"Star a ticker to add it to your watchlist.</div>",
            unsafe_allow_html=True,
        )
        return
    for t in tickers:
        if st.button(t, key=f"watchlist_row_{t}", width="stretch"):
            st.session_state["pending_jump"] = t
            st.rerun()


def render_dashboard_view() -> None:
    main_col, watch_col = st.columns([5, 1.3], gap="large")
    with watch_col:
        _render_watchlist_panel()
    with main_col:
        # --------------------------------------------------------------------------
        # Header
        # --------------------------------------------------------------------------

        data = st.session_state["analysis_cache"].get(cache_key)

        refresh_label = (
            data["fetched_at"].strftime("%d %b %Y · %H:%M UTC") if data else "Not yet run"
        )
        company = data["technical"].get("long_name", active_ticker) if data else ""

        st.markdown(
            f"<div style='margin:0 0 26px'>"
            f"<div class='pt-h' style='margin-bottom:8px'>{company or 'Dashboard'}</div>"
            f"<div style='display:flex;align-items:baseline;gap:14px;flex-wrap:wrap'>"
            f"<span style='font-size:40px;font-weight:600;letter-spacing:-0.035em;"
            f"color:{T.TEXT};line-height:1'>{active_ticker}</span>"
            f"<span style='font-size:12.5px;color:{T.TEXT_3}'>Updated {refresh_label}</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        if st.session_state.get("analysis_error") == "missing_key":
            st.warning(
                "Add your API keys in the sidebar's **API Setup Required** section "
                "to run analysis.",
                icon="🔑",
            )
        elif st.session_state.get("analysis_error"):
            raw_err = st.session_state["analysis_error"]
            low = raw_err.lower()
            if "503" in raw_err or "unavailable" in low or "overloaded" in low:
                st.error("The AI service is overloaded right now. Wait a moment and press Analyze again.",
                         icon=":material/cloud_off:")
            elif "429" in raw_err or "resource_exhausted" in low or "quota" in low:
                st.error("The AI service's usage limit was reached. Try again in a few minutes.",
                         icon=":material/hourglass_top:")
            else:
                st.error(f"Analysis failed: {raw_err}")

        if not data:
            st.info("Select a ticker in the sidebar and click **Analyze** to load the PulseTrade dashboard.")
            st.stop()

        technical = data["technical"]
        history_df = data["history"]
        news = data["news"]
        sentiment = data["ai"]["sentiment"]
        outlook = data["ai"]["outlook"]

        if news.get("error"):
            st.warning(f"News data notice: {news['error']}", icon="📰")

        # --------------------------------------------------------------------------
        # Reusable components
        # --------------------------------------------------------------------------


        def _base_chart_layout(**overrides) -> dict:
            return T.chart_layout(**overrides)

        def render_meter(value: float, left: str, right: str, color: str) -> None:
            st.markdown(T.meter_html(value, left, right, color), unsafe_allow_html=True)

        def sentiment_color(score: float) -> str:
            if score >= 0.15:
                return T.BULLISH
            if score <= -0.15:
                return T.BEARISH
            return T.NEUTRAL

        def lean_color(score: float) -> str:
            return T.BULLISH if score >= 0 else T.BEARISH

        def render_lean_caption(lean_score: float) -> str:
            side = "Bullish" if lean_score >= 0 else "Bearish"
            mag = round(abs(lean_score) * 100)
            c = lean_color(lean_score)
            return (
                f"<div style='margin-top:14px;font-size:15px;font-weight:600;"
                f"letter-spacing:-0.015em;color:{T.TEXT}'>Leans {side} "
                f"<span style='color:{c};font-variant-numeric:tabular-nums'>{mag}%</span></div>"
            )

        DISCLAIMER_HTML = (
            "<div class='pt-note'>AI-generated outlook based on sentiment and trend "
            "data — not financial advice. This is not a recommendation to buy or sell.</div>"
        )

        # --------------------------------------------------------------------------
        # Key metrics row (always visible)
        # --------------------------------------------------------------------------

        col1, col2, col3, col4 = st.columns(4, gap="small")

        def _tinted(color: str) -> str:
            """A state-coloured wash inside a card. The accent comes from the
            data itself — bullish cards glow green, bearish red — so colour
            is never arbitrary decoration."""
            return (
                f"position:relative;overflow:hidden;"
                f"background-image:radial-gradient(120% 90% at 100% 0%,"
                f"{color}1F,transparent 58%);"
            )

        with col1:
            price_val = technical["current_price"]
            pct_val = technical["pct_change_24h"] or 0.0
            up = pct_val >= 0
            c = T.BULLISH if up else T.BEARISH
            arrow = "\u2191" if up else "\u2193"
            st.markdown(
                f"<div class='pt-card' style='{_tinted(c)}'>"
                f"<div class='pt-label'>Last Price</div>"
                f"<div class='pt-value'>${price_val:,.2f}</div>"
                f"<div class='pt-delta' style='color:{c}'>{arrow} {abs(pct_val):.2f}% today</div></div>",
                unsafe_allow_html=True,
            )

        with col2:
            score = sentiment["sentiment_score"]
            c = sentiment_color(score)
            st.markdown(
                f"<div class='pt-card' style='{_tinted(c)}'>"
                f"<div class='pt-label'>Sentiment Index</div>"
                f"<div class='pt-value'>{score:+.2f}</div>"
                f"<div class='pt-delta' style='color:{c}'>{sentiment['sentiment_label']}</div>"
                f"<div style='margin-top:16px'>{T.meter_html(score, 'Negative', 'Positive', c)}</div></div>",
                unsafe_allow_html=True,
            )

        with col3:
            vol = technical["volatility_pct"]
            vol_label = technical["volatility_label"]
            vol_frac = max(0.0, min(1.0, vol / 80.0))
            vc = T.AMBER if vol >= 45 else T.CYAN
            st.markdown(
                f"<div class='pt-card' style='{_tinted(vc)}'>"
                f"<div class='pt-label'>Volatility</div>"
                f"<div class='pt-value'>{vol:.1f}%</div>"
                f"<div class='pt-delta' style='color:{T.TEXT_2}'>{vol_label} &middot; annualized</div>"
                f"<div style='margin-top:16px;height:3px;border-radius:2px;background:rgba(255,255,255,0.07)'>"
                f"<div style='height:3px;border-radius:2px;width:{vol_frac*100:.0f}%;"
                f"background:linear-gradient(90deg,{T.ACCENT},{vc});box-shadow:0 0 12px {vc}66'></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

        with col4:
            market_open, _ = _market_status()
            status = "Open" if market_open else "Closed"
            c = T.BULLISH if market_open else T.TEXT_3
            vol_str = f"{technical['volume']:,}" if technical.get("volume") else "\u2014"
            st.markdown(
                f"<div class='pt-card' style='{_tinted(c)}'>"
                f"<div class='pt-label'>{active_ticker} &middot; Market</div>"
                f"<div class='pt-value'>{status}</div>"
                f"<div class='pt-delta' style='color:{T.TEXT_2}'>"
                f"<span style='color:{c};text-shadow:0 0 9px {c}'>&#9679;</span> "
                f"Vol {vol_str}</div></div>",
                unsafe_allow_html=True,
            )

        st.write("")

        # --------------------------------------------------------------------------

        lean = outlook["directional_lean"]
        tab_detailed, tab_simple = st.tabs(["Detailed", "Simple"])

        # ---------------------------- DETAILED ------------------------------
        with tab_detailed:
            left_col, right_col = st.columns([2, 1], gap="large")

            with left_col:
                if not history_df.empty:
                    st.markdown(
                        f"<div class='pt-h' style='margin-top:6px'>Price &middot; {time_horizon}</div>",
                        unsafe_allow_html=True,
                    )
                    price_fig = go.Figure()
                    # subtle area wash under the price line
                    price_fig.add_trace(go.Scatter(
                        x=history_df.index, y=history_df["Close"], name="Close",
                        line=dict(color=T.ACCENT, width=2),
                        fill="tozeroy", fillcolor="rgba(79,139,255,0.07)",
                        hovertemplate="$%{y:.2f}<extra></extra>",
                    ))
                    price_fig.add_trace(go.Scatter(
                        x=history_df.index, y=history_df["SMA_7"], name="7D avg",
                        line=dict(color=T.TEXT_2, width=1.2, dash="dot"),
                        hovertemplate="$%{y:.2f}<extra>7D</extra>",
                    ))
                    price_fig.add_trace(go.Scatter(
                        x=history_df.index, y=history_df["SMA_30"], name="30D avg",
                        line=dict(color=T.TEXT_3, width=1.2, dash="dot"),
                        hovertemplate="$%{y:.2f}<extra>30D</extra>",
                    ))
                    lo = float(history_df["Close"].min())
                    hi = float(history_df["Close"].max())
                    pad = (hi - lo) * 0.12 or 1.0
                    price_fig.update_layout(**T.chart_layout(
                        height=330, yaxis=dict(
                            range=[lo - pad, hi + pad],
                            showgrid=True, gridcolor="rgba(255,255,255,0.045)",
                            zeroline=False, showline=False, ticks="",
                            tickfont=dict(size=11, color=T.TEXT_3), tickprefix="$",
                        ),
                    ))
                    st.plotly_chart(price_fig, width="stretch", config=T.CHART_CONFIG)

                    c1, c2 = st.columns(2, gap="medium")
                    with c1:
                        st.markdown("<div class='pt-h'>Daily change</div>", unsafe_allow_html=True)
                        chg = history_df["Daily_Pct_Change"].fillna(0)
                        chg_fig = go.Figure(go.Bar(
                            x=history_df.index, y=chg,
                            marker_color=[T.BULLISH if v >= 0 else T.BEARISH for v in chg],
                            hovertemplate="%{y:.2f}%<extra></extra>",
                        ))
                        chg_fig.update_layout(**T.chart_layout(
                            height=168, margin=dict(l=8, r=8, t=6, b=8),
                            yaxis=dict(ticksuffix="%", showgrid=True,
                                       gridcolor="rgba(255,255,255,0.045)", zeroline=False,
                                       showline=False, ticks="",
                                       tickfont=dict(size=11, color=T.TEXT_3)),
                        ))
                        st.plotly_chart(chg_fig, width="stretch", config=T.CHART_CONFIG)
                    with c2:
                        st.markdown("<div class='pt-h'>Volume</div>", unsafe_allow_html=True)
                        vol_fig = go.Figure(go.Bar(
                            x=history_df.index, y=history_df["Volume"],
                            marker_color="rgba(79,139,255,0.42)",
                            hovertemplate="%{y:,.0f}<extra></extra>",
                        ))
                        vol_fig.update_layout(**T.chart_layout(
                            height=168, margin=dict(l=8, r=8, t=6, b=8),
                        ))
                        st.plotly_chart(vol_fig, width="stretch", config=T.CHART_CONFIG)
                else:
                    st.warning("No historical data available for this ticker.")

            with right_col:
                render_sentiment_panel(sentiment, news)

            st.write("")
            st.markdown("<div class='pt-h'>Technicals</div>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4, gap="small")
            m1.metric("Volume", f"{technical['volume']:,}" if technical['volume'] else "\u2014")
            m2.metric("7-Day SMA", f"${technical['sma_7']:,.2f}" if technical['sma_7'] else "\u2014")
            m3.metric("30-Day SMA", f"${technical['sma_30']:,.2f}" if technical['sma_30'] else "\u2014")
            m4.metric("Momentum", f"{technical['momentum_pct']:+.2f}%" if technical['momentum_pct'] is not None else "\u2014")

            st.write("")
            st.markdown("<div class='pt-h'>30-Day Outlook</div>", unsafe_allow_html=True)
            o1, o2 = st.columns([1, 1.6], gap="large")
            with o1:
                st.markdown(
                    f"<div class='pt-card'>"
                    f"<div class='pt-label'>Directional Lean</div>"
                    f"<div class='pt-value' style='color:{lean_color(lean)}'>{lean:+.2f}</div>"
                    f"<div style='margin-top:18px'>"
                    f"{T.meter_html(lean, 'Bearish', 'Bullish', lean_color(lean))}</div>"
                    f"{render_lean_caption(lean)}</div>",
                    unsafe_allow_html=True,
                )
            with o2:
                cat = "".join(f"<li style='margin-bottom:7px'>{c}</li>" for c in outlook.get("catalysts", []))
                rsk = "".join(f"<li style='margin-bottom:7px'>{r}</li>" for r in outlook.get("risks", []))
                st.markdown(
                    f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:26px'>"
                    f"<div><div class='pt-h' style='color:{T.BULLISH}'>Catalysts</div>"
                    f"<ul class='pt-body' style='padding-left:17px;margin:0'>{cat}</ul></div>"
                    f"<div><div class='pt-h' style='color:{T.BEARISH}'>Risks</div>"
                    f"<ul class='pt-body' style='padding-left:17px;margin:0'>{rsk}</ul></div></div>",
                    unsafe_allow_html=True,
                )

            st.write("")
            st.markdown(
                f"<div class='pt-panel'><div class='pt-h'>Written Outlook</div>"
                f"<div class='pt-body'>{outlook.get('detailed_outlook','')}</div>"
                f"{DISCLAIMER_HTML}</div>",
                unsafe_allow_html=True,
            )

        # ------------------------------ SIMPLE -------------------------------
        with tab_simple:
            company_name = technical.get("long_name", active_ticker)
            pct = technical.get("pct_change_24h") or 0
            if pct > 0.5:
                arrow, trend_word, tc = "\u2197", "climbing", T.BULLISH
            elif pct < -0.5:
                arrow, trend_word, tc = "\u2198", "slipping", T.BEARISH
            else:
                arrow, trend_word, tc = "\u2192", "holding steady", T.NEUTRAL

            sentiment_word = {
                "Strongly Positive": "very positive",
                "Positive": "mostly positive",
                "Neutral": "mixed",
                "Negative": "mostly negative",
                "Strongly Negative": "very negative",
            }.get(sentiment.get("sentiment_label", "Neutral"), "mixed")

            plain = (f"{company_name}'s stock has been {trend_word} recently, and online "
                     f"buzz has been {sentiment_word}")
            top_driver = (sentiment.get("top_drivers") or [None])[0]
            def _decap(s: str) -> str:
                """Lowercase only the leading word when it's ordinary prose.
                A blanket .lower() mangles proper nouns — 'Apple Intelligence'
                and 'iOS 27' must survive being spliced mid-sentence."""
                if not s:
                    return s
                first = s.split()[0]
                if first.isupper() or (len(first) > 1 and first[1].isupper()):
                    return s  # acronym ("AI", "EU") or camel-ish ("iOS")
                return s[0].lower() + s[1:]

            plain += f", largely because of {_decap(top_driver)}." if top_driver else "."

            _, mid, _ = st.columns([1, 3, 1])
            with mid:
                st.markdown(
                    f"<div style='text-align:center;padding:24px 0 6px'>"
                    f"<div class='pt-h'>How is it doing?</div>"
                    f"<div style='font-size:64px;line-height:1;color:{tc};margin:10px 0 6px'>{arrow}</div>"
                    f"<div style='font-size:15px;color:{T.TEXT_3}'>Currently {trend_word}</div></div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='pt-panel' style='text-align:center'>"
                    f"<div style='font-size:19px;line-height:1.6;color:{T.TEXT};"
                    f"letter-spacing:-0.012em'>{plain}</div></div>",
                    unsafe_allow_html=True,
                )
                st.write("")
                st.markdown(
                    f"<div class='pt-panel'><div class='pt-h'>Next 30 Days</div>"
                    f"<div style='margin:16px 0 4px'>"
                    f"{T.meter_html(lean, 'Bearish', 'Bullish', lean_color(lean))}</div>"
                    f"{render_lean_caption(lean)}"
                    f"<div class='pt-body' style='margin-top:16px'>{outlook.get('simple_outlook','')}</div>"
                    f"{DISCLAIMER_HTML}</div>",
                    unsafe_allow_html=True,
                )


# --------------------------------------------------------------------------
# About — same design system as the rest of the product. Every claim maps to
# a feature that actually ships; nothing aspirational.
# --------------------------------------------------------------------------


def _about_html() -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">{T.GOOGLE_FONTS}
<style>
{T.BASE_CSS}
/* transparent so the app's ambient wash shows through the iframe */
body {{ background:transparent; }}
.wrap {{ max-width:860px; margin:0 auto; padding:14px 8px 60px; }}
section {{ padding:52px 0; border-top:1px solid {T.BORDER}; }}
section:first-of-type {{ border-top:0; padding-top:10px; }}
h2 {{ font-size:30px; }}
p {{ font-size:16px; margin-top:16px; max-width:64ch; }}
ul,ol {{ font-size:16px; line-height:1.72; color:{T.TEXT_2}; max-width:64ch;
        padding-left:20px; margin:14px 0 0; }}
li {{ margin-bottom:9px; }} li strong {{ color:{T.TEXT}; font-weight:600; }}
.note {{ border-left:2px solid {T.ACCENT}; padding:3px 0 3px 18px; margin-top:20px;
         font-size:14px; line-height:1.62; color:{T.TEXT_3}; max-width:64ch; }}
.r {{ opacity:0; transform:translateY(20px);
      transition:opacity .8s {T.EASE}, transform .8s {T.EASE}; }}
.r.on {{ opacity:1; transform:none; }}
</style></head><body><div class="wrap">

<section>
  <div class="eyebrow r">The Problem</div>
  <h2 class="r" style="margin-top:14px">Numbers only tell half the story.</h2>
  <p class="r">Traditional stock tools show you charts and numbers. But markets don't move on
     numbers alone &mdash; they move on news, sentiment, and momentum. Most investors have no
     easy way to see both sides of the story in one place.</p>
</section>

<section>
  <div class="eyebrow r">What It Does</div>
  <h2 class="r" style="margin-top:14px">Two halves of one picture.</h2>
  <p class="r">PulseTrade combines two things that are usually kept apart:</p>
  <ul class="r">
    <li><strong>Hard financial data</strong> &mdash; real-time prices, moving averages, and
        volatility, pulled directly from the market.</li>
    <li><strong>Live sentiment intelligence</strong> &mdash; an engine that reads current news and
        discussion about a stock and distills it into a clear sentiment score, backed by real
        cited sources.</li>
  </ul>
  <p class="r">Together, they give you a fuller picture: not just where a stock has been, but how
     the world is currently talking about it.</p>
</section>

<section>
  <div class="eyebrow r">How It Works</div>
  <h2 class="r" style="margin-top:14px">Four steps.</h2>
  <ol class="r">
    <li><strong>Pick a ticker.</strong> Historical prices, daily change, and moving averages load instantly.</li>
    <li><strong>Sentiment is calculated live.</strong> Recent news and discussion are scored from
        strongly negative to strongly positive.</li>
    <li><strong>See the lean.</strong> A bearish&ndash;bullish meter shows which way the data points,
        backed by the specific catalysts and risks driving it.</li>
    <li><strong>Get a 30-day outlook.</strong> A plain-language read on where sentiment and momentum
        are trending &mdash; not a price prediction, but a clear-eyed view of current direction.</li>
  </ol>
</section>

<section>
  <div class="eyebrow r">Built For Everyone</div>
  <h2 class="r" style="margin-top:14px">Two ways in.</h2>
  <ul class="r">
    <li><strong>Detailed View</strong> &mdash; full metrics, sentiment breakdowns, cited sources, and
        charts for users who want to dig into the data themselves.</li>
    <li><strong>Simple View</strong> &mdash; a plain-English summary and a single visual cue for anyone
        who just wants to know: how's this stock doing right now?</li>
  </ul>
</section>

<section>
  <div class="eyebrow r">Built Responsibly</div>
  <h2 class="r" style="margin-top:14px">Information, not advice.</h2>
  <p class="r">PulseTrade's AI never predicts exact prices and never tells you to buy or sell. It
     reports what the data and sentiment currently show &mdash; clearly labeled, always cited, and
     always presented as information, not advice.</p>
  <div class="note r">AI-generated outlook based on sentiment and trend data &mdash; not financial
     advice. This is not a recommendation to buy or sell.</div>
</section>

</div><script>
  var io = new IntersectionObserver(function(es){{
    es.forEach(function(e){{ if(e.isIntersecting){{ e.target.classList.add('on'); io.unobserve(e.target); }} }});
  }}, {{ threshold:0.1 }});
  document.querySelectorAll('.r').forEach(function(el){{ io.observe(el); }});
</script>
{T.AUTOFIT_JS}
</body></html>"""


def render_about_page() -> None:
    st.markdown(
        f"<div style='margin:0 0 6px'><div class='pt-h'>About</div>"
        f"<div style='font-size:40px;font-weight:600;letter-spacing:-0.035em;"
        f"color:{T.TEXT};line-height:1.05'>What is PulseTrade?</div></div>",
        unsafe_allow_html=True,
    )
    components.html(_about_html(), height=2000, scrolling=False)

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("Back to Dashboard", key="about_back_bottom",
                     type="primary", width="stretch"):
            st.session_state["view"] = "dashboard"
            st.rerun()


# --------------------------------------------------------------------------
# Page dispatch
# --------------------------------------------------------------------------

_page = st.session_state["page"]

if _page == "landing":
    render_landing_page()
elif _page == "login":
    render_login_page()
elif st.session_state["view"] == "movers":
    render_movers_page()
elif st.session_state["view"] == "about":
    render_about_page()
else:
    render_dashboard_view()
