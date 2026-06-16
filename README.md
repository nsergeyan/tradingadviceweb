# Trading Buddy

> A full-stack trading assistant that combines quantitative strategies and local LLM-powered news analysis to produce simple BUY / DO NOT BUY signals on the most actively traded S&P 500 stocks.

**University group project** — Leiden University, 2024/2025

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Trading Strategies](#trading-strategies)
- [AI Research Engine](#ai-research-engine)
- [Testing](#testing)
- [Team](#team)

---

## Demo

[![Demo Video](https://img.youtube.com/vi/X5sK50jIdfg/0.jpg)](https://www.youtube.com/watch?v=X5sK50jIdfg)

> Click the thumbnail to watch the demo.

---

## Overview

Trading Buddy scans the S&P 500, identifies the 50 most liquid stocks by weekly volume, runs three independent quantitative strategies on the top 5, and aggregates them into a single trading signal per stock. Clicking any symbol opens an AI-generated research panel that fetches recent news and produces a plain-English analysis using a locally hosted LLM via Ollama.

---

## Features

- **Dynamic stock universe** — rebuilds weekly top-50 list automatically using yfinance volume data
- **Three combined strategies** — Break of Structure (BOS), Fair Value Gaps (FVG), Opening Range Breakout (ORB), weighted and merged into one decision
- **AI news analysis** — fetches articles from Yahoo Finance & Google News RSS, extracts full text, filters paywalled sources, and sends to a local LLM for structured analysis
- **Local OHLCV database** — SQLite via Peewee ORM, populated from Alpha Vantage; supports daily, weekly, and monthly timeframes
- **One-command launch** — `python main.py` starts the backend and opens the browser automatically
- **Backtesting modules** — standalone backtest scripts for each strategy (BOS, FVG, ORB)
- **VAR forecasting module** — experimental Vector AutoRegression predictor ready for future integration

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Database | SQLite, Peewee ORM |
| Data | Alpha Vantage API, yfinance |
| AI / LLM | Ollama (local), gemma3:12b |
| Web scraping | trafilatura, newspaper3k, BeautifulSoup4 |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Testing | pytest |

---

## Architecture

```
tradingadviceweb2/
├── main.py                        # Entry point — starts server + opens browser
├── backend/
│   ├── main_backend.py            # FastAPI app, routes, CORS, DB lifespan
│   ├── settings.py                # Env/config loading
│   ├── list_stocks.py             # Top-50 universe selector (weekly volume)
│   ├── final_strat.py             # Strategy combiner (BOS 60% + FVG 20% + ORB 20%)
│   ├── bos_strat.py               # Break of Structure strategy
│   ├── fair_value_gaps_strategy.py# Fair Value Gaps strategy
│   ├── orb_strategy.py            # Opening Range Breakout strategy
│   ├── analytics.py               # VAR forecasting (experimental)
│   ├── database/
│   │   ├── database.py            # SQLite connection + Peewee setup
│   │   ├── models.py              # MetaData & PriceData models
│   │   └── crud.py                # OHLCV fetch / update operations
│   ├── aiAnalyzer/
│   │   ├── deep_research.py       # News collection + LLM orchestration
│   │   └── prompt_ai.py           # LLM interface (Ollama HTTP)
│   └── backtest/
│       ├── bos_backtest.py
│       ├── fvg_backtest.py
│       └── orb_backtest.py
├── frontend/
│   ├── views.py                   # FastAPI router serving index.html
│   └── templates/
│       └── index.html             # Single-page UI
└── Test/
    └── Backend/                   # pytest suite (unit + integration + load)
```

**Request flow:**
```
Browser → GET /signals/top5
           → list_stocks.get_50_stocks()   (yfinance, cached weekly)
           → final_strategy() × 5          (Alpha Vantage → SQLite → BOS/FVG/ORB)
           → JSON response

Browser → GET /analyze/top5/{index}
           → deep_research.aiAnalyzeTopFiveStocks()
           → news fetch + full-text extraction
           → Ollama LLM prompt
           → structured JSON (summary / opportunities / risks / sources)
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- An [Alpha Vantage API key](https://www.alphavantage.co/support/#api-key) (free tier works)
- Docker Desktop *(only needed for the local LLM / AI analysis feature)*

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/tradingadviceweb2.git
cd tradingadviceweb2

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Local LLM setup (optional — needed for AI analysis)

The AI news analysis feature requires a local Ollama instance with the `gemma3:12b` model.

**Option A — Docker image (pre-configured):**
```bash
# Download localLLM.tar from the shared drive link (see team or releases)
docker load -i localLLM.tar
docker run --gpus all -p 11434:11434 localLLM
```

**Option B — Native Ollama:**
```bash
# Install Ollama from https://ollama.com
ollama pull gemma3:12b
ollama serve
```

---

## Configuration

Copy `.env.example` to `backend/.env` and fill in your values:

```bash
cp backend/.env.example backend/.env
```

```env
ALPHAVANTAGE_API_KEY=your_alpha_vantage_api_key_here
DATABASE_PATH=TradingAdvice.db
LOCAL_LLM_URL=http://localhost:11434    # optional, only for AI analysis
```

---

## Running the App

```bash
# From the project root — starts backend + opens browser automatically
python main.py
```

The server runs at `http://127.0.0.1:8000`.

**Manual start (backend only):**
```bash
uvicorn backend.main_backend:app --reload
```

---

## API Reference

### `GET /signals/top5`

Returns the top 5 most liquid S&P 500 stocks and their combined strategy signals.

```json
{
  "symbols": ["AAPL", "MSFT", "AMZN", "GOOGL", "META"],
  "signals": {
    "AAPL": {
      "decision": "BUY",
      "avg_risk": 1.72,
      "avg_gains": 4.01,
      "bos_signal": "BUY (risk level = low)",
      "fvg_price": 193.5,
      "orb_price": 195.2
    }
  }
}
```

### `GET /analyze/top5/{index}`

Returns AI-generated news and research analysis for the stock at `index` in the top-50 list (0-based).

```json
{
  "symbol": "AAPL",
  "summary": "Apple shares rose after strong iPhone sales...",
  "news": [
    {
      "title": "Apple beats earnings expectations",
      "publisher": "Reuters",
      "link": "https://...",
      "content": "Full article text...",
      "paywalled": false
    }
  ],
  "details": {}
}
```

### `GET /`

Serves the frontend UI (`index.html`).

---

## Trading Strategies

### Universe Selection

`list_stocks.py` reads the S&P 500 ticker list, fetches last week's volume for each stock via yfinance, and caches the top-50 result in `stocks_volume.csv`. The cache is invalidated weekly.

### Break of Structure (BOS) — weight: 60%

Examines the last 3 weekly candles:
- Higher highs + higher lows → strong bullish (risk score = 2)
- Partial → medium bullish (risk score = 1)
- Neither → neutral/bearish (risk score = 0)

Estimated gains derived from recent high/close spread.

### Fair Value Gaps (FVG) — weight: 20%

Identifies "big" candles by body-to-range ratio on weekly data, then detects bullish/bearish gaps around them. Applies a time-decay factor so recent gaps carry more weight.

### Opening Range Breakout (ORB) — weight: 20%

Uses the first 2 daily candles to define an opening range (`or_high`, `or_low`). Evaluates the next 3 days for breakouts and daily trend direction.

### Signal Aggregation

```python
risk  = 0.6 * bos_risk  + 0.2 * fvg_risk  + 0.2 * orb_risk
gains = 0.6 * bos_gains + 0.2 * fvg_gains + 0.2 * orb_gains

# Decision thresholds
risk >= 1.5  → "BUY"
risk >= 1.0  → "BUY (caution)"
risk < 1.0   → "DO NOT BUY"
```

---

## AI Research Engine

`aiAnalyzer/deep_research.py` orchestrates the following for a given ticker:

1. **News collection** — fetches articles from Yahoo Finance and Google News RSS, resolves redirects, extracts full text via trafilatura / newspaper3k, flags paywalled sources
2. **Context building** — combines company info (yfinance), 7-day price history, and article content into a structured prompt
3. **LLM inference** — sends the prompt to a local Ollama instance and parses the response into: *Summary*, *Opportunities*, *Risks*, *Sources*

`prompt_ai.py` handles the HTTP interface to Ollama, keeping the LLM calls in one place.

---

## Testing

```bash
pytest Test/
```

The test suite covers:
- Unit tests for each strategy (BOS, FVG, ORB, final combiner)
- Stock universe selection
- AI analyzer (normal, failure, empty-news scenarios)
- Load and stress tests
- Scalability tests

---

## Team

Built as a group project at Leiden University (2024/2025) — Group 27.

| Name | Contribution |
|---|---|
| Narek Sergeyan | FastAPI backend (`main_backend.py`), AI research engine (`deep_research.py`, `prompt_ai.py`), system integration, rontend UI/UX, some tests |
| Artem Litovenko | FastAPI backend (`main_backend.py`), AI research engine, data pipeline |
| Alexander Djurrema | Stock universe selector (`list_stocks.py`)|
| Jingshan Yuan | Database layer (`database/`), Fair Value Gaps strategy (`fair_value_gaps_strategy.py`) |
| Kaan Uysal | Break of Structure strategy (`bos_strat.py`) |
| Alejandro Lopez | Opening Range Breakout strategy (`orb_strategy.py`)|

> This project is not financial advice.
