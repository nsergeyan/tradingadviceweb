# TradingAdvice

**TradingAdvice** (shown in the UI as **Trading Buddy**) is an experimental trading assistant that combines:

- **Liquidity filters** (top 50 most-traded S&P 500 stocks),
- **Three quantitative trading strategies**, and
- **AI-powered news & company analysis**

…to produce simple **BUY / DO NOT BUY** decisions on the **top 5 most tradable stocks**, plus a detailed AI-written research view when you click on a stock.

---

## Table of Contents

- [Name](#name)
- [Description](#description)
- [Badges](#badges)
- [Visuals](#visuals)
- [Getting Started](#getting-started)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Run the Backend](#run-the-backend)
  - [Open the Frontend](#open-the-frontend)
- [Usage](#usage)
  - [User Flow](#user-flow)
  - [Main API Endpoints](#main-api-endpoints)
- [Architecture](#architecture)
  - [Frontend](#frontend)
  - [Backend API](#backend-api)
  - [Data & Database](#data--database)
  - [Trading Strategies](#trading-strategies)
  - [AI News & Research Engine](#ai-news--research-engine)
  - [Advanced Analytics](#advanced-analytics)


---

## Name

**TradingAdvice**  
A web-based assistant for trading signals and AI-enhanced stock research.

---

## Description

TradingAdvice is a small web application where a user can:

1. Open a page and request **signals for the top 5 most tradable stocks** (by weekly volume).
2. See a simple decision per stock:  
   **BUY**, **BUY (caution)**, or **DO NOT BUY**, plus average risk and expected gains.
3. Click on any symbol to open an **AI-generated news & fundamentals analysis** for that stock.

The app is built as a **FastAPI backend** with a **minimal HTML/JavaScript frontend** and uses:

- Price data from **Alpha Vantage** and **Yahoo Finance**,
- A local **SQLite** database (via Peewee),
- Multiple **trading strategies** (Break of Structure, Fair Value Gaps, Opening Range Breakout),
- And several **LLM providers** (OpenAI GPT, Google Gemini, and a local LLM via Ollama) to rank stocks and analyze news.

### Key Features

- **Top 50 universe, updated weekly**
  - Automatically finds the **50 most-traded S&P 500 stocks** based on last week’s volume.

- **Top 5 signals**
  - Selects the **top 5 by volume** and runs three strategies on each:
    - Break of Structure (BOS)
    - Fair Value Gaps (FVG)
    - Opening Range Breakout (ORB)
  - Combines them into one **final decision**, **average risk**, and **average estimated gains**.

- **AI news & research per stock**
  - When the user clicks a stock:
    - Fetches recent news and company info.
    - Uses an LLM to produce:
      - A plain-language **summary**,
      - **Opportunities** and **risks**,
      - A list of **sources**.

- **Local OHLCV database**
  - Uses Alpha Vantage to download **daily, weekly, and monthly candles** into SQLite.
  - Reusable via a small CRUD/ORM layer.

- **Extensible quant & AI stack**
  - Additional modules for **VAR-based forecasting** and **backtesting** are included for future experiments.

---

## Badges(Not finished)

- CI Status: -
- Python Version: `3.10+`
- Framework: `FastAPI`

---

## Visuals

_Add screenshots or GIFs here when available._

For example:

- Screenshot of the **Top 5 Signals** table.
- Screenshot of the **News / Analysis** panel for a single stock.

---

## Getting Started

### Requirements

- **Python** 3.10+ (recommended)
- **pip** / **virtualenv** or similar
- **Alpha Vantage API key**
- (Optional) **OpenAI API key** for GPT-based ranking
- (Optional) **Google Gemini API key**
- (Optional) Local LLM via **Ollama** for deep analysis
- Basic command-line familiarity

### Installation

From the project root:

```sh
pip install -r backend/requirements.txt
```
### If you prefer a virtual environment

```sh
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

---

## Configuration

Set your configuration via environment variables or a `.env` file. Typical settings:

```env
DATABASE_NAME=trading.db
ALPHAVANTAGE_API_KEY=your_alpha_vantage_key

OPENAI_API_KEY=your_openai_key          # optional
GEMINI_API_KEY=your_gemini_key          # optional
LOCAL_LLM_URL=http://localhost:11434    # optional, for Ollama/local LLM
```

---

## Run the backend

From the backend directory (example):

```
cd backend
uvicorn main:app --reload
```

This starts FastAPI at:

http://127.0.0.1:8000

---

## Open the Frontend

If you serve index.html via FastAPI (e.g. route /), open:

http://127.0.0.1:8000/

Or open index.html directly in your browser and make sure the script’s BACKEND_URL matches:

```js
const BACKEND_URL = "http://127.0.0.1:8000";
```

---

## Usage

User Flow

1. Start the backend

```sh
uvicorn main:app --reload
```

2. Open the frontend page (served at / or by opening index.html directly).

3. Click “Get signals”:

    The app:

- Loads the top 50 most-traded S&P 500 stocks.

- Picks the top 5 by volume.

- Runs the three strategies and combines them.

- Displays the Top 5 Signals table.

4. Click on any symbol:

- The News / Analysis panel opens.

- The backend fetches recent news and runs the AI analysis.

- You see:

  - A summary,

  - A list of news articles (title, excerpt, publisher, link),

  - Optional raw details.

---

## Main API Endpoints

GET /signals/top5

Returns the top 5 tradable stocks and their combined strategy signals.

Example response:

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
    },
    "MSFT": {
      "decision": "BUY (caution)",
      "avg_risk": 1.20,
      "avg_gains": 2.50,
      "bos_signal": "BUY (risk level = medium)",
      "fvg_price": 420.0,
      "orb_price": 415.3
    }
  }
}

```
GET /analyze/top5/{index}

Returns AI news & company analysis for the symbol at index in the top 50 list.

Example response (simplified):

```json
{
  "symbol": "AAPL",
  "summary": "Apple shares rose after strong iPhone sales...",
  "news": [
    {
      "title": "Apple beats earnings expectations",
      "publisher": "Reuters",
      "link": "https://example.com/article",
      "content": "Full article text...",
      "paywalled": false
    }
  ],
  "details": {
    "company_info": { "...": "..." },
    "price_history": [ "...", "..." ]
  }
}
```

---

## Architecture

Frontend

- File: index.html

- Stack: plain HTML + JavaScript + CSS (dark theme).

- Talks to the backend via fetch calls to http://127.0.0.1:8000.

Main UI elements:

“Top 5 Signals” card

- Button: Get signals

- On click:

  - Calls GET /signals/top5

  -  Renders a table:

```markdown
| Symbol | Decision      | Risk | Gains |
|--------|--------------|------|-------|
| AAPL   | BUY          | 1.72 | 4.01  |
| MSFT   | BUY (caution)| 1.20 | 2.50  |

```

News / Analysis panel

- Hidden by default.

- When a symbol is clicked:

  - Calls GET /analyze/top5/{index}.

  - Displays:

    - A summary block,

    - A list of news items (title, excerpt, publisher, link),

    - Optional raw details section.

---
  
## Backend API

- Entry point: main.py

- Framework: FastAPI

- DB access: Peewee + SQLite

On startup:

- Connects to the SQLite database.

- Creates tables (MetaData, PriceData) if they don’t exist.

- Configures CORS (all origins allowed) for local dev.

Routes:

- views.py – serves the main HTML template at /.

- Main JSON endpoints:

  - GET /signals/top5

  - GET /analyze/top5/{index}

---

## Data & Database

Configuration

- File: settings.py

- Reads environment variables for:

  - DATABASE_NAME

  - ALPHAVANTAGE_API_KEY

  - LLM-related API keys/URLs.

Database

- File: database/database.py

- Uses SqliteDatabase with a thread-safe connection state.

- Provides get_db() for request-scoped DB connections.

Models

- File: database/models.py

    MetaData

  - symbol – stock ticker (e.g. AAPL)

  - info_type – "Daily", "Weekly", "Monthly"

  - last_refreshed

  - time_zone

    PriceData

  - meta – FK to MetaData

  - date

  - open, high, low, close

  - volume

OHLCV CRUD

- Folder: DbForStockUpdate (e.g. crud.py)

  - update_ohlcv(symbol, info_type="Weekly")

    - Calls Alpha Vantage time series endpoints.

    - Updates MetaData & PriceData.

  - fetch_ohlcv(symbol, info_type="Weekly", limit=None, start_date=None, end_date=None)

    - Returns a pandas DataFrame of OHLCV rows.

---

## Trading Strategies

Universe Selection – Top 50

- File: list_stocks.py

  - get_50_stocks():

    - Reads S&P 500 tickers from stocks.csv.

    - For each ticker:

      - Uses yfinance to get last week’s volume.

    - Writes stocks_volume.csv:

      - First line: current ISO week.

      - Remaining lines: Symbol,Volume.

    - If the week changed, regenerates stocks_volume.csv.

    - Returns the top 50 symbols by weekly volume.

This list is used for both /signals/top5 and /analyze/top5/{index}.

---

## Final Strategy – Combiner

- File: final_strat.py

Combines:

- Break of Structure (BOS) – bos_strat.py

- Fair Value Gaps (FVG) – fair_value_gaps_strategy.py

- Opening Range Breakout (ORB) – orb_strategy.py

Workflow summary:

```python
bos_price, bos_risk, bos_gains, bos_signal = bos_strat(cash, symbol)

df_weekly = fetch_ohlcv(symbol, "Weekly", limit=10)
fvg_price, fvg_risk, fvg_gains = fair_value_gaps_strategy(df_weekly)

update_ohlcv(symbol, "Daily")
df_daily = fetch_ohlcv(symbol, "Daily", limit=10)
orb_price, orb_risk, orb_gains = orb_strategy(df_daily)
```

Weighted averages:

```python
risk  = 0.6 * bos_risk + 0.2 * fvg_risk + 0.2 * orb_risk
gains = 0.6 * bos_gains + 0.2 * fvg_gains + 0.2 * orb_gains
```

Decision:

- risk >= 1.5 → "BUY"

- 1.0 <= risk < 1.5 → "BUY (caution)"

- risk < 1.0 → "DO NOT BUY"

---

## BOS Strategy – bos_strat.py

- Uses weekly OHLCV.

- Checks the last 3 candles:

  - Higher highs + higher lows → strong bullish (risk = 2).

  - Partial higher highs/lows → medium bullish (risk = 1).

  - Else → neutral/negative (risk = 0).

- Computes estimated gains from recent highs/closes.

- Also has bos_backtest.py using backtrader to backtest this logic.

---

## FVG Strategy – fair_value_gaps_strategy.py

- Uses weekly OHLCV.

- Identifies “big” candles by body-to-range ratio.

- Looks for bullish/bearish fair value gaps around those candles.

- Applies a time-decay factor so recent gaps have more weight.

- Returns:

  - estimated_price

  - risk_level

  - estimated_gains

---

## ORB Strategy – orb_strategy.py

- Uses daily OHLCV.

- First two days define the opening range:

  - or_high = max high of days 0–1

  - or_low = min low of days 0–1

- Next three days:

  - Check for breakouts above or_high or below or_low.

  - Evaluate daily trend (close vs open).

- Returns:

  - estimated_price

  - risk_level

  - estimated_gains

---

## AI News & Research Engine

- Folder: aiAnalyzer (e.g. deep_research.py, prompt_ai.py).

News Collection

- Validates tickers with yfinance.

- Collects recent articles from:

  - Yahoo Finance

  - Google News RSS

- Cleans URLs and resolves redirects.

- Extracts full article text with newspaper3k / trafilatura.

- Filters by relevance to the ticker/company.

- Marks likely paywalled sources.

- Returns structured news objects:

  - title

  - publisher

  - link

  - timestamp

  - content

AI Stock Ranking

- initial_stock_ranking():

  - Takes candidate tickers from get_50_stocks() (first 10).

  - Fetches short news context per ticker.

  - Builds a prompt listing all candidates and news.

  - Sends prompt to:

- OpenAI GPT (prompt_ai.gpt),

- Falls back to Google Gemini (prompt_ai.gemini) if needed.

  - Asks the model to output a comma-separated ranking from worst to best.

  - Parses the response and takes the top 5.

(This function is available and can be integrated to replace the simple “top 5 by volume” approach if desired.)

Deep AI Analysis – aiAnalyzeTopFiveStocks(symbol)

For a given symbol:

- Retrieves:

  - Company info via yfinance.Ticker(symbol).info

  - Last 7 days of prices

  - Full news (via the news collector)

- Builds a rich prompt containing:

  - Company description

  - Short price history

  - Titles + full content of recent news

- Sends the prompt to a local LLM via prompt_ai.local_llm(...):

  - Typically an Ollama model (e.g. gemma3:12b).

- Instructs the LLM to output:

  - News Summary

  - Opportunities

  - Risks

  - Sources

The result is returned as JSON-like data and displayed in the News / Analysis panel.

LLM Orchestration – prompt_ai.py

- gpt(prompt: str) – OpenAI GPT (e.g. gpt-5-nano).

- gemini(prompt: str) – Google Gemini (gemini-2.0-flash).

- local_llm(prompt: str, system_prompt: str = None) – Local LLM via HTTP (Ollama).

---

## Advanced Analytics

- File: analytics.py

Implements a VAR (Vector AutoRegression) forecaster:

- Takes historical OHLCV data.

- Standardizes with StandardScaler.

- Fits a VAR model.

- Predicts next-step OHLCV values plus confidence intervals.

- Inverse-transforms to original units.

Currently not wired into the UI, but ready for future forecast/volatility features.