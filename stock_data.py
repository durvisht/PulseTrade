"""PulseTrade — deterministic stock market analytics.

All numeric/mathematical work lives here (yfinance + pandas + numpy).
Nothing in this module ever calls an LLM.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

PERIOD_MAP = {
    "7 Days": "1mo",
    "30 Days": "3mo",
    "90 Days": "6mo",
    "1 Year": "1y",
}


@st.cache_data(ttl=300, show_spinner=False)
def get_stock_history(ticker: str, period: str = "30 Days") -> pd.DataFrame:
    """Fetch historical OHLCV data and compute moving averages / daily % change.

    Returns a DataFrame indexed by Date with columns:
    Close, Volume, SMA_7, SMA_30, Daily_Pct_Change
    """
    yf_period = PERIOD_MAP.get(period, "3mo")
    raw = yf.Ticker(ticker).history(period=yf_period, interval="1d")

    if raw.empty:
        return pd.DataFrame(
            columns=["Close", "Volume", "SMA_7", "SMA_30", "Daily_Pct_Change"]
        )

    df = pd.DataFrame(index=raw.index)
    df["Close"] = raw["Close"]
    df["Volume"] = raw["Volume"]
    df["SMA_7"] = df["Close"].rolling(window=7, min_periods=1).mean()
    df["SMA_30"] = df["Close"].rolling(window=30, min_periods=1).mean()
    df["Daily_Pct_Change"] = df["Close"].pct_change() * 100
    df.index.name = "Date"

    # Trim display window to the requested horizon while keeping enough
    # lookback history for SMA_30 to be meaningful.
    horizon_days = {"7 Days": 7, "30 Days": 30, "90 Days": 90, "1 Year": 365}.get(
        period, 30
    )
    if len(df) > horizon_days:
        df = df.iloc[-horizon_days:]

    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_current_snapshot(ticker: str) -> dict:
    """Return current price, 24h % change, volume, and company name."""
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = t.info or {}
    except Exception:
        info = {}

    hist = t.history(period="5d", interval="1d")
    if hist.empty or len(hist) < 1:
        return {
            "current_price": None,
            "prev_close": None,
            "pct_change": None,
            "volume": None,
            "long_name": info.get("longName", ticker),
        }

    current_price = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
    pct_change = (
        ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0
    )
    volume = int(hist["Volume"].iloc[-1])

    return {
        "current_price": current_price,
        "prev_close": prev_close,
        "pct_change": pct_change,
        "volume": volume,
        "long_name": info.get("longName", ticker),
    }


def compute_volatility(df: pd.DataFrame) -> dict:
    """Compute annualized volatility (%) from daily % change, plus a
    qualitative label (Low / Moderate / High)."""
    if df.empty or "Daily_Pct_Change" not in df.columns:
        return {"annualized_pct": 0.0, "label": "Unknown"}

    daily_returns = df["Daily_Pct_Change"].dropna() / 100.0
    if daily_returns.empty:
        return {"annualized_pct": 0.0, "label": "Unknown"}

    daily_std = daily_returns.std()
    annualized_pct = float(daily_std * np.sqrt(252) * 100)

    if annualized_pct < 15:
        label = "Low"
    elif annualized_pct < 30:
        label = "Moderate"
    else:
        label = "High"

    return {"annualized_pct": round(annualized_pct, 1), "label": label}


def _bucket_sentiment_label(score: float) -> str:
    """Bucket a -1..1 score using Alpha Vantage's own thresholds, so the
    deterministic label always agrees with the deterministic score."""
    if score <= -0.35:
        return "Strongly Negative"
    if score <= -0.15:
        return "Negative"
    if score < 0.15:
        return "Neutral"
    if score < 0.35:
        return "Positive"
    return "Strongly Positive"


@st.cache_data(ttl=900, show_spinner=False)
def get_news_sentiment_raw(ticker: str, av_api_key: str, limit: int = 30) -> dict:
    """Fetch real news articles + per-article sentiment scores for a ticker
    from Alpha Vantage's NEWS_SENTIMENT endpoint, and compute a deterministic
    relevance-weighted aggregate score in Python.

    The sentiment score/label here are NEVER produced by an LLM — only the
    articles (title, url, summary) are later handed to Gemini so it can
    write an objective narrative and identify top drivers. This mirrors the
    same "LLM never computes numbers" rule used for the stock math above.

    Returns:
        {
            "sentiment_score": float [-1.0, 1.0],
            "sentiment_label": str,
            "articles": [
                {"title": str, "url": str, "summary": str,
                 "source": str, "relevance": float, "ticker_score": float},
                ...
            ],
            "error": str | None,
        }
    """
    empty_result = {
        "sentiment_score": 0.0,
        "sentiment_label": "Neutral",
        "articles": [],
        "error": None,
    }

    try:
        resp = requests.get(
            ALPHA_VANTAGE_URL,
            params={
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "apikey": av_api_key,
                "limit": limit,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return {**empty_result, "error": f"Network error: {exc}"}

    if "Error Message" in data:
        return {**empty_result, "error": data["Error Message"]}
    if "Note" in data:
        return {**empty_result, "error": data["Note"]}
    if "Information" in data:
        return {**empty_result, "error": data["Information"]}

    feed = data.get("feed", [])
    if not feed:
        return {**empty_result, "error": "No recent news articles found."}

    articles = []
    weighted_sum = 0.0
    weight_total = 0.0

    for item in feed:
        ticker_matches = item.get("ticker_sentiment", [])
        match = next(
            (t for t in ticker_matches if t.get("ticker", "").upper() == ticker.upper()),
            None,
        )
        if match is None:
            continue

        relevance = float(match.get("relevance_score", 0.0))
        ticker_score = float(match.get("ticker_sentiment_score", 0.0))

        weighted_sum += relevance * ticker_score
        weight_total += relevance

        articles.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "relevance": round(relevance, 3),
                "ticker_score": round(ticker_score, 3),
            }
        )

    if weight_total > 0:
        aggregate_score = weighted_sum / weight_total
    else:
        aggregate_score = 0.0

    aggregate_score = max(-1.0, min(1.0, aggregate_score))
    articles.sort(key=lambda a: a["relevance"], reverse=True)

    return {
        "sentiment_score": round(aggregate_score, 3),
        "sentiment_label": _bucket_sentiment_label(aggregate_score),
        "articles": articles,
        "error": None,
    }


def get_technical_summary(ticker: str, period: str = "30 Days") -> dict:
    """Bundle everything the AI outlook engine needs, pre-computed in Python."""
    df = get_stock_history(ticker, period)
    snapshot = get_current_snapshot(ticker)
    volatility = compute_volatility(df)

    latest_sma_7 = float(df["SMA_7"].iloc[-1]) if not df.empty else None
    latest_sma_30 = float(df["SMA_30"].iloc[-1]) if not df.empty else None

    momentum = None
    if latest_sma_7 is not None and latest_sma_30 is not None and latest_sma_30 != 0:
        momentum = round(((latest_sma_7 - latest_sma_30) / latest_sma_30) * 100, 2)

    return {
        "ticker": ticker,
        "current_price": snapshot["current_price"],
        "pct_change_24h": snapshot["pct_change"],
        "volume": snapshot["volume"],
        "sma_7": latest_sma_7,
        "sma_30": latest_sma_30,
        "momentum_pct": momentum,
        "volatility_pct": volatility["annualized_pct"],
        "volatility_label": volatility["label"],
        "long_name": snapshot["long_name"],
    }
