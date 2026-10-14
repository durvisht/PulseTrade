"""PulseTrade — AI research & outlook engine.

Wraps the google-genai SDK (Gemini) to turn real news articles (fetched
deterministically from Alpha Vantage in stock_data.py) into an objective
narrative, plus a qualitative 30-day outlook. This module NEVER computes
numeric sentiment or stock metrics itself — the sentiment score is a
relevance-weighted aggregate computed in Python from real per-article
scores; Gemini only writes the qualitative summary/drivers/outlook and
never invents a number or a citation.
"""

from __future__ import annotations

import json
import re
import time

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

MODEL_NAME = "gemini-3.1-flash-lite"
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 6


def _generate_with_retry(client: genai.Client, **kwargs):
    """Call generate_content, retrying on transient errors:
    - 503 'high demand' (common with Gemini during peak load)
    - 429 free-tier per-minute rate limit (short, recoverable window —
      NOT the same as a daily quota exhaustion)
    Kept short (2 retries, 6s) so a real outage fails fast instead of
    stalling the UI for a long time.
    """
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            return client.models.generate_content(**kwargs)
        except ServerError as exc:
            last_error = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(3 * (attempt + 1))
        except ClientError as exc:
            is_rate_limit = getattr(exc, "code", None) == 429
            if not is_rate_limit:
                raise
            last_error = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF_SECONDS)
    raise last_error

SYSTEM_INSTRUCTION = (
    "You are an objective market intelligence analyst. Provide direct, "
    "neutral market summaries. Never refer to yourself, Gemini, AI, or use "
    "self-referential phrases such as 'as an AI', 'Gemini analysis', or "
    "'AI indicates'. Never state a specific price target or percentage "
    "forecast, and never phrase output as a buy/sell recommendation — "
    "describe direction and drivers only, in third-person objective "
    "financial reporting style."
)

# Phrases that must never leak into output. Checked case-insensitively.
_SELF_REFERENTIAL_PATTERNS = [
    r"\bas an ai\b",
    r"\bas a language model\b",
    r"\bgemini(?:'s)? (?:analysis|indicates|suggests|believes|thinks|finds)\b",
    r"\bai analysis\b",
    r"\bai(?:-| )?(?:generated )?indicates\b",
    r"\bi am an ai\b",
    r"\bthis ai\b",
    r"\bas an artificial intelligence\b",
]

_BUY_SELL_PATTERNS = [
    r"\byou should (?:buy|sell|hold)\b",
    r"\bwe recommend (?:buying|selling|holding)\b",
    r"\bconsider buying\b",
    r"\bconsider selling\b",
]


def _sanitize_text(text: str) -> str:
    """Strip/flag stray self-referential or recommendation language."""
    if not text:
        return text
    cleaned = text
    for pattern in _SELF_REFERENTIAL_PATTERNS:
        cleaned = re.sub(pattern, "Market data", cleaned, flags=re.IGNORECASE)
    for pattern in _BUY_SELL_PATTERNS:
        cleaned = re.sub(
            pattern, "data suggests monitoring", cleaned, flags=re.IGNORECASE
        )
    return cleaned


def _sanitize_obj(obj):
    """Recursively sanitize all string values in a parsed JSON object."""
    if isinstance(obj, str):
        return _sanitize_text(obj)
    if isinstance(obj, list):
        return [_sanitize_obj(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _sanitize_obj(v) for k, v in obj.items()}
    return obj


def _extract_json(raw_text: str) -> dict:
    """Pull a JSON object out of a model response, tolerating markdown fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def analyze_sentiment(ticker: str, news_data: dict, api_key: str) -> dict:
    """Turn real, pre-fetched news articles (from Alpha Vantage) into an
    objective narrative. The sentiment score/label are NOT computed here —
    they arrive already-computed in `news_data` (see
    stock_data.get_news_sentiment_raw) and are passed through unchanged.
    Gemini only summarizes and identifies drivers from real article text,
    and citations are the real article titles/URLs — never invented.

    Args:
        news_data: output of stock_data.get_news_sentiment_raw(ticker, ...)

    Returns:
        {
            "sentiment_score": float [-1.0, 1.0],   # pass-through, deterministic
            "sentiment_label": str,                  # pass-through, deterministic
            "top_drivers": [str, str, str],
            "summary": str,
            "citations": [{"title": str, "uri": str}, ...],
        }
    """
    articles = news_data.get("articles", [])

    if not articles:
        return {
            "sentiment_score": news_data.get("sentiment_score", 0.0),
            "sentiment_label": news_data.get("sentiment_label", "Neutral"),
            "top_drivers": [],
            "summary": f"No recent news coverage was found for {ticker}.",
            "citations": [],
        }

    client = genai.Client(api_key=api_key)

    top_articles = articles[:14]
    articles_block = "\n\n".join(
        f"[{i+1}] {a['title']} (source: {a['source']}, "
        f"per-article sentiment: {a['ticker_score']:+.2f}, relevance: {a['relevance']:.2f})\n{a['summary']}"
        for i, a in enumerate(top_articles)
    )

    prompt = f"""The following are real recent news articles about the stock
ticker {ticker}, each with a pre-computed sentiment score you should treat
as ground truth (do not recalculate or contradict these scores):

{articles_block}

The overall aggregate sentiment score across all coverage has already been
computed as {news_data['sentiment_score']:+.2f} ({news_data['sentiment_label']}).

Based ONLY on the articles above, write an in-depth but objective research
note. Respond with ONLY a raw JSON object (no markdown fences) in exactly
this shape:
{{
  "top_drivers": ["<driver 1>", "<driver 2>", "<driver 3>", "<driver 4>"],
  "summary": "<4-5 objective, third-person sentences giving real analytical depth: what is actually happening (specific events/figures from the articles, not vague generalities), why it matters for sentiment direction, and how it reconciles with the aggregate sentiment score above>"
}}

Rules:
- Ground every claim in specific details from the articles (names, figures,
  events) rather than generic filler language.
- Do not simply restate the sentiment label — explain the underlying story.
- Use objective, third-person financial reporting language."""

    response = _generate_with_retry(
        client,
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
        ),
    )

    result = _extract_json(response.text)
    result = _sanitize_obj(result)
    result.setdefault("top_drivers", [])
    result.setdefault("summary", "")

    citations = [
        {"title": a["title"], "uri": a["url"]}
        for a in top_articles
        if a.get("url")
    ]

    return {
        "sentiment_score": news_data.get("sentiment_score", 0.0),
        "sentiment_label": news_data.get("sentiment_label", "Neutral"),
        "top_drivers": result["top_drivers"],
        "summary": result["summary"],
        "citations": citations,
    }


def generate_outlook(
    ticker: str, technical_data: dict, sentiment_data: dict, api_key: str
) -> dict:
    """Synthesize technical + sentiment data into a qualitative 30-day
    directional outlook. Never a price target — only a lean score.

    Returns:
        {
            "directional_lean": float [-1.0, 1.0],
            "catalysts": [str, ...],
            "risks": [str, ...],
            "detailed_outlook": str,
            "simple_outlook": str,
            "disclaimer": str,
        }
    """
    client = genai.Client(api_key=api_key)

    disclaimer = (
        "AI-generated outlook based on sentiment and trend data — not "
        "financial advice. This is not a recommendation to buy or sell."
    )

    prompt = f"""Synthesize the following pre-computed technical data and
sentiment research for {ticker} into a 30-day directional outlook.

Technical data (already computed, do not recalculate):
{json.dumps(technical_data, indent=2, default=str)}

Sentiment research:
{json.dumps({k: v for k, v in sentiment_data.items() if k != 'citations'}, indent=2)}

Respond with ONLY a raw JSON object (no markdown fences) in exactly this
shape:
{{
  "directional_lean": <float between -1.0 (fully Bearish) and 1.0 (fully Bullish)>,
  "catalysts": ["<catalyst 1>", "<catalyst 2>", "<catalyst 3>"],
  "risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
  "detailed_outlook": "<5-6 sentence analyst-style paragraph with real depth: reference the specific technical posture (moving average positioning, momentum, volatility level) AND the specific sentiment drivers together, explain how they interact/conflict, and describe what would need to change for the outlook to shift. Direction and drivers ONLY. Never a price figure, percentage forecast, or buy/sell recommendation.>",
  "simple_outlook": "<one plain-language sentence a beginner would understand, e.g. 'Data currently leans bullish for {ticker} over the next month, but that is not guaranteed.'>"
}}

Rules:
- Never include a specific price target or percentage forecast.
- Never phrase anything as a recommendation to buy, sell, or hold.
- Describe direction and drivers descriptively only.
- Be specific — reference the actual technical figures and news drivers
  provided above rather than generic statements.
- Use objective, third-person financial reporting language."""

    response = _generate_with_retry(
        client,
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
        ),
    )

    result = _extract_json(response.text)
    result = _sanitize_obj(result)

    result.setdefault("directional_lean", 0.0)
    result.setdefault("catalysts", [])
    result.setdefault("risks", [])
    result.setdefault("detailed_outlook", "")
    result.setdefault("simple_outlook", "")

    result["directional_lean"] = max(
        -1.0, min(1.0, float(result["directional_lean"]))
    )
    result["disclaimer"] = disclaimer

    return result


def get_full_analysis(
    ticker: str, technical_data: dict, news_data: dict, api_key: str
) -> dict:
    """Single entry point: runs sentiment narrative synthesis then outlook
    synthesis, returning one combined dict that powers both the Detailed
    and Simple views without a second round of API calls per view.

    Args:
        news_data: output of stock_data.get_news_sentiment_raw(ticker, ...)
    """
    sentiment_data = analyze_sentiment(ticker, news_data, api_key)
    outlook_data = generate_outlook(ticker, technical_data, sentiment_data, api_key)

    return {
        "sentiment": sentiment_data,
        "outlook": outlook_data,
    }
