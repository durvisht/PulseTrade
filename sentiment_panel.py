"""PulseTrade — the Market Sentiment panel on the dashboard.

Turns the engine's one long summary into a scannable layout: a one-line
headline, numbered drivers, short takeaways, and a source list where each
article carries its own sentiment reading.
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import streamlit as st

import theme as T

_ABBREV = re.compile(r"(?:\b(?:Inc|Corp|Co|Ltd|Mr|Ms|Dr|vs|No|St)|(?:\b[A-Za-z]\.)+[A-Za-z])\.$")


def split_sentences(text: str) -> list[str]:
    """Sentence split that doesn't break on 'Inc.' or 'U.S.'."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“'])", (text or "").strip())
    out: list[str] = []
    for p in parts:
        if out and _ABBREV.search(out[-1]):
            out[-1] = f"{out[-1]} {p}"
        elif p:
            out.append(p)
    return out


def _tone(score: float) -> tuple[str, str]:
    if score >= 0.15:
        return T.BULLISH, "Positive"
    if score <= -0.15:
        return T.BEARISH, "Negative"
    return T.NEUTRAL, "Neutral"


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _source_row(title: str, url: str, source: str, score: float | None) -> str:
    color, label = _tone(score) if score is not None else (T.TEXT_3, "")
    score_txt = f"{score:+.2f}" if score is not None else ""
    safe_url = html.escape(url, quote=True)
    return (
        f"<a class='sp-src' href='{safe_url}' target='_blank' rel='noopener'>"
        f"<span class='sp-src-dot' style='background:{color};box-shadow:0 0 8px {color}'></span>"
        f"<span class='sp-src-body'>"
        f"<span class='sp-src-title'>{html.escape(title)}</span>"
        f"<span class='sp-src-meta'>{html.escape(source or _domain(url))}"
        f"{' &middot; ' if score_txt else ''}"
        f"<span style='color:{color}'>{label} {score_txt}</span></span>"
        f"</span></a>"
    )


def render_sentiment_panel(sentiment: dict, news: dict) -> None:
    score = float(sentiment.get("sentiment_score", 0.0))
    color, _ = _tone(score)
    label = sentiment.get("sentiment_label", "Neutral")
    sentences = split_sentences(sentiment.get("summary", ""))
    lede, rest = (sentences[0], sentences[1:]) if sentences else ("", [])

    # ---- headline card
    st.markdown(
        f"<div class='pt-panel sp-head' style='background-image:radial-gradient(120% 100% at 100% 0%,{color}22,transparent 60%)'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center'>"
        f"<span class='pt-h' style='margin:0'>Market Sentiment</span>"
        f"<span class='sp-pill' style='color:{color};border-color:{color}55;background:{color}14'>"
        f"{html.escape(label)} &middot; {score:+.2f}</span></div>"
        f"<div class='sp-lede'>{html.escape(lede)}</div>"
        f"{T.meter_html(score, 'Negative', 'Positive', color)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ---- drivers
    drivers = sentiment.get("top_drivers", [])
    if drivers:
        rows = "".join(
            f"<div class='sp-driver'><span class='sp-num'>{i}</span>"
            f"<span>{html.escape(d)}</span></div>"
            for i, d in enumerate(drivers, start=1)
        )
        st.markdown(
            f"<div class='pt-panel sp-gap'><div class='pt-h'>What's moving it</div>{rows}</div>",
            unsafe_allow_html=True,
        )

    # ---- takeaways (the rest of the summary, as short points)
    if rest:
        pts = "".join(
            f"<div class='sp-point'><span class='sp-tick'></span><span>{html.escape(s)}</span></div>"
            for s in rest
        )
        st.markdown(
            f"<div class='pt-panel sp-gap'><div class='pt-h'>Key takeaways</div>{pts}</div>",
            unsafe_allow_html=True,
        )

    # ---- sources, each with its own article-level sentiment
    by_url = {a.get("url"): a for a in news.get("articles", [])}
    cites = sentiment.get("citations", [])
    if cites:
        rendered = []
        for c in cites:
            art = by_url.get(c["uri"], {})
            s = art.get("ticker_score")
            rendered.append(_source_row(c["title"], c["uri"], art.get("source", ""),
                                        float(s) if s is not None else None))
        st.markdown(
            f"<div class='pt-panel sp-gap'><div class='pt-h'>Sources &middot; {len(cites)}</div>"
            f"{''.join(rendered[:4])}</div>",
            unsafe_allow_html=True,
        )
        if len(rendered) > 4:
            with st.expander(f"{len(rendered) - 4} more sources"):
                st.markdown("".join(rendered[4:]), unsafe_allow_html=True)


PANEL_CSS = f"""
.sp-gap {{ margin-top:12px; }}
.sp-pill {{ font-size:12px; font-weight:600; padding:4px 10px; border-radius:999px;
  border:1px solid; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.sp-lede {{ margin:16px 0 18px; font-size:17px; line-height:1.5; font-weight:500;
  letter-spacing:-0.012em; color:{T.TEXT}; }}
.sp-driver {{ display:flex; gap:12px; align-items:flex-start; padding:10px 0;
  border-top:1px solid rgba(255,255,255,0.06); font-size:14px; line-height:1.45; color:{T.TEXT}; }}
.pt-h + .sp-driver {{ border-top:0; padding-top:2px; }}
.sp-num {{ flex:none; width:22px; height:22px; border-radius:7px; display:flex;
  align-items:center; justify-content:center; font-size:11.5px; font-weight:700;
  color:{T.ACCENT}; background:rgba(79,139,255,0.12); border:1px solid rgba(79,139,255,0.25); }}
.sp-point {{ display:flex; gap:11px; align-items:flex-start; padding:7px 0;
  font-size:14px; line-height:1.55; color:{T.TEXT_2}; }}
.sp-tick {{ flex:none; width:6px; height:6px; margin-top:8px; border-radius:50%;
  background:{T.VIOLET}; box-shadow:0 0 8px {T.VIOLET}; }}
a.sp-src {{ display:flex; gap:11px; align-items:flex-start; padding:10px 8px; margin:0 -8px;
  border-radius:9px; text-decoration:none !important; transition:background .2s {T.EASE}; }}
a.sp-src:hover {{ background:rgba(255,255,255,0.045); }}
.sp-src-dot {{ flex:none; width:7px; height:7px; margin-top:7px; border-radius:50%; }}
.sp-src-body {{ min-width:0; display:flex; flex-direction:column; gap:3px; }}
.sp-src-title {{ font-size:13.5px; line-height:1.4; color:{T.TEXT};
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
.sp-src-meta {{ font-size:11.5px; color:{T.TEXT_3}; font-variant-numeric:tabular-nums; }}
"""
