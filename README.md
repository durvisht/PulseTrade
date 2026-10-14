# PulseTrade

PulseTrade is a two-tier stock intelligence dashboard that pairs deterministic
market analytics (via `yfinance`/`pandas`/`numpy`) with real, live news
research (via Alpha Vantage's `NEWS_SENTIMENT` endpoint) and a qualitative
30-day directional outlook synthesized by the Gemini API.

Built as a college app-portfolio project to demonstrate: separation of
deterministic computation from LLM synthesis, structured JSON prompting,
retrieval grounded in real citations, and output-safety guardrails on
generative financial content — entirely on free-tier APIs, at zero cost.

## Why this architecture

A recurring failure mode in "AI + finance" demos is letting the LLM do the
math (price targets, % forecasts, sentiment scores) — which fabricates false
precision — or letting it narrate itself ("As an AI, I think..."), which
undermines the tone of objective reporting. PulseTrade avoids both by hard
separation between deterministic computation and LLM synthesis:

- **All numbers come from Python — including sentiment.** `stock_data.py`
  computes price, SMAs, daily % change, and annualized volatility directly
  from `yfinance` history. It also computes the sentiment score itself: a
  relevance-weighted aggregate of real per-article sentiment scores returned
  by Alpha Vantage's `NEWS_SENTIMENT` endpoint (`get_news_sentiment_raw`).
  The LLM never invents a number — it only writes the qualitative narrative
  around numbers that already exist.
- **Citations are real, not generated.** Article titles and URLs come
  directly from Alpha Vantage's news feed, not from the model — eliminating
  the citation-hallucination risk that comes with asking an LLM to cite its
  own sources.
- **The LLM never predicts a price.** `gemini_engine.generate_outlook`
  returns a `directional_lean` score (-1.0 to +1.0) — a qualitative
  visualization of sentiment + momentum, not a forecast — plus catalysts,
  risks, and a plain-language read. A disclaimer is rendered wherever this
  appears.
- **Self-referential language is actively suppressed**, not just requested.
  The `system_instruction` forbids phrases like "as an AI" or "Gemini
  indicates," and `gemini_engine._sanitize_text` runs a regex pass over
  every generated string as a second line of defense in case the model
  drifts.
- **One API call pair per ticker.** `get_full_analysis` runs sentiment
  narrative synthesis once and outlook synthesis once; the result is cached
  in `st.session_state`, so switching between the Detailed and Simple tabs
  never triggers a re-fetch or extra API cost.
- **Zero-cost by design.** Google Cloud increasingly gates even free-tier
  features (Search Grounding, Custom Search) behind a linked billing
  account. PulseTrade instead uses Alpha Vantage — a finance-specific news
  API with a genuinely free, no-card-required key — for real-time news
  retrieval, keeping the entire stack runnable at $0.

## Project structure

```
├── app.py                   # Streamlit layout, tabs, sidebar, caching
├── stock_data.py             # yfinance + Alpha Vantage fetch, deterministic math (SMAs, volatility, sentiment aggregate)
├── gemini_engine.py           # google-genai client, narrative synthesis, outlook synthesis, sanitization, retry logic
├── requirements.txt
├── .streamlit/
│   ├── secrets.toml           # local GEMINI_API_KEY + ALPHA_VANTAGE_API_KEY (gitignored)
│   └── config.toml            # light theme for the main content area
└── README.md
```

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Get two free API keys (no credit card required for either):
   - **Gemini**: [Google AI Studio](https://aistudio.google.com/apikey)
   - **Alpha Vantage**: [alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)

3. Either:
   - Put both in `.streamlit/secrets.toml`:
     ```toml
     GEMINI_API_KEY = "your-gemini-key"
     ALPHA_VANTAGE_API_KEY = "your-av-key"
     ```
   - Or leave `secrets.toml` blank and paste both keys into the sidebar's
     **Gemini API Key** / **Alpha Vantage API Key** fields when the app is
     running.

4. Run the app:

   ```bash
   streamlit run app.py
   ```

## How it works

1. **User picks a ticker + time horizon** in the sidebar and clicks Analyze.
2. `stock_data.get_technical_summary` pulls yfinance history and computes
   price, % change, volume, SMA-7, SMA-30, momentum, and annualized
   volatility — pure Python/pandas, zero LLM involvement.
3. `stock_data.get_news_sentiment_raw` fetches real recent news articles for
   the ticker from Alpha Vantage, along with Alpha Vantage's own per-article
   sentiment scores, and computes a relevance-weighted aggregate score in
   Python — again, zero LLM involvement in the number itself.
4. `gemini_engine.analyze_sentiment` sends the real articles (title, source,
   summary, per-article score) to Gemini and asks it to identify the top 3
   drivers and write an objective 2-sentence summary — treating the
   pre-computed scores as ground truth, never recalculating them. Citations
   returned to the UI are the real article titles/URLs, not model output.
5. `gemini_engine.generate_outlook` sends the already-computed technical
   numbers plus the sentiment result to Gemini, asking it to synthesize a
   single structured JSON outlook: a `directional_lean` score, catalysts,
   risks, a detailed analyst-style paragraph, and a plain-language sentence
   — explicitly forbidding price targets or buy/sell phrasing.
6. Both results are cached once in `st.session_state` and shared by the
   **Detailed** and **Simple** tabs, so tab-switching is free.
7. The **Bearish/Bullish Slider** is a single reusable component
   (`render_lean_slider`) that renders the same `directional_lean` score at
   two levels of detail — full lean indicator + written outlook in
   Detailed, slider + one sentence in Simple.

## Cost

Both APIs are used entirely within their free tiers:
- **Alpha Vantage**: free key, no billing account, rate-limited (cache the
  news fetch to stay well within limits — `get_news_sentiment_raw` is
  cached for 15 minutes via `@st.cache_data`).
- **Gemini**: free tier has a per-model daily request cap (varies by model
  and account). `gemini_engine.py` uses `gemini-3.1-flash-lite` and retries
  automatically on transient `503` (high demand) and `429` (short rate-limit
  window) errors. If you exhaust a model's daily free quota during heavy
  testing, swap `MODEL_NAME` in `gemini_engine.py` for another Gemini model
  — each model tracks its free-tier quota separately.

## Disclaimer

All outlook content is generated from sentiment and technical trend data —
it is not financial advice, and PulseTrade never recommends buying or
selling any security.
