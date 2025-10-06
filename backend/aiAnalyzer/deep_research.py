import yfinance as yf
import requests
from openai import OpenAI
import os, time, calendar
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs, urlsplit, urlunsplit, quote_plus
from newspaper import Article


# Set your OpenAI API key
#You can put your own api if you have a better one
api_key = "YOUR_OPENAI_KEY_HERE"
client = OpenAI(api_key=api_key)

# --------------------- Validation ---------------------
def is_valid_nasdaq(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return info.get("exchange") == "NMS"  # NASDAQ
    except Exception:
        return False

def get_recent_news(symbol, max_articles=10, lookback_days=7, lang="en-US", region="US"):
    """
    Returns dict:
    {
      "news": [ {title, publisher, link, timestamp}, ... ],
      "sources": [ "Yahoo Finance", "Google News", "Bing News", "Finnhub", "NewsAPI" ]
    }
    Sources: Yahoo Finance, Google News RSS (no API key) + optionally Bing, Finnhub, NewsAPI
    """
    out, seen_titles, seen_links, used_sources = [], set(), set(), set()
    look_from = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    # --------------------- Helper for getting content from news ---------------------
    def _fetch_article_content(url: str) -> str:
        """Download and extract main text from a news article link."""
        try:
            article = Article(url)
            article.download()
            article.parse()
            return article.text.strip()
        except Exception:
            return ""


    # --- helpers ---
    def _epoch(dt: datetime) -> int:
        """Convert datetime to Unix timestamp (UTC)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    def _strip_tracking(u: str) -> str:
        """Remove tracking parameters (utm, fbclid, etc.) from a URL."""
        try:
            parts = urlsplit(u)
            q = parse_qs(parts.query)
            safe_q = {k: v for k, v in q.items() if not k.lower().startswith(("utm_", "gclid", "fbclid", "mc_cid", "mc_eid"))}
            new_query = urlencode([(k, vv) for k, vs in safe_q.items() for vv in vs])
            return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, new_query, ""))
        except Exception:
            return u

    def _add(title, publisher, link, ts):
        """Add a news item if not duplicate and has required fields."""
        if not (title and link and ts):
            return
        norm_title = title.strip().lower()
        norm_link = _strip_tracking(link)
        if norm_title in seen_titles or norm_link in seen_links:
            return
        seen_titles.add(norm_title)
        seen_links.add(norm_link)

        content = _fetch_article_content(norm_link) #get content text
        text_check = f"{title.lower()} {content.lower()}"
        if symbol.lower() not in text_check and comp_name.lower() not in text_check:
            return  # skip irrelevant article

        out.append({
            "title": title.strip(),
            "publisher": publisher.strip() if publisher else "",
            "link": norm_link,
            "timestamp": ts,
            "content": content
        })

    # --- setup: try to get company name (for better queries) ---
    try:
        comp_name = ""
        try:
            comp_name = yf.Ticker(symbol).info.get("longName") or ""
        except Exception:
            pass
        queries = [symbol]
        if comp_name and comp_name.lower() not in {symbol.lower()}:
            queries.append(comp_name)
    except Exception:
        queries = [symbol]

    # --------- Provider: Yahoo Finance ----------
    try:
        before = len(out)
        for q in queries:
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={quote_plus(q)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            for item in (data.get("news") or [])[:max_articles]:
                ts = item.get("providerPublishTime")
                pub_ts = int(ts) if isinstance(ts, (int, float)) and ts > 0 else None
                _add(item.get("title"), item.get("publisher"), item.get("link"), pub_ts)
        if len(out) > before:
            used_sources.add("Yahoo Finance")
    except Exception:
        pass

    # --------- Provider: Google News (RSS, no API key) ----------
    try:
        import feedparser
        before = len(out)
        rss_q = quote_plus(f'("{symbol}" OR "{comp_name}" OR "NASDAQ:{symbol}")') if len(queries) > 1 else quote_plus(f'"{symbol}" OR "NASDAQ:{symbol}"')
        rss_url = (
            f"https://news.google.com/rss/search?q={rss_q}+when:{lookback_days}d"
            f"&hl={lang}&gl={region.split('-')[0] if '-' in region else region}&ceid={region}:{lang.split('-')[0]}"
        )
        feed = feedparser.parse(rss_url)
        for e in feed.entries[:max_articles * 2]:
            title = getattr(e, "title", None)
            link = getattr(e, "link", None)
            publisher = ""
            pub_ts = None
            if getattr(e, "published_parsed", None):
                pub_ts = calendar.timegm(e.published_parsed)
            elif getattr(e, "updated_parsed", None):
                pub_ts = calendar.timegm(e.updated_parsed)
            _add(title, publisher, link, pub_ts)
        if len(out) > before:
            used_sources.add("Google News")
    except Exception:
        pass

    # --------- Post-processing: filter, sort, slice ----------
    if out:
        min_ts = _epoch(look_from)
        out = [x for x in out if (x["timestamp"] or 0) >= min_ts]
        for x in out:
            if not x["timestamp"]:
                x["timestamp"] = min_ts
        out.sort(key=lambda x: x["timestamp"], reverse=True)
        out = out[:max_articles]

    return {"news": out, "sources": sorted(list(used_sources))}

# --------------------- Ai2 ---------------------
def aiAnalyzeTopFiveStocks(stocks):
    """
    Analyze top 5 stocks using recent news (titles + full content) and AI reasoning.
    Input: list of 5 stock symbols
    Output: GPT-generated detailed analysis for all 5 stocks
    """
    all_summaries = []

    for symbol in stocks:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="7d")
        news_result = get_recent_news(symbol, max_articles=10)
        news_items = news_result["news"]

        # Prepare news content for GPT
        news_list = "\n".join([
            f"{i + 1}. {n['title']} ({n.get('publisher', '')})\n"
            f" URL: {n.get('link', '')}\n"
            f" Full content:\n{n.get('content', '')}\n"
            for i, n in enumerate(news_items)
        ])

        print("\nFull article content:\n")
        for i, n in enumerate(news_items, 1):
            print(f"[{i}] {n['title']}")
            print(f"Publisher: {n.get('publisher', '')}")
            print(f"URL: {n.get('link', '')}\n")
            print(n.get('content', '')[:5000])  # shows up to 5000 symbols
            print("\n" + "-" * 120 + "\n")

        # Build per-stock summary for GPT
        stock_prompt = f"""
Stock: {symbol}

Company info: {info}
Recent price trend (7 days): {hist.to_dict()}

News articles (titles + full content):
{news_list}

All sources for this stock: {', '.join(news_result['sources'])}
"""
        all_summaries.append(stock_prompt)

    # Combine all 5 stock summaries into a single GPT prompt
    combined_prompt = f"""
You are a financial analyst AI. Your task is to evaluate 5 NASDAQ stocks chosen as the best current opportunities by another system.
That means all 5 stocks are already considered good investments — so your recommendation should always be **Buy** or **Strong Buy**.

### Important Guidelines:
- Focus mainly on the news content (titles + content). The news is the most important part of your reasoning.
- Company info and recent price trends can be mentioned, but only as background context.
- Always explain clearly **why the news supports a Buy recommendation**.
- Also point out any **risks** or negative details from the news, so investors understand the downsides too.
- Write in a clear, simple, beginner-friendly style.

### For each stock, provide:
1. **News Summary**
   - Summarize the main points of the news articles in simple language.
   - Highlight what’s positive and also mention any negative signals.

2. **Opportunities**
   - List the positive news and growth drivers.

3. **Risks**
   - List potential problems or uncertainties mentioned in the news.

4. **AI Recommendation**
   - Always give **Buy** or **Strong Buy**.
   - Explain why the news supports this recommendation.

5. **Outlook**
   - **Short-term:** How the stock might react in the near future based on news.
   - **Long-term:** Growth potential and risks if these trends continue.

### Tone and Style:
- Use bullet points and short sections.
- Be clear, simple, and structured.
- Always connect your recommendation directly to the news.

**IMPORTANT:** At the end of your analysis for each stock, **list all news sources (publishers) used** in a section called **Sources**.

Stocks to analyze:
{chr(10).join(all_summaries)}
"""
    # Try OpenAI first, fall back to Gemini
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": combined_prompt}],
            max_tokens=2500
        )
        return response.choices[0].message.content

    except Exception as e:
        print("OpenAI API failed:", str(e))
        print("Falling back to Gemini API...")

        try:
            GEMINI_API_KEY = "AIzaSyBF0_vWi7TtJ2NdMerL_uB-13pjNsfRqrs"
            GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": combined_prompt
                            }
                        ]
                    }
                ]
            }

            r = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except Exception as ge:
            print("Gemini API failed too:", str(ge))
            return "Both AI services failed. Please try again later."

if __name__ == "__main__":
    top5 = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"]
    print(aiAnalyzeTopFiveStocks(top5))
