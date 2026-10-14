"""PulseTrade — weekly S&P 500 movers.

The ten biggest gainers and ten biggest decliners in the S&P 500 over the
past trading week, refreshed every Sunday at 5:00 PM US Eastern.

How the Sunday refresh works: rather than relying on a background job
(which silently misses runs whenever this machine is asleep or the app is
stopped), every snapshot is tied to the most recent Sunday-5-PM boundary.
The first time anyone opens the page after that boundary, a new snapshot
is computed and saved to disk; everyone sees that same snapshot until the
following Sunday at 5 PM. The list is always the one for the current week,
whether or not the app was running at 5 PM.

"The past week" = the last close on or before that Sunday (normally
Friday) versus the last close on or before the Sunday before — so market
holidays are handled naturally.
"""

from __future__ import annotations

import html
import io
import json
import time as time_mod
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

import theme as T

ET = ZoneInfo("America/New_York")
REFRESH_WEEKDAY = 6          # Sunday
REFRESH_TIME = time(17, 0)   # 5:00 PM ET
TOP_N = 10

_DATA_DIR = Path(__file__).parent / "data"
_SNAPSHOT = _DATA_DIR / "weekly_movers.json"
_CONSTITUENTS = _DATA_DIR / "sp500_constituents.csv"
_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


# --------------------------------------------------------------------------
# Schedule
# --------------------------------------------------------------------------


def current_anchor(now: datetime | None = None) -> datetime:
    """The most recent Sunday 5:00 PM ET at or before `now`."""
    now = (now or datetime.now(ET)).astimezone(ET)
    days_back = (now.weekday() - REFRESH_WEEKDAY) % 7
    anchor = datetime.combine(now.date() - timedelta(days=days_back), REFRESH_TIME, ET)
    if anchor > now:
        anchor -= timedelta(days=7)
    return anchor


def next_anchor(now: datetime | None = None) -> datetime:
    return current_anchor(now) + timedelta(days=7)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


def _fetch_constituents() -> pd.DataFrame:
    resp = requests.get(_WIKI_URL, headers={"User-Agent": "Mozilla/5.0 PulseTrade"}, timeout=20)
    resp.raise_for_status()
    table = pd.read_html(io.StringIO(resp.text), attrs={"id": "constituents"})[0]
    df = pd.DataFrame({
        "symbol": table["Symbol"].astype(str).str.strip(),
        "name": table["Security"].astype(str).str.strip(),
        "sector": table["GICS Sector"].astype(str).str.strip(),
    })
    _DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(_CONSTITUENTS, index=False)
    return df


def _constituents() -> pd.DataFrame:
    """Fresh list each weekly refresh; fall back to the last saved copy."""
    try:
        return _fetch_constituents()
    except Exception:
        if _CONSTITUENTS.exists():
            return pd.read_csv(_CONSTITUENTS)
        raise


def _last_close_on_or_before(closes: pd.DataFrame, day: date) -> tuple[pd.Series, date]:
    rows = closes.loc[closes.index.date <= day]
    if rows.empty:
        raise ValueError(f"No trading data on or before {day}")
    return rows.iloc[-1], rows.index[-1].date()


def _download(symbols: list[str], start: date, end: date, threads: bool) -> pd.DataFrame:
    raw = yf.download(symbols, start=start, end=end, interval="1d",
                      auto_adjust=True, progress=False, threads=threads)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        return raw["Close"]
    return raw[["Close"]].rename(columns={"Close": symbols[0]})


def _download_closes(symbols: list[str], start: date, end: date) -> pd.DataFrame:
    """Bulk download, then retry anything that came back empty. Yahoo
    throttles large bursts and reports the casualties as 'possibly
    delisted' — dropping them silently could hide a real top mover."""
    closes = _download(symbols, start, end, threads=True)
    for attempt in range(2):
        missing = [s for s in symbols if s not in closes.columns or closes[s].isna().all()]
        if not missing:
            break
        time_mod.sleep(2 + attempt * 3)
        retry = _download(missing, start, end, threads=False)
        if not retry.empty:
            closes = closes.drop(columns=[c for c in retry.columns if c in closes.columns])
            closes = closes.join(retry, how="outer")
    return closes


def compute_snapshot(anchor: datetime) -> dict:
    members = _constituents()
    # Yahoo uses '-' where the index list uses '.', e.g. BRK.B -> BRK-B
    yahoo = {row.symbol.replace(".", "-"): row for row in members.itertuples()}

    end_day = anchor.date()
    start_day = end_day - timedelta(days=7)
    closes = _download_closes(list(yahoo), start_day - timedelta(days=10), end_day + timedelta(days=1))

    end_px, end_date = _last_close_on_or_before(closes, end_day)
    start_px, start_date = _last_close_on_or_before(closes, start_day)
    pct = ((end_px / start_px) - 1.0) * 100.0
    pct = pct.replace([float("inf"), float("-inf")], pd.NA).dropna()

    def rows(series: pd.Series) -> list[dict]:
        out = []
        for sym, change in series.items():
            m = yahoo.get(sym)
            out.append({
                "symbol": sym,
                "name": m.name if m is not None else sym,
                "sector": m.sector if m is not None else "",
                "pct": round(float(change), 2),
                "close": round(float(end_px[sym]), 2),
            })
        return out

    return {
        "anchor": anchor.isoformat(),
        "generated_at": datetime.now(ET).isoformat(),
        "week_start": start_date.isoformat(),
        "week_end": end_date.isoformat(),
        "universe": int(pct.size),
        "gainers": rows(pct.sort_values(ascending=False).head(TOP_N)),
        "losers": rows(pct.sort_values(ascending=True).head(TOP_N)),
    }


def _load_saved() -> dict | None:
    try:
        return json.loads(_SNAPSHOT.read_text())
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _snapshot_for(anchor_iso: str) -> dict:
    """One computation per weekly boundary per process; also persisted, so a
    restart mid-week doesn't recompute."""
    saved = _load_saved()
    if saved and saved.get("anchor") == anchor_iso:
        return saved
    snap = compute_snapshot(datetime.fromisoformat(anchor_iso))
    _DATA_DIR.mkdir(exist_ok=True)
    tmp = _SNAPSHOT.with_suffix(".tmp")
    tmp.write_text(json.dumps(snap, indent=2))
    tmp.replace(_SNAPSHOT)
    return snap


def get_weekly_movers() -> tuple[dict | None, str | None]:
    """(snapshot, warning). Falls back to last week's list if this week's
    can't be built (e.g. no network), and says so."""
    anchor_iso = current_anchor().isoformat()
    try:
        return _snapshot_for(anchor_iso), None
    except Exception as exc:
        saved = _load_saved()
        if saved:
            return saved, f"Couldn't refresh this week's list ({exc}). Showing the last saved one."
        return None, f"Couldn't build the weekly list: {exc}"


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------


def _fmt_day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}"


def _mover_rows(items: list[dict], color: str) -> None:
    peak = max((abs(i["pct"]) for i in items), default=1.0) or 1.0
    for rank, item in enumerate(items, start=1):
        width = max(4.0, abs(item["pct"]) / peak * 100)
        tag = "up" if color == T.BULLISH else "dn"
        with st.container(key=f"mvrow_{tag}_{rank}"):
            c_row, c_btn = st.columns([12, 1], vertical_alignment="center", gap="small")
        with c_row:
            st.markdown(
                f"<div class='mv-row'>"
                f"<span class='mv-rank'>{rank}</span>"
                f"<span class='mv-id'><b>{html.escape(item['symbol'])}</b>"
                f"<span>{html.escape(item['name'])}</span></span>"
                f"<span class='mv-val'>"
                f"<b style='color:{color}'>{item['pct']:+.2f}%</b>"
                f"<span>${item['close']:,.2f}</span></span>"
                f"<span class='mv-bar'><i style='width:{width:.0f}%;background:{color};"
                f"box-shadow:0 0 10px {color}66'></i></span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with c_btn:
            if st.button("", key=f"mv_{tag}_{rank}", icon=":material/arrow_forward:",
                         help=f"Analyze {item['symbol']}", type="tertiary"):
                st.session_state["pending_jump"] = item["symbol"]
                st.rerun()


def render_movers_page() -> None:
    now = datetime.now(ET)
    nxt = next_anchor(now)

    st.markdown(
        f"<div style='margin:0 0 22px'>"
        f"<div class='pt-h' style='margin-bottom:8px'>S&amp;P 500 &middot; Weekly movers</div>"
        f"<div style='font-size:40px;font-weight:600;letter-spacing:-0.035em;color:{T.TEXT};"
        f"line-height:1.05'>Biggest moves this week</div></div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Building this week's list from all S&P 500 stocks…"):
        snap, warning = get_weekly_movers()
    if warning:
        st.warning(warning, icon=":material/schedule:")
    if not snap:
        return

    gen = datetime.fromisoformat(snap["generated_at"]).astimezone(ET)
    st.markdown(
        f"<div class='mv-meta'>"
        f"<span><i class='mv-dot'></i>Week of <b>{_fmt_day(snap['week_start'])} – {_fmt_day(snap['week_end'])}</b>"
        f" &middot; closing prices</span>"
        f"<span>{snap['universe']} stocks ranked</span>"
        f"<span>Updated {gen:%a %b} {gen.day}, {gen.strftime('%I:%M %p').lstrip('0')} ET</span>"
        f"<span>Next update {nxt:%a %b} {nxt.day}, {nxt.strftime('%I:%M %p').lstrip('0')} ET</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f"<div class='mv-head' style='--mv:{T.BULLISH}'>{T.icon('chart', 16, T.BULLISH)}"
            f"<span>Top gainers</span></div>",
            unsafe_allow_html=True,
        )
        _mover_rows(snap["gainers"], T.BULLISH)
    with right:
        st.markdown(
            f"<div class='mv-head' style='--mv:{T.BEARISH}'>"
            f"<span style='display:inline-flex;transform:scaleY(-1)'>{T.icon('chart', 16, T.BEARISH)}</span>"
            f"<span>Top decliners</span></div>",
            unsafe_allow_html=True,
        )
        _mover_rows(snap["losers"], T.BEARISH)

    st.markdown(
        "<div class='pt-note'>Weekly price change from closing prices (Yahoo Finance), "
        "adjusted for splits and dividends. For information only — not financial advice.</div>",
        unsafe_allow_html=True,
    )


MOVERS_CSS = f"""
.mv-meta {{ display:flex; flex-wrap:wrap; gap:8px; margin:-6px 0 24px; }}
.mv-meta span {{ font-size:12.5px; color:{T.TEXT_2}; padding:6px 11px; border-radius:8px;
  background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07);
  display:inline-flex; align-items:center; gap:8px; }}
.mv-meta b {{ color:{T.TEXT}; font-weight:600; }}
.mv-dot {{ width:7px; height:7px; border-radius:50%; background:{T.ACCENT};
  box-shadow:0 0 9px {T.ACCENT}; display:inline-block; }}
.mv-head {{ display:flex; align-items:center; gap:10px; margin:0 0 10px; padding:12px 14px;
  border-radius:12px; font-size:15px; font-weight:600; color:{T.TEXT};
  background:linear-gradient(90deg, color-mix(in srgb, var(--mv) 16%, transparent), transparent);
  border:1px solid color-mix(in srgb, var(--mv) 30%, transparent); }}
.mv-row {{ position:relative; display:grid; grid-template-columns:28px minmax(0,1fr) auto;
  align-items:center; gap:12px; padding:11px 14px 14px; border-radius:11px;
  background:linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.012));
  border:1px solid rgba(255,255,255,0.065);
  transition:transform .35s {T.EASE}, border-color .35s {T.EASE}; }}
.mv-row:hover {{ transform:translateX(3px); border-color:rgba(255,255,255,0.14); }}
.mv-rank {{ font-size:12px; font-weight:700; color:{T.TEXT_3}; font-variant-numeric:tabular-nums; }}
.mv-id {{ min-width:0; display:flex; flex-direction:column; gap:2px; }}
.mv-id b {{ font-size:14px; font-weight:600; color:{T.TEXT}; letter-spacing:0.01em; }}
.mv-id span {{ font-size:12px; color:{T.TEXT_3}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.mv-val {{ display:flex; flex-direction:column; align-items:flex-end; gap:2px;
  font-variant-numeric:tabular-nums; }}
.mv-val b {{ font-size:15px; font-weight:600; }}
.mv-val span {{ font-size:12px; color:{T.TEXT_3}; }}
/* keep each row and its analyze button on one line at every width */
[class*="st-key-mvrow_"] {{ margin-bottom:4px; }}
[class*="st-key-mvrow_"] [data-testid="stHorizontalBlock"] {{ flex-wrap:nowrap !important; gap:6px; }}
[class*="st-key-mvrow_"] [data-testid="stColumn"]:first-child {{ flex:1 1 auto !important; min-width:0 !important; width:auto !important; }}
[class*="st-key-mvrow_"] [data-testid="stColumn"]:last-child {{ flex:0 0 40px !important; min-width:40px !important; width:40px !important; }}
[class*="st-key-mvrow_"] button {{ width:40px; height:40px; border-radius:10px; color:{T.TEXT_3}; }}
[class*="st-key-mvrow_"] button:hover {{ color:{T.TEXT}; background:rgba(255,255,255,0.06); }}
.mv-bar {{ position:absolute; left:14px; right:14px; bottom:6px; height:2px;
  border-radius:1px; background:rgba(255,255,255,0.05); overflow:hidden; }}
.mv-bar i {{ display:block; height:2px; border-radius:1px; }}
"""
