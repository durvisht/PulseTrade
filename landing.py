"""PulseTrade — landing page.

Honest scope note (per the project brief): Streamlit can't reproduce true
layered parallax or scroll-linked physics. What it *can* do cleanly, and
what's built here, is an embedded HTML surface with IntersectionObserver
reveals, CSS-driven atmosphere/motion, and a scroll-coupled drift on the
background washes. No external animation library, nothing faked.

Copy is the established PulseTrade About content — no new claims. The
hero product preview is a UI mockup and is labelled "Sample" so its
placeholder numbers can't be mistaken for live market data.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import theme as T

_ASSETS = Path(__file__).parent / "assets"

# Shown in the marquee. Symbols + names only — deliberately no prices, since
# fabricated quotes on a finance product would read as live market data.
_MARQUEE = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
    ("AMZN", "Amazon"), ("GOOGL", "Alphabet"), ("META", "Meta"),
    ("TSLA", "Tesla"), ("JPM", "JPMorgan"), ("V", "Visa"),
    ("COST", "Costco"), ("NFLX", "Netflix"), ("AMD", "AMD"),
    ("ORCL", "Oracle"), ("DIS", "Disney"), ("KO", "Coca-Cola"),
]


def logo_data_uri(name: str = "mark.png") -> str | None:
    path = _ASSETS / name
    if not path.exists():
        return None
    return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}"


def _marquee_row() -> str:
    chip = (
        "<span class='tick'><b>{s}</b><span>{n}</span></span>"
    )
    items = "".join(chip.format(s=s, n=n) for s, n in _MARQUEE)
    return items + items  # duplicated for a seamless loop


def _preview_card() -> str:
    """A UI preview used as the hero image. Explicitly labelled Sample."""
    spark = ("M0 78 L38 70 L76 82 L114 54 L152 62 L190 40 "
             "L228 48 L266 26 L304 34 L342 14 L380 20")
    return f"""
<div class="preview elev">
  <div class="pv-top">
    <span class="pv-chip">{T.logo_mark_svg(13, T.ACCENT)} AAPL</span>
    <span class="pv-sample">Sample</span>
  </div>
  <div class="pv-price">
    <span class="pv-num">$331.41</span>
    <span class="pv-delta">&#8593; 2.14%</span>
  </div>
  <svg class="pv-spark" viewBox="0 0 380 96" preserveAspectRatio="none">
    <defs>
      <linearGradient id="pvfill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stop-color="{T.ACCENT}" stop-opacity="0.42"/>
        <stop offset="100%" stop-color="{T.ACCENT}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path d="{spark} L380 96 L0 96 Z" fill="url(#pvfill)" class="pv-area"/>
    <path d="{spark}" fill="none" stroke="{T.ACCENT}" stroke-width="2.2"
          stroke-linecap="round" stroke-linejoin="round" class="pv-line"/>
  </svg>
  <div class="pv-meter">
    <div class="pv-meter-label"><span>Sentiment</span><span class="pv-pos">+0.34</span></div>
    <div class="pv-track"><div class="pv-fill"></div><div class="pv-dot"></div></div>
  </div>
  <div class="pv-tiles">
    <div class="pv-tile"><span>7D avg</span><b>$326.60</b></div>
    <div class="pv-tile"><span>Volatility</span><b>21.1%</b></div>
    <div class="pv-tile"><span>Lean</span><b class="pv-pos">Bullish</b></div>
  </div>
</div>"""



# --------------------------------------------------------------------------
# Section illustrations
# --------------------------------------------------------------------------
# One per section, each drawing that section's actual idea rather than
# generic imagery. Pure SVG: crisp at any size, no external assets, and
# they animate when their section scrolls into view.

_LBL = "font-family:Inter,sans-serif;font-size:11px;font-weight:600;letter-spacing:.08em"


def _art_problem() -> str:
    """Half the story: price is visible, the 'why' behind it isn't."""
    a, t3 = T.ACCENT, T.TEXT_3
    line = "M20 210 L60 196 L100 214 L140 170 L180 182"
    ghost = "M180 182 L220 150 L260 162 L300 118 L340 132 L380 96"
    chips = ""
    for i, (x, y) in enumerate([(232, 206), (300, 176), (248, 60), (322, 232)]):
        chips += (
            f"<g class='f{i % 3 + 1}'>"
            f"<rect x='{x}' y='{y}' width='62' height='30' rx='7' "
            f"fill='rgba(255,255,255,0.04)' stroke='rgba(255,255,255,0.10)'/>"
            f"<rect x='{x + 9}' y='{y + 9}' width='30' height='3' rx='1.5' fill='rgba(255,255,255,0.22)'/>"
            f"<rect x='{x + 9}' y='{y + 17}' width='44' height='3' rx='1.5' fill='rgba(255,255,255,0.12)'/>"
            f"</g>"
        )
    grid = "".join(
        f"<line x1='20' x2='380' y1='{y}' y2='{y}' stroke='rgba(255,255,255,0.04)'/>"
        for y in (70, 120, 170, 220, 260)
    )
    return f"""
<svg viewBox="0 0 400 290" fill="none">
  {grid}
  <rect x="200" y="20" width="190" height="258" rx="12" fill="rgba(139,92,246,0.05)"/>
  <line x1="200" x2="200" y1="20" y2="278" stroke="rgba(255,255,255,0.16)" stroke-dasharray="4 5"/>
  <text x="24" y="40" fill="{a}" style="{_LBL}">PRICE</text>
  <text x="214" y="40" fill="{T.VIOLET}" style="{_LBL}">WHY?</text>
  <path d="{line} L180 278 L20 278 Z" fill="rgba(79,139,255,0.10)"/>
  <path class="art-draw" d="{line}" stroke="{a}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="{ghost}" stroke="{t3}" stroke-width="1.6" stroke-dasharray="3 6" stroke-linecap="round"/>
  <circle cx="180" cy="182" r="5" fill="{a}"/>
  <circle cx="180" cy="182" r="12" fill="none" stroke="{a}" opacity=".5" class="ping"/>
  {chips}
</svg>"""


def _art_combine() -> str:
    """Two data worlds overlapping into one read."""
    return f"""
<svg viewBox="0 0 400 290" fill="none">
  <defs>
    <radialGradient id="cA"><stop offset="0%" stop-color="{T.ACCENT}" stop-opacity=".55"/>
      <stop offset="100%" stop-color="{T.ACCENT}" stop-opacity=".04"/></radialGradient>
    <radialGradient id="cB"><stop offset="0%" stop-color="{T.BULLISH}" stop-opacity=".5"/>
      <stop offset="100%" stop-color="{T.BULLISH}" stop-opacity=".04"/></radialGradient>
  </defs>
  <g class="drawL"><circle cx="152" cy="145" r="96" fill="url(#cA)" stroke="rgba(79,139,255,.55)"/></g>
  <g class="drawR"><circle cx="248" cy="145" r="96" fill="url(#cB)" stroke="rgba(0,196,106,.5)"/></g>
  <text x="96"  y="150" fill="{T.TEXT}" style="{_LBL}">DATA</text>
  <text x="258" y="150" fill="{T.TEXT}" style="{_LBL}">MOOD</text>
  <g transform="translate(174 128)" class="glow">
    <rect width="52" height="34" rx="10" fill="{T.CANVAS}" stroke="rgba(255,255,255,.18)"/>
    <g transform="translate(9 9) scale(.54)">{T.logo_mark_svg(30, T.TEXT).replace("display:block", "display:inline")}</g>
  </g>
  <path class="art-draw" d="M58 62 L82 54 L100 66 L124 40" stroke="{T.ACCENT}" stroke-width="2" stroke-linecap="round"/>
  <path class="art-draw" d="M290 232 L310 222 L326 238 L350 214" stroke="{T.BULLISH}" stroke-width="2" stroke-linecap="round"/>
</svg>"""


def _art_views() -> str:
    """The same read at two levels of detail."""
    bars = "".join(
        f"<rect x='{48 + i * 17}' y='{206 - h}' width='10' height='{h}' rx='2' "
        f"fill='{T.BULLISH if i % 3 else T.BEARISH}' opacity='.75'/>"
        for i, h in enumerate([18, 30, 14, 36, 24, 42, 20, 32])
    )
    rows = "".join(
        f"<rect x='44' y='{226 + i * 13}' width='{150 - i * 26}' height='4' rx='2' fill='rgba(255,255,255,.14)'/>"
        for i in range(3)
    )
    return f"""
<svg viewBox="0 0 400 290" fill="none">
  <g class="f1">
    <rect x="28" y="36" width="206" height="228" rx="14" fill="rgba(255,255,255,0.035)" stroke="rgba(139,92,246,.45)"/>
    <text x="44" y="62" fill="{T.VIOLET}" style="{_LBL}">DETAILED</text>
    <path class="art-draw" d="M44 142 L72 128 L96 136 L124 104 L150 114 L178 86 L216 94"
          stroke="{T.ACCENT}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    <line x1="44" x2="216" y1="160" y2="160" stroke="rgba(255,255,255,.06)"/>
    {bars}
    {rows}
  </g>
  <g class="f2">
    <rect x="258" y="58" width="116" height="206" rx="20" fill="rgba(255,255,255,0.035)" stroke="rgba(34,211,238,.5)"/>
    <rect x="300" y="68" width="32" height="5" rx="2.5" fill="rgba(255,255,255,.18)"/>
    <text x="274" y="100" fill="{T.CYAN}" style="{_LBL}">SIMPLE</text>
    <path d="M292 172 L316 132 L340 172" stroke="{T.BULLISH}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <line x1="316" x2="316" y1="136" y2="196" stroke="{T.BULLISH}" stroke-width="5" stroke-linecap="round"/>
    <rect x="274" y="222" width="84" height="4" rx="2" fill="rgba(255,255,255,.1)"/>
    <rect x="274" y="222" width="56" height="4" rx="2" fill="{T.BULLISH}"/>
    <rect x="274" y="236" width="70" height="4" rx="2" fill="rgba(255,255,255,.14)"/>
  </g>
</svg>"""


def _art_trust() -> str:
    """A guarded core with the three commitments orbiting it."""
    chips = [
        ("ALWAYS CITED", 44, 58, T.ACCENT),
        ("CLEARLY LABELED", 226, 70, T.CYAN),
        ("NO PRICE TARGETS", 118, 238, T.AMBER),
    ]
    chip_svg = "".join(
        f"<g class='f{i + 1}'><rect x='{x}' y='{y}' width='{len(s) * 7.4 + 24:.0f}' height='26' rx='13' "
        f"fill='{T.CANVAS}' stroke='{c}' stroke-opacity='.55'/>"
        f"<circle cx='{x + 13}' cy='{y + 13}' r='3' fill='{c}'/>"
        f"<text x='{x + 22}' y='{y + 17}' fill='{T.TEXT_2}' style='{_LBL};font-size:9.5px'>{s}</text></g>"
        for i, (s, x, y, c) in enumerate(chips)
    )
    return f"""
<svg viewBox="0 0 400 290" fill="none">
  <defs>
    <radialGradient id="sh"><stop offset="0%" stop-color="{T.AMBER}" stop-opacity=".32"/>
      <stop offset="100%" stop-color="{T.AMBER}" stop-opacity="0"/></radialGradient>
  </defs>
  <circle cx="200" cy="148" r="110" fill="url(#sh)"/>
  <circle cx="200" cy="148" r="92" stroke="rgba(255,255,255,.08)" stroke-dasharray="3 7" class="spin"/>
  <circle cx="200" cy="148" r="62" stroke="rgba(255,255,255,.05)"/>
  <path d="M200 100 L236 116 V144 C236 166 220 182 200 188 C180 182 164 166 164 144 V116 Z"
        fill="rgba(255,176,32,.10)" stroke="{T.AMBER}" stroke-width="2.2" stroke-linejoin="round"/>
  <path class="art-draw" d="M184 144 L196 156 L218 132" stroke="{T.AMBER}" stroke-width="3"
        stroke-linecap="round" stroke-linejoin="round"/>
  {chip_svg}
</svg>"""


def _art(svg: str, delay: str = "r2") -> str:
    return f"<div class='art elev r {delay}'>{svg}</div>"


def _css() -> str:
    return f"""
{T.BASE_CSS}
{T.ATMOSPHERE_CSS}

.wrap {{ max-width:1180px; margin:0 auto; padding:0 56px; position:relative; z-index:2; }}
section {{ position:relative; overflow:hidden; }}

/* ---------- header ---------- */
.nav {{ position:absolute; top:0; left:0; right:0; z-index:5; padding:30px 0; }}

/* ---------- hero ---------- */
.hero {{ padding:128px 0 78px; }}
.hero-grid {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr);
              gap:56px; align-items:center; }}
@media (max-width:980px) {{
  .hero-grid {{ grid-template-columns:1fr; gap:48px; }}
  .wrap {{ padding:0 28px; }}
}}
.hero h1 {{ margin:22px 0 0; font-size:clamp(40px,5.4vw,66px); }}
.hero .sub {{ max-width:48ch; margin-top:24px; font-size:18px; }}
.hero .cue {{
  margin-top:44px; display:flex; align-items:center; gap:11px; font-size:11px;
  font-weight:600; letter-spacing:0.14em; text-transform:uppercase; color:{T.TEXT_3};
}}
.hero .cue i {{ display:block; width:1px; height:24px;
  background:linear-gradient(180deg,{T.BORDER_HI},transparent);
  animation:cue 2.1s {T.EASE} infinite; }}
@keyframes cue {{ 0%,100%{{opacity:.3;transform:translateY(0)}} 50%{{opacity:1;transform:translateY(5px)}} }}

/* ---------- hero product preview ---------- */
.pv-wrap {{ position:relative; animation:floaty 7s ease-in-out infinite; }}
.pv-glow {{
  position:absolute; inset:14% 8% 4% 8%; border-radius:50%; filter:blur(58px);
  background:radial-gradient(circle,rgba(79,139,255,0.42),transparent 70%);
  z-index:0; animation:pulseGlow 6s ease-in-out infinite;
}}
.preview {{
  position:relative; z-index:1; border-radius:18px; padding:20px 20px 18px;
  backdrop-filter:blur(12px);
}}
.pv-top {{ display:flex; justify-content:space-between; align-items:center; }}
.pv-chip {{
  display:inline-flex; align-items:center; gap:7px; font-size:12px; font-weight:600;
  letter-spacing:0.02em; color:{T.TEXT}; background:rgba(255,255,255,0.06);
  border:1px solid rgba(255,255,255,0.09); padding:5px 10px; border-radius:7px;
}}
.pv-sample {{
  font-size:9.5px; font-weight:700; letter-spacing:0.13em; text-transform:uppercase;
  color:{T.TEXT_3}; border:1px solid {T.BORDER_HI}; padding:3px 7px; border-radius:5px;
}}
.pv-price {{ display:flex; align-items:baseline; gap:11px; margin:18px 0 4px; }}
.pv-num {{ font-size:34px; font-weight:600; letter-spacing:-0.03em; color:{T.TEXT}; }}
.pv-delta {{ font-size:14px; font-weight:600; color:{T.BULLISH}; }}
.pv-pos {{ color:{T.BULLISH}; }}
.pv-spark {{ width:100%; height:96px; display:block; margin:6px 0 4px; }}
.pv-line {{ stroke-dasharray:900; stroke-dashoffset:900;
            animation:draw 2.6s {T.EASE} .5s forwards; }}
.pv-area {{ opacity:0; animation:fadeIn 1.4s {T.EASE} 1.6s forwards; }}
@keyframes draw {{ to {{ stroke-dashoffset:0; }} }}
@keyframes fadeIn {{ to {{ opacity:1; }} }}
.pv-meter {{ margin:12px 0 16px; }}
.pv-meter-label {{ display:flex; justify-content:space-between; font-size:11px;
  font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:{T.TEXT_3};
  margin-bottom:9px; }}
.pv-track {{ position:relative; height:3px; border-radius:2px; background:rgba(255,255,255,0.08); }}
.pv-fill {{ height:3px; border-radius:2px; width:0;
  background:linear-gradient(90deg,transparent,{T.BULLISH});
  animation:grow 1.6s {T.EASE} 1.4s forwards; }}
@keyframes grow {{ to {{ width:67%; }} }}
.pv-dot {{ position:absolute; top:-4px; left:0; width:2px; height:11px; border-radius:1px;
  background:{T.BULLISH}; box-shadow:0 0 10px {T.BULLISH};
  animation:move 1.6s {T.EASE} 1.4s forwards; }}
@keyframes move {{ to {{ left:67%; }} }}
.pv-tiles {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }}
.pv-tile {{ background:rgba(255,255,255,0.035); border:1px solid rgba(255,255,255,0.06);
  border-radius:9px; padding:10px 11px; }}
.pv-tile span {{ display:block; font-size:9.5px; font-weight:600; letter-spacing:0.1em;
  text-transform:uppercase; color:{T.TEXT_3}; margin-bottom:5px; }}
.pv-tile b {{ font-size:14px; font-weight:600; color:{T.TEXT}; letter-spacing:-0.01em; }}

/* ---------- marquee ---------- */
.marquee {{ position:relative; z-index:2; border-top:1px solid {T.BORDER};
  border-bottom:1px solid {T.BORDER}; padding:16px 0; overflow:hidden;
  background:rgba(255,255,255,0.012); }}
.marquee-track {{ display:flex; gap:38px; width:max-content;
  animation:marquee 46s linear infinite; }}
.marquee:hover .marquee-track {{ animation-play-state:paused; }}
.tick {{ display:inline-flex; align-items:baseline; gap:8px; white-space:nowrap; }}
.tick b {{ font-size:13px; font-weight:600; color:{T.TEXT_2}; letter-spacing:0.02em; }}
.tick span {{ font-size:12px; color:{T.TEXT_3}; }}
.marquee::before, .marquee::after {{
  content:''; position:absolute; top:0; bottom:0; width:120px; z-index:3; pointer-events:none;
}}
.marquee::before {{ left:0;  background:linear-gradient(90deg,{T.CANVAS},transparent); }}
.marquee::after  {{ right:0; background:linear-gradient(270deg,{T.CANVAS},transparent); }}

/* ---------- stats ---------- */
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
  background:{T.BORDER}; border:1px solid {T.BORDER}; border-radius:16px;
  overflow:hidden; margin-top:6px; }}
@media (max-width:760px) {{ .stats {{ grid-template-columns:1fr 1fr; }} }}
.stat {{ background:{T.CANVAS}; padding:26px 22px; }}
.stat b {{ display:block; font-size:34px; font-weight:600; letter-spacing:-0.035em;
  color:{T.TEXT}; line-height:1; }}
.stat span {{ display:block; margin-top:9px; font-size:12px; color:{T.TEXT_3}; }}

/* ---------- sections ---------- */
.sec {{ padding:104px 0; border-top:1px solid {T.BORDER}; }}
.grid {{ display:grid; grid-template-columns:minmax(0,5fr) minmax(0,6fr); gap:64px; align-items:center; }}
@media (max-width:820px) {{ .grid {{ grid-template-columns:1fr; gap:26px; }} }}
.idx {{ font-size:11px; font-weight:600; letter-spacing:0.14em; color:{T.TEXT_3}; }}
.lede {{ font-size:19px; color:{T.TEXT}; line-height:1.55; letter-spacing:-0.012em; }}

.r {{ opacity:0; transform:translateY(26px);
      transition:opacity .85s {T.EASE}, transform .85s {T.EASE}; }}
.r.on {{ opacity:1; transform:none; }}
.r2 {{ transition-delay:.09s; }} .r3 {{ transition-delay:.18s; }} .r4 {{ transition-delay:.27s; }}

/* ---------- illustrations ---------- */
.side {{ display:flex; flex-direction:column; }}
.art {{ border-radius:18px; padding:10px; margin-top:26px; position:relative; overflow:hidden; }}
.art svg {{ width:100%; height:auto; display:block; }}
.art .art-draw {{ stroke-dasharray:600; stroke-dashoffset:600; }}
.art.on .art-draw {{ animation:draw 2.2s {T.EASE} .35s forwards; }}
.art .f1, .art .f2, .art .f3 {{ transform-box:fill-box; }}
.art .f1 {{ animation:floaty 6s ease-in-out infinite; }}
.art .f2 {{ animation:floaty 7.5s ease-in-out -2s infinite; }}
.art .f3 {{ animation:floaty 9s ease-in-out -4s infinite; }}
.art .spin {{ transform-box:fill-box; transform-origin:center; animation:spin 48s linear infinite; }}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
.art .ping {{ transform-box:fill-box; transform-origin:center; animation:ping 2.4s ease-out infinite; }}
@keyframes ping {{ 0%{{transform:scale(.6);opacity:.8}} 100%{{transform:scale(2.2);opacity:0}} }}
.art .drawL {{ animation:nudgeR 7s ease-in-out infinite; }}
.art .drawR {{ animation:nudgeL 7s ease-in-out infinite; }}
@keyframes nudgeR {{ 0%,100%{{transform:translateX(-10px)}} 50%{{transform:translateX(4px)}} }}
@keyframes nudgeL {{ 0%,100%{{transform:translateX(10px)}}  50%{{transform:translateX(-4px)}} }}
.art .glow {{ filter:drop-shadow(0 0 14px rgba(255,255,255,.18)); }}

/* ---------- cards ---------- */
.pillars {{ display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:34px; }}
@media (max-width:820px) {{ .pillars {{ grid-template-columns:1fr; }} }}
.card {{ border-radius:16px; padding:28px 26px; }}
.card h3 {{ margin:16px 0 10px; }}
.card p {{ font-size:15.5px; }}
.ico {{ width:40px; height:40px; border-radius:11px; display:flex; align-items:center;
  justify-content:center; border:1px solid rgba(255,255,255,0.09); }}

/* ---------- steps ---------- */
.steps {{ display:grid; grid-template-columns:repeat(4,1fr); gap:1px; margin-top:44px;
  background:{T.BORDER}; border:1px solid {T.BORDER}; border-radius:16px; overflow:hidden; }}
@media (max-width:900px) {{ .steps {{ grid-template-columns:1fr 1fr; }} }}
@media (max-width:560px) {{ .steps {{ grid-template-columns:1fr; }} }}
.step {{ background:{T.CANVAS}; padding:28px 24px 32px;
  transition:background .45s {T.EASE}; }}
.step:hover {{ background:{T.SURFACE}; }}
.step .n {{ font-size:12px; font-weight:600; color:{T.ACCENT}; letter-spacing:0.08em; }}
.step h3 {{ font-size:17px; margin:14px 0 9px; }}
.step p {{ font-size:14.5px; line-height:1.58; }}

.note {{ border-left:2px solid {T.ACCENT}; padding:4px 0 4px 22px; margin-top:30px;
  font-size:14.5px; line-height:1.62; color:{T.TEXT_2}; max-width:70ch; }}
.close {{ padding:124px 0 116px; text-align:center; border-top:1px solid {T.BORDER}; }}
.close h2 {{ max-width:18ch; margin:0 auto; }}
"""


def _html() -> str:
    lockup = T.logo_lockup_html(24)
    a, b = T.ACCENT, T.BULLISH
    return f"""<!doctype html><html><head><meta charset="utf-8">{T.GOOGLE_FONTS}
<style>{_css()}</style></head><body>

<div class="nav"><div class="wrap">{lockup}</div></div>

<section class="hero" id="hero">
  {T.aurora(intensity=1.0)}
  <div class="grain"></div>
  <div class="wrap hero-grid">
    <div>
      <div class="eyebrow r">Market Intelligence</div>
      <h1 class="r r2">Where market data meets market mood.</h1>
      <p class="sub r r3">Stock prices tell you what happened. PulseTrade tells you why
         &mdash; and what the market is feeling about it right now.</p>
      <div class="cue r r4"><i></i>Scroll</div>
    </div>
    <div class="pv-wrap r r3">
      <div class="pv-glow"></div>
      {_preview_card()}
    </div>
  </div>
</section>

<div class="marquee"><div class="marquee-track">{_marquee_row()}</div></div>

<section class="sec"><div class="wrap">
  <div class="stats">
    <div class="stat r"><b>39</b><span>Tickers in the default universe</span></div>
    <div class="stat r r2"><b>2</b><span>Independent data sources</span></div>
    <div class="stat r r3"><b>30</b><span>Day outlook horizon</span></div>
    <div class="stat r r4"><b>2</b><span>Views &mdash; detailed and simple</span></div>
  </div>
</div></section>

<section class="sec">{T.aurora(intensity=0.45)}<div class="wrap grid">
  <div class="side"><div class="idx r">01 &nbsp;/&nbsp; The Problem</div>{_art(_art_problem())}</div>
  <div>
    <h2 class="r r2">Numbers only tell<br>half the story.</h2>
    <p class="r r3" style="margin-top:24px;max-width:58ch">Traditional stock tools show you charts
      and numbers. But markets don't move on numbers alone &mdash; they move on news, sentiment,
      and momentum. Most investors have no easy way to see both sides of the story in one place.</p>
  </div>
</div></section>

<section class="sec"><div class="wrap grid">
  <div class="side"><div class="idx r">02 &nbsp;/&nbsp; What It Does</div>{_art(_art_combine())}</div>
  <div>
    <div class="lede r r2">PulseTrade combines two things that are usually kept apart.</div>
    <div class="pillars">
      <div class="card elev r r3">
        <div class="ico" style="background:rgba(79,139,255,0.12)">{T.icon('chart', 20, a)}</div>
        <h3>Hard financial data</h3>
        <p>Real-time prices, moving averages, and volatility, pulled directly from the market.</p>
      </div>
      <div class="card elev r r4">
        <div class="ico" style="background:rgba(0,196,106,0.12)">{T.icon('pulse', 20, b)}</div>
        <h3>Live sentiment intelligence</h3>
        <p>An engine that reads current news and discussion about a stock and distills it into a
           clear sentiment score, backed by real cited sources.</p>
      </div>
    </div>
    <p class="r r4" style="margin-top:30px;font-size:15.5px;max-width:62ch">Together they give you a
       fuller picture: not just where a stock has been, but how the world is currently talking about it.</p>
  </div>
</div></section>

<section class="sec">{T.aurora(intensity=0.4)}<div class="wrap">
  <div class="idx r">03 &nbsp;/&nbsp; How It Works</div>
  <h2 class="r r2" style="margin-top:20px;max-width:14ch">Four steps to a clearer read.</h2>
  <div class="steps">
    <div class="step r"><div class="n">01</div><h3>Pick a ticker</h3>
      <p>Historical prices, daily change, and moving averages load instantly.</p></div>
    <div class="step r r2"><div class="n">02</div><h3>Sentiment runs live</h3>
      <p>Recent news and discussion are scored from strongly negative to strongly positive.</p></div>
    <div class="step r r3"><div class="n">03</div><h3>See the lean</h3>
      <p>A bearish&ndash;bullish meter shows where the data points, with the catalysts and risks behind it.</p></div>
    <div class="step r r4"><div class="n">04</div><h3>Read the outlook</h3>
      <p>A plain-language view of where sentiment and momentum are trending over 30 days.</p></div>
  </div>
</div></section>

<section class="sec"><div class="wrap grid">
  <div class="side"><div class="idx r">04 &nbsp;/&nbsp; Built For Everyone</div>{_art(_art_views())}</div>
  <div>
    <h2 class="r r2">Two ways in.</h2>
    <div class="pillars" style="margin-top:32px">
      <div class="card elev r r3">
        <div class="ico" style="background:rgba(139,92,246,0.12)">{T.icon('layers', 20, T.VIOLET)}</div>
        <h3>Detailed</h3>
        <p>Full metrics, sentiment breakdowns, cited sources, and charts &mdash; for digging into the data yourself.</p></div>
      <div class="card elev r r4">
        <div class="ico" style="background:rgba(34,211,238,0.12)">{T.icon('gauge', 20, T.CYAN)}</div>
        <h3>Simple</h3>
        <p>A plain-English summary and a single visual cue, for anyone who just wants to know how a stock is doing right now.</p></div>
    </div>
  </div>
</div></section>

<section class="sec">{T.aurora(intensity=0.35)}<div class="wrap grid">
  <div class="side"><div class="idx r">05 &nbsp;/&nbsp; Built Responsibly</div>{_art(_art_trust())}</div>
  <div>
    <h2 class="r r2">Information, not advice.</h2>
    <p class="r r3" style="margin-top:24px;max-width:58ch">PulseTrade never predicts exact prices and
       never tells you to buy or sell. It reports what the data and sentiment currently show &mdash;
       clearly labeled, always cited.</p>
    <div class="note r r4">AI-generated outlook based on sentiment and trend data &mdash; not financial
       advice. This is not a recommendation to buy or sell.</div>
  </div>
</div></section>

<section class="close">{T.aurora(intensity=0.7)}<div class="wrap">
  <div class="eyebrow r" style="margin-bottom:22px">Get Started</div>
  <h2 class="r r2">See what the market's really saying.</h2>
  <p class="r r3" style="max-width:44ch;margin:20px auto 0">Create an account and pull your first
     read in under a minute.</p>
</div></section>

<script>
  var io = new IntersectionObserver(function(es){{
    es.forEach(function(e){{ if(e.isIntersecting){{ e.target.classList.add('on'); io.unobserve(e.target); }} }});
  }}, {{ threshold:0.12, rootMargin:'0px 0px -6% 0px' }});
  document.querySelectorAll('.r').forEach(function(el){{ io.observe(el); }});

  // Scroll-coupled drift on the background washes. The iframe doesn't
  // scroll itself, so we read the parent's scroll position instead.
  (function () {{
    var blobs = document.querySelectorAll('.aurora .blob');
    var frame = window.frameElement;
    function onScroll() {{
      if (!frame) return;
      var y = -frame.getBoundingClientRect().top;
      for (var i = 0; i < blobs.length; i++) {{
        // translate, never margin: transforms don't affect layout, so this
        // can't change scrollHeight and feed back into the autofit resizer.
        blobs[i].style.setProperty('--py', (y * (0.02 + (i % 3) * 0.015)) + 'px');
      }}
    }}
    try {{
      window.parent.addEventListener('scroll', onScroll, true);
      onScroll();
    }} catch (e) {{}}
  }})();
</script>
{T.AUTOFIT_JS}
</body></html>"""


# First-paint height only — the page resizes its own frame (see T.AUTOFIT_JS).
LANDING_HEIGHT = 3400


def render_landing_page() -> None:
    components.html(_html(), height=LANDING_HEIGHT, scrolling=False)

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("Get Started", key="landing_cta", type="primary", width="stretch"):
            st.session_state["page"] = "login"
            st.rerun()
