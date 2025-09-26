import yfinance as yf
import requests
from openai import OpenAI
import os, time, calendar
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs, urlsplit, urlunsplit, quote_plus

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

# --------------------- Fetch News ---------------------
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
        out.append({
            "title": title.strip(),
            "publisher": publisher.strip() if publisher else "",
            "link": norm_link,
            "timestamp": ts
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
        rss_q = quote_plus(f'("{symbol}" OR "{comp_name}")') if len(queries) > 1 else quote_plus(symbol)
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

    # --------- Provider: Bing News (optional, API key required) ----------
    try:
        bing_key = os.getenv("BING_NEWS_API_KEY")
        if bing_key:
            before = len(out)
            headers = {"Ocp-Apim-Subscription-Key": bing_key}
            for q in queries:
                params = {
                    "q": q,
                    "mkt": "en-US",
                    "freshness": "Week",
                    "count": max_articles,
                    "safeSearch": "Off"
                }
                r = requests.get("https://api.bing.microsoft.com/v7.0/news/search",
                                 headers=headers, params=params, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    for art in data.get("value", []):
                        title = art.get("name")
                        link = art.get("url")
                        publisher = ""
                        prov = art.get("provider") or []
                        if prov and isinstance(prov, list) and prov[0].get("name"):
                            publisher = prov[0]["name"]
                        pub_ts = None
                        dp = art.get("datePublished")
                        if dp:
                            try:
                                from dateutil import parser as dtp
                                pub_ts = _epoch(dtp.isoparse(dp))
                            except Exception:
                                pass
                        _add(title, publisher, link, pub_ts)
            if len(out) > before:
                used_sources.add("Bing News")
    except Exception:
        pass

    # --------- Provider: Finnhub (optional, API key required) ----------
    try:
        finnhub_key = os.getenv("FINNHUB_API_KEY")
        if finnhub_key:
            before = len(out)
            date_to = datetime.utcnow().date()
            date_from = (datetime.utcnow() - timedelta(days=lookback_days)).date()
            params = {"symbol": symbol, "from": str(date_from), "to": str(date_to), "token": finnhub_key}
            r = requests.get("https://finnhub.io/api/v1/company-news", params=params, timeout=6)
            if r.status_code == 200:
                for it in r.json():
                    _add(it.get("headline"), it.get("source"), it.get("url"), it.get("datetime"))
            if len(out) > before:
                used_sources.add("Finnhub")
    except Exception:
        pass

    # --------- Provider: NewsAPI.org (optional, API key required) ----------
    try:
        newsapi_key = os.getenv("NEWSAPI_KEY")
        if newsapi_key:
            before = len(out)
            for q in queries:
                params = {
                    "q": q,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": max_articles,
                    "apiKey": newsapi_key
                }
                r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=6)
                if r.status_code == 200:
                    data = r.json()
                    for art in data.get("articles", []):
                        title = art.get("title")
                        link = art.get("url")
                        src = (art.get("source") or {}).get("name")
                        pub_ts = None
                        dp = art.get("publishedAt")
                        if dp:
                            try:
                                from dateutil import parser as dtp
                                pub_ts = _epoch(dtp.isoparse(dp))
                            except Exception:
                                pass
                        _add(title, src, link, pub_ts)
            if len(out) > before:
                used_sources.add("NewsAPI")
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


# --------------------- Scoring System ---------------------
def calculate_financial_score(info, hist):
    score = 0

    # EPS
    eps = info.get("trailingEps", 0)
    if eps < 0: score -= 3
    elif eps > 1: score += 2

    # Debt-to-equity
    debt_to_equity = info.get("debtToEquity", 0)
    if debt_to_equity > 100: score -= 2
    elif debt_to_equity < 50: score += 1

    # Revenue growth (1-year)
    rev_growth = info.get("revenueGrowth", 0)
    if rev_growth and rev_growth < 0: score -= 2
    elif rev_growth and rev_growth > 0.2: score += 2

    # Profit margin
    profit_margin = info.get("profitMargins", 0)
    if profit_margin and profit_margin < 0: score -= 2
    elif profit_margin and profit_margin > 0.1: score += 1

    # Stock price trend last 7 days
    try:
        pct_change = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]
        if pct_change > 0.05: score += 1
        elif pct_change < -0.05: score -= 1
    except:
        pass

    return score

def calculate_news_score(news_items):
    score = 0
    negative_keywords = ["scandal", "lawsuit", "fraud", "investigation", "bankruptcy", "recall"]
    positive_keywords = ["partnership", "contract", "growth", "record revenue", "acquisition", "innovation"]

    for news in news_items:
        title = news['title'].lower()
        if any(word in title for word in negative_keywords):
            score -= 2
        elif any(word in title for word in positive_keywords):
            score += 1
    return score

# --------------------- AI Analysis ---------------------
def analyze_stock(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    hist = stock.history(period="7d")
    news_result = get_recent_news(symbol, max_articles=10)
    news_items = news_result["news"]
    sources_used = news_result["sources"]

    # Calculate scores
    financial_score = calculate_financial_score(info, hist)
    news_score = calculate_news_score(news_items)
    total_score = financial_score + news_score

    # Convert to recommendation
    if total_score <= -3:
        recommendation = "Sell"
    elif -2 <= total_score <= 0:
        recommendation = "Hold"
    elif 1 <= total_score <= 3:
        recommendation = "Buy"
    else:
        recommendation = "Strong Buy"

    # Prepare news for AI
    news_list = "\n".join([f"{i+1}. {n['title']} ({n['publisher']})" for i, n in enumerate(news_items)])

    # AI prompt
    prompt = f"""
You are a financial analyst AI. Evaluate the NASDAQ stock {symbol} for beginner investors.
Here is the last 7 days of price data:
{hist.to_dict()}

Company info:
{info}

Recent news headlines:
{news_list}

Financial Score: {financial_score}
News Score: {news_score}
Total Score: {total_score}
AI Recommendation: {recommendation}

Instructions:
- Explain your recommendation in simple language.
- Highlight key risks and opportunities from both financials and news.
- Provide short-term and long-term outlook.
- Use clear headings, bullet points, and beginner-friendly language.
- Be realistic and balanced.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700
    )

    print("\nSources used for news:")
    for s in sources_used:
        print("-", s)

    return response.choices[0].message.content


# --------------------- Main ---------------------
def main():
    print("Welcome to the NASDAQ AI Stock Analyzer!")
    while True:
        symbol = input("Enter NASDAQ stock symbol (e.g., AAPL, TSLA): ").upper().strip()
        if is_valid_nasdaq(symbol):
            break
        print("Invalid NASDAQ stock symbol. Try again.")

    print("\nFetching analysis...\n")
    analysis = analyze_stock(symbol)
    print(f"Analysis for {symbol}:\n")
    print(analysis)

if __name__ == "__main__":
    main()