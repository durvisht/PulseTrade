"""PulseTrade — design system.

Single source of truth for color, type, spacing, the logo, and chart
styling. Every surface (landing, login, dashboard) pulls from here so the
product reads as one designed system rather than three separate pages.

Design principles:
  1. Near-monochrome canvas. One interactive accent (blue). Green/red are
     reserved *exclusively* for market semantics — never decoration.
  2. Typography carries the hierarchy. Tight tracking on display sizes,
     tabular figures on every number.
  3. Space is structural. A 4px rhythm, with large negative space at
     section boundaries.
  4. Motion is subtle and physical — one easing curve, used everywhere.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Color
# --------------------------------------------------------------------------

CANVAS = "#08090B"
SURFACE = "#0E1013"
SURFACE_2 = "#15181C"
BORDER = "#1C2026"
BORDER_HI = "#282D35"

TEXT = "#F7F8F8"
TEXT_2 = "#9CA3AE"
TEXT_3 = "#646B76"

ACCENT = "#4F8BFF"
ACCENT_DIM = "#2B5FC4"
ACCENT_GLOW = "rgba(79,139,255,0.16)"

# Secondary hues. Used for atmosphere (aurora, glows, category accents) and
# for distinguishing data series — never as flat decoration on surfaces.
CYAN = "#22D3EE"
VIOLET = "#8B5CF6"
AMBER = "#FFB020"

BULLISH = "#00C46A"
BEARISH = "#FF453A"
NEUTRAL = "#8A929E"

FONT_STACK = (
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
)
EASE = "cubic-bezier(0.16, 1, 0.3, 1)"

GOOGLE_FONTS = (
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>"
)

# --------------------------------------------------------------------------
# Logo
# --------------------------------------------------------------------------
# An ascending monoline pulse: it reads as a heartbeat (market mood) and as
# a price chart (market data) at once — the product thesis in one stroke.
# It deliberately exits higher than it enters. Single path, round joins,
# legible down to 16px, and recolorable via currentColor.

_PULSE_PATH = "M3 19 L15 19 L23 7 L32 25 L41 13 L61 5"


def logo_mark_svg(height: int = 28, color: str = ACCENT, stroke: float = 3.0) -> str:
    """The mark on its own — header, favicon, compact contexts."""
    width = round(height * 64 / 32)
    return (
        f"<svg width='{width}' height='{height}' viewBox='0 0 64 32' fill='none' "
        f"xmlns='http://www.w3.org/2000/svg' style='display:block'>"
        f"<path d='{_PULSE_PATH}' stroke='{color}' stroke-width='{stroke}' "
        f"stroke-linecap='round' stroke-linejoin='round'/></svg>"
    )


def logo_lockup_html(height: int = 26, color: str = TEXT, mark_color: str = ACCENT,
                     size: float = 1.0) -> str:
    """Mark + wordmark. Kept as HTML so CSS handles the type properly."""
    fs = round(17 * size)
    gap = round(10 * size)
    return (
        f"<span style=\"display:inline-flex;align-items:center;gap:{gap}px;\">"
        f"{logo_mark_svg(height, mark_color)}"
        f"<span style=\"font-family:{FONT_STACK};font-weight:600;font-size:{fs}px;"
        f"letter-spacing:-0.022em;color:{color};line-height:1;white-space:nowrap;\">"
        f"PulseTrade</span></span>"
    )


# --------------------------------------------------------------------------
# Base CSS — shared by every embedded HTML surface
# --------------------------------------------------------------------------

BASE_CSS = f"""
*, *::before, *::after {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; overflow:hidden; }}
::-webkit-scrollbar {{ display:none; }}
body {{
  background:{CANVAS};
  color:{TEXT};
  font-family:{FONT_STACK};
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
  font-variant-numeric:tabular-nums;
}}
.eyebrow {{
  font-size:11px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase;
  color:{TEXT_3};
}}
h1,h2,h3 {{ margin:0; font-weight:600; letter-spacing:-0.035em; line-height:1.04; }}
h1 {{ font-size:clamp(44px, 7vw, 82px); }}
h2 {{ font-size:clamp(30px, 4vw, 46px); letter-spacing:-0.03em; }}
h3 {{ font-size:21px; letter-spacing:-0.02em; }}
p  {{ margin:0; font-size:17px; line-height:1.62; color:{TEXT_2}; }}
.rule {{ height:1px; background:{BORDER}; border:0; margin:0; }}
"""

# --------------------------------------------------------------------------
# Atmosphere — depth, color, motion
# --------------------------------------------------------------------------
# The canvas stays near-black; color arrives as *light* (blurred radial
# washes behind content) rather than as painted surfaces. That keeps text
# contrast intact while giving the page depth, and it's cheap to animate.


def aurora(seed: int = 0, intensity: float = 1.0) -> str:
    """A drifting field of blurred color behind a section."""
    a = 0.30 * intensity
    b = 0.24 * intensity
    c = 0.20 * intensity
    return (
        f"<div class='aurora' aria-hidden='true'>"
        f"<span class='blob b1' style='background:radial-gradient(circle,"
        f"rgba(79,139,255,{a}),transparent 68%)'></span>"
        f"<span class='blob b2' style='background:radial-gradient(circle,"
        f"rgba(139,92,246,{b}),transparent 68%)'></span>"
        f"<span class='blob b3' style='background:radial-gradient(circle,"
        f"rgba(34,211,238,{c}),transparent 68%)'></span>"
        f"</div>"
    )


ATMOSPHERE_CSS = f"""
.aurora {{
  position:absolute; inset:0; overflow:hidden; pointer-events:none; z-index:0;
}}
.aurora .blob {{
  position:absolute; display:block; border-radius:50%;
  filter:blur(70px); will-change:transform;
}}
.aurora .blob {{ --py:0px; }}
.b1 {{ width:560px; height:560px; top:-160px; left:-120px;  animation:drift1 22s ease-in-out infinite; }}
.b2 {{ width:620px; height:620px; top:-40px;  right:-180px; animation:drift2 27s ease-in-out infinite; }}
.b3 {{ width:460px; height:460px; bottom:-220px; left:34%;  animation:drift3 31s ease-in-out infinite; }}
@keyframes drift1 {{ 0%,100%{{transform:translate(0,var(--py)) scale(1)}}  50%{{transform:translate(70px,calc(var(--py) + 50px)) scale(1.12)}} }}
@keyframes drift2 {{ 0%,100%{{transform:translate(0,var(--py)) scale(1)}}  50%{{transform:translate(-60px,calc(var(--py) + 70px)) scale(1.08)}} }}
@keyframes drift3 {{ 0%,100%{{transform:translate(0,var(--py)) scale(1)}}  50%{{transform:translate(40px,calc(var(--py) - 60px)) scale(1.15)}} }}

/* a fine grain over the whole surface stops large dark areas banding */
.grain {{
  position:absolute; inset:0; pointer-events:none; z-index:1; opacity:0.16;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E");
}}

/* elevation: a lit top edge + a real cast shadow reads as depth */
.elev {{
  background:linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.012));
  border:1px solid rgba(255,255,255,0.075);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.06), 0 16px 40px rgba(0,0,0,0.5);
  transition:transform .5s {EASE}, box-shadow .5s {EASE}, border-color .5s {EASE};
}}
.elev:hover {{
  transform:translateY(-4px);
  border-color:rgba(79,139,255,0.42);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.09),
             0 26px 60px rgba(0,0,0,0.6), 0 0 44px rgba(79,139,255,0.14);
}}

@keyframes floaty {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-12px)}} }}
@keyframes shimmer {{ 0%{{background-position:-380px 0}} 100%{{background-position:380px 0}} }}
@keyframes marquee {{ from{{transform:translateX(0)}} to{{transform:translateX(-50%)}} }}
@keyframes pulseGlow {{ 0%,100%{{opacity:.5}} 50%{{opacity:1}} }}
"""


# --------------------------------------------------------------------------
# Icons — 1.5px monoline, inherit color via currentColor
# --------------------------------------------------------------------------

_ICONS = {
    "chart": "M3 17.5 L9 11 L13 15 L21 6.5",
    "pulse": "M2 12 H7 L9.5 6 L13 18 L15.5 12 H22",
    "layers": "M12 3 L21 8 L12 13 L3 8 Z M3 13.5 L12 18.5 L21 13.5",
    "shield": "M12 3 L20 6.5 V12 C20 16.5 16.5 19.8 12 21 C7.5 19.8 4 16.5 4 12 V6.5 Z",
    "search": "M11 19 A8 8 0 1 1 11 3 A8 8 0 0 1 11 19 Z M17 17 L21.5 21.5",
    "gauge": "M4.5 18 A9 9 0 1 1 19.5 18 M12 12 L16 8.5",
}


def icon(name: str, size: int = 20, color: str = ACCENT, stroke: float = 1.6) -> str:
    d = _ICONS.get(name, _ICONS["chart"])
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' "
        f"xmlns='http://www.w3.org/2000/svg'><path d='{d}' stroke='{color}' "
        f"stroke-width='{stroke}' stroke-linecap='round' stroke-linejoin='round'/></svg>"
    )


# --------------------------------------------------------------------------
# Plotly — a restrained chart theme
# --------------------------------------------------------------------------


def chart_layout(**overrides) -> dict:
    """Finance-grade chart chrome: no chartjunk, hairline horizontal grid
    only, muted axis type, unified dark hover."""
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=11, color=TEXT_3),
        margin=dict(l=8, r=8, t=28, b=8),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=SURFACE_2,
            bordercolor=BORDER_HI,
            font=dict(family="Inter, sans-serif", size=12, color=TEXT),
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=TEXT_3),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.045)",
            zeroline=False,
            showline=False,
            ticks="",
            tickfont=dict(size=11, color=TEXT_3),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.0,
            xanchor="left",
            x=0,
            font=dict(size=11, color=TEXT_2),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    layout.update(overrides)
    return layout


CHART_CONFIG = {"displayModeBar": False, "scrollZoom": False}


# --------------------------------------------------------------------------
# Meters — thin, precise, HTML. Deliberately not Plotly gauges: a hairline
# meter reads as designed instrumentation; a speedometer reads as clip art.
# --------------------------------------------------------------------------
# NOTE: these MUST stay single-line strings with no leading indentation.
# A whitespace-only line breaks CommonMark's HTML-block parsing inside
# st.markdown and the whole thing renders as a literal code block.


def meter_html(value: float, left: str, right: str, color: str,
               track: str = "rgba(255,255,255,0.07)") -> str:
    """A -1..1 value rendered as a hairline meter with a precise marker."""
    pct = max(0.0, min(100.0, (value + 1) / 2 * 100))
    return (
        f"<div style=\"width:100%\">"
        f"<div style=\"position:relative;height:3px;border-radius:2px;background:{track};\">"
        f"<div style=\"position:absolute;left:0;top:0;height:3px;width:{pct}%;"
        f"border-radius:2px;background:linear-gradient(90deg,transparent,{color});opacity:0.55;\"></div>"
        f"<div style=\"position:absolute;left:{pct}%;top:-4px;width:2px;height:11px;"
        f"border-radius:1px;background:{color};transform:translateX(-1px);"
        f"box-shadow:0 0 10px {color};\"></div></div>"
        f"<div style=\"display:flex;justify-content:space-between;margin-top:9px;"
        f"font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:{TEXT_3};\">"
        f"<span>{left}</span><span>{right}</span></div></div>"
    )


# --------------------------------------------------------------------------
# Streamlit chrome — injected once from app.py.
#
# NOTE: this string is deliberately flush-left. Streamlit runs st.markdown
# through CommonMark first, and any line indented 4+ spaces becomes an
# indented *code block* — which renders the CSS as visible text instead of
# applying it. Keep every line at column 0.
# --------------------------------------------------------------------------


def streamlit_css() -> str:
    """One <style> block. Deliberately a single type-1 HTML block with the
    font pulled in via @import rather than <link> tags:

      * A <link> opens a CommonMark *type-6* HTML block, which terminates at
        the first blank line — after which indented CSS is parsed as an
        indented code block and rendered as visible text.
      * A <style> opens a *type-1* block, which runs to the closing tag and
        is immune to both blank lines and indentation.

    Every line is also flush-left as belt-and-braces.
    """
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp, button, input, select, textarea {{
font-family: {FONT_STACK} !important;
-webkit-font-smoothing: antialiased;
}}
.stApp {{ background: {CANVAS}; }}
[data-testid="stAppViewContainer"] {{ background: {CANVAS}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2.4rem; max-width: 1480px; }}

/* numbers everywhere read as instrumentation */
[data-testid="stMetricValue"], .pt-num {{ font-variant-numeric: tabular-nums; }}

/* ---------------- sidebar ---------------- */
section[data-testid="stSidebar"] {{
background: {SURFACE};
border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] > div {{ padding-top: 22px; }}
section[data-testid="stSidebar"] hr {{ border-color: {BORDER}; margin: 18px 0; }}
section[data-testid="stSidebar"] label {{
font-size: 11px !important; font-weight: 600 !important;
letter-spacing: 0.08em; text-transform: uppercase; color: {TEXT_3} !important;
}}

/* inputs */
[data-baseweb="select"] > div, [data-baseweb="base-input"] {{
background: {SURFACE_2} !important;
border: 1px solid {BORDER} !important;
border-radius: 9px !important;
transition: border-color .2s {EASE};
}}
[data-baseweb="select"] > div:hover, [data-baseweb="base-input"]:hover {{
border-color: {BORDER_HI} !important;
}}
input {{ color: {TEXT} !important; font-size: 14px !important; }}
input::placeholder {{ color: {TEXT_3} !important; opacity: 1; }}

/* ---------------- buttons ---------------- */
.stButton button {{
border-radius: 9px; font-weight: 550; font-size: 14px;
letter-spacing: -0.005em; transition: all .22s {EASE};
border: 1px solid {BORDER_HI}; background: transparent; color: {TEXT_2};
}}
.stButton button:hover {{
border-color: {TEXT_3}; color: {TEXT}; background: {SURFACE_2};
}}
.stButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button {{
background: {ACCENT}; border-color: {ACCENT}; color: #fff; font-weight: 600;
}}
.stButton button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button:hover {{
background: #3F7BEF; border-color: #3F7BEF; color: #fff;
box-shadow: 0 5px 22px {ACCENT_GLOW};
}}
[data-testid="stFormSubmitButton"] button {{
border-radius: 9px; font-size: 14px; letter-spacing: -0.005em;
}}

/* segmented control (login mode switch) */
[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
background: {SURFACE_2} !important; color: {TEXT} !important;
border-color: {BORDER_HI} !important;
}}

/* ---------------- tabs ---------------- */
.stTabs [data-baseweb="tab-list"] {{
gap: 4px; border-bottom: 1px solid {BORDER}; background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
height: 40px; padding: 0 16px; background: transparent;
font-size: 14px; font-weight: 550; color: {TEXT_3};
}}
.stTabs [aria-selected="true"] {{ color: {TEXT} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {ACCENT}; height: 2px; }}

/* ---------------- metrics ---------------- */
div[data-testid="stMetric"] {{
background: {SURFACE}; border: 1px solid {BORDER};
border-radius: 13px; padding: 17px 19px;
}}
div[data-testid="stMetric"] label {{
font-size: 11px !important; font-weight: 600 !important;
letter-spacing: 0.08em; text-transform: uppercase; color: {TEXT_3} !important;
}}
[data-testid="stMetricValue"] {{
font-size: 25px !important; font-weight: 600 !important;
letter-spacing: -0.02em; color: {TEXT} !important;
}}

/* ---------------- PulseTrade primitives ---------------- */
.pt-card {{
background: {SURFACE}; border: 1px solid {BORDER};
border-radius: 13px; padding: 19px 21px; height: 100%;
transition: border-color .3s {EASE};
}}
.pt-card:hover {{ border-color: {BORDER_HI}; }}
.pt-label {{
font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
text-transform: uppercase; color: {TEXT_3}; margin-bottom: 11px;
}}
.pt-value {{
font-size: 29px; font-weight: 600; letter-spacing: -0.028em;
color: {TEXT}; line-height: 1; font-variant-numeric: tabular-nums;
}}
.pt-delta {{
display: inline-block; margin-top: 11px; font-size: 13px; font-weight: 600;
letter-spacing: -0.01em; font-variant-numeric: tabular-nums;
}}
.pt-panel {{
background: {SURFACE}; border: 1px solid {BORDER};
border-radius: 13px; padding: 24px 24px 20px;
}}
.pt-h {{
font-size: 11px; font-weight: 600; letter-spacing: 0.1em;
text-transform: uppercase; color: {TEXT_3}; margin: 0 0 14px;
}}
.pt-title {{
font-size: 19px; font-weight: 600; letter-spacing: -0.022em;
color: {TEXT}; margin: 0 0 4px;
}}
.pt-body {{ font-size: 14.5px; line-height: 1.62; color: {TEXT_2}; }}
.pt-note {{
border-left: 2px solid {ACCENT}; padding: 3px 0 3px 16px; margin-top: 16px;
font-size: 12.5px; line-height: 1.6; color: {TEXT_3};
}}
.pt-cite {{ font-size: 13px; line-height: 1.5; margin-bottom: 9px; }}
.pt-cite a {{ color: {TEXT_2}; text-decoration: none; }}
.pt-cite a:hover {{ color: {ACCENT}; }}
.pt-tick {{
font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
color: {TEXT_3}; font-variant-numeric: tabular-nums;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 13px !important; }}

/* ---------------- atmosphere ---------------- */
/* Color arrives as light behind the UI, not paint on it — so text contrast
   is untouched while the page gains depth. Fixed so it doesn't scroll. */
.stApp::before {{
content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
background:
radial-gradient(820px 560px at 10% -8%,  rgba(79,139,255,0.22), transparent 60%),
radial-gradient(760px 520px at 94% 0%,   rgba(139,92,246,0.17), transparent 60%),
radial-gradient(680px 500px at 48% 106%, rgba(34,211,238,0.12), transparent 60%);
animation: appDrift 26s ease-in-out infinite;
}}
@keyframes appDrift {{
0%,100% {{ transform:translate3d(0,0,0) scale(1); }}
50%     {{ transform:translate3d(0,-18px,0) scale(1.04); }}
}}
section.stMain, [data-testid="stAppViewContainer"] > .main {{ position:relative; z-index:1; }}
section[data-testid="stSidebar"] {{ position:relative; z-index:2; }}

/* ---------------- elevation ---------------- */
.pt-card, .pt-panel {{
background:linear-gradient(180deg, rgba(255,255,255,0.042), rgba(255,255,255,0.012));
border:1px solid rgba(255,255,255,0.07);
box-shadow:inset 0 1px 0 rgba(255,255,255,0.055), 0 12px 32px rgba(0,0,0,0.45);
transition:transform .45s {EASE}, box-shadow .45s {EASE}, border-color .45s {EASE};
}}
.pt-card:hover, .pt-panel:hover {{
transform:translateY(-3px);
border-color:rgba(79,139,255,0.34);
box-shadow:inset 0 1px 0 rgba(255,255,255,0.08),
           0 22px 48px rgba(0,0,0,0.55), 0 0 36px rgba(79,139,255,0.11);
}}
div[data-testid="stMetric"] {{
background:linear-gradient(180deg, rgba(255,255,255,0.042), rgba(255,255,255,0.012));
border:1px solid rgba(255,255,255,0.07);
box-shadow:inset 0 1px 0 rgba(255,255,255,0.055), 0 10px 26px rgba(0,0,0,0.4);
transition:transform .45s {EASE}, border-color .45s {EASE};
}}
div[data-testid="stMetric"]:hover {{
transform:translateY(-2px); border-color:rgba(79,139,255,0.3);
}}

/* ---------------- entrance ---------------- */
@keyframes ptRise {{ from {{ opacity:0; transform:translateY(14px); }}
                     to   {{ opacity:1; transform:none; }} }}
.pt-card, .pt-panel, div[data-testid="stMetric"] {{ animation:ptRise .6s {EASE} both; }}

/* ---------------- sidebar ---------------- */
section[data-testid="stSidebar"] {{
background:
radial-gradient(420px 300px at 0% 0%, rgba(79,139,255,0.14), transparent 70%),
radial-gradient(360px 260px at 100% 100%, rgba(139,92,246,0.10), transparent 70%),
{SURFACE} !important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{ padding-top:6px; }}
.sb-brand {{
padding:10px 4px 20px; margin-bottom:6px; border-bottom:1px solid {BORDER};
}}
.sb-tag {{
margin-top:10px; font-size:11px; font-weight:600; letter-spacing:.12em;
text-transform:uppercase; color:{TEXT_3};
}}
.sb-label {{
margin:18px 2px 8px; font-size:10.5px; font-weight:700; letter-spacing:.14em;
text-transform:uppercase; color:{TEXT_3};
}}
.sb-card {{
background:linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015));
border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:13px 14px;
box-shadow:inset 0 1px 0 rgba(255,255,255,0.05);
}}
@keyframes pulseGlow {{ 0%,100%{{opacity:.55}} 50%{{opacity:1}} }}
.sb-dot {{ width:8px; height:8px; border-radius:50%; display:inline-block;
animation:pulseGlow 2.4s ease-in-out infinite; }}
.sb-feat {{ display:flex; gap:12px; align-items:flex-start; padding:10px 0;
border-bottom:1px solid rgba(255,255,255,0.05); font-size:13px; line-height:1.35; color:{TEXT}; }}
.sb-feat:last-child {{ border-bottom:0; }}
.sb-feat b {{ font-weight:600; }}
.sb-feat span span {{ color:{TEXT_3}; font-size:12px; }}
.sb-ico {{ flex:none; width:30px; height:30px; border-radius:9px; display:flex;
align-items:center; justify-content:center;
background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08); }}
.sb-spacer {{ height:20px; }}
.sb-account {{ display:flex; align-items:center; gap:11px; }}
.sb-account b {{ display:block; font-size:13.5px; font-weight:600; color:{TEXT};
white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.sb-email {{ display:block; font-size:11.5px; color:{TEXT_3};
white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.sb-avatar {{ flex:none; width:36px; height:36px; border-radius:50%;
display:flex; align-items:center; justify-content:center;
font-size:15px; font-weight:700; color:#fff;
background:linear-gradient(135deg, {ACCENT}, {VIOLET});
box-shadow:0 0 0 2px rgba(255,255,255,0.08), 0 6px 16px rgba(79,139,255,0.35); }}
.sb-foot {{ margin:18px 2px 6px; font-size:11px; color:{TEXT_3};
display:flex; flex-wrap:wrap; align-items:center; gap:6px; }}
.sb-foot span {{ padding:3px 8px; border-radius:6px; color:{TEXT_2};
background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); }}

/* ---------------- auth ---------------- */
a.pt-google {{
display:flex; align-items:center; justify-content:center; gap:11px;
height:44px; border-radius:9px; text-decoration:none !important;
background:#FFFFFF; color:#1F1F1F !important; font-size:14px; font-weight:600;
border:1px solid #DADCE0; transition:all .22s {EASE};
}}
a.pt-google:hover {{ background:#F2F4F7; box-shadow:0 6px 22px rgba(255,255,255,0.10); }}
.st-key-su_submit button {{ height:44px; margin-top:6px; }}

/* nav buttons: quiet rows, with a lit active state */
section[data-testid="stSidebar"] [class*="st-key-nav_"] button {{
justify-content:flex-start; gap:10px; height:42px; padding:0 14px;
border:1px solid transparent; background:transparent; color:{TEXT_2};
font-weight:550; margin-bottom:-6px;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button > div,
section[data-testid="stSidebar"] .st-key-star_toggle button > div,
section[data-testid="stSidebar"] .st-key-logout_btn button > div {{
justify-content:flex-start; width:100%;
}}
section[data-testid="stSidebar"] .st-key-star_toggle button,
section[data-testid="stSidebar"] .st-key-logout_btn button {{ justify-content:flex-start; padding:0 14px; }}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button:hover {{
background:rgba(255,255,255,0.05); color:{TEXT}; border-color:transparent;
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] {{
background:linear-gradient(90deg, rgba(79,139,255,0.20), rgba(79,139,255,0.04));
border-color:rgba(79,139,255,0.30); color:{TEXT};
box-shadow:inset 3px 0 0 {ACCENT};
}}
section[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"]:hover {{
box-shadow:inset 3px 0 0 {ACCENT}; background:linear-gradient(90deg, rgba(79,139,255,0.26), rgba(79,139,255,0.06));
}}
section[data-testid="stSidebar"] .st-key-analyze_btn button {{
height:44px; background:linear-gradient(90deg, {ACCENT}, {VIOLET});
border:0; box-shadow:0 8px 24px rgba(79,139,255,0.30);
}}
section[data-testid="stSidebar"] .st-key-analyze_btn button:hover {{
filter:brightness(1.08); box-shadow:0 10px 30px rgba(79,139,255,0.45);
}}
section[data-testid="stSidebar"] .st-key-star_toggle button {{ height:40px; }}
section[data-testid="stSidebar"] .st-key-logout_btn button {{ color:{TEXT_3}; }}
section[data-testid="stSidebar"] .st-key-logout_btn button:hover {{ color:{BEARISH}; }}
section[data-testid="stSidebar"] [data-testid="stSegmentedControl"] button {{ flex:1; }}
</style>
"""


# --------------------------------------------------------------------------
# Auto-fit
# --------------------------------------------------------------------------
# components.html() takes a *fixed* pixel height, but content height is
# responsive — so a hardcoded value either clips on narrow viewports or
# leaves dead space on wide ones. These frames are same-origin srcdoc, so
# the document can resize its own frameElement. The height passed from
# Python then only needs to be a reasonable first paint.

AUTOFIT_JS = """
<script>
(function () {
  var last = 0;
  function fit() {
    try {
      var h = document.documentElement.scrollHeight;
      if (Math.abs(h - last) > 2 && window.frameElement) {
        last = h;
        window.frameElement.style.height = h + 'px';
      }
    } catch (e) {}
  }
  fit();
  window.addEventListener('load', fit);
  window.addEventListener('resize', fit);
  if (window.ResizeObserver) new ResizeObserver(fit).observe(document.body);
  setTimeout(fit, 120); setTimeout(fit, 600);
})();
</script>
"""
