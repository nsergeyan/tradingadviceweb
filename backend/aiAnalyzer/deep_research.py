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
def get_recent_fake_news(symbol, max_articles=8):
    """
    Fake news generator for testing AI pipeline.
    Each stock gets a mix of positive and negative long-form news.
    """
    sources = []
    fake_news = []

    if symbol == "AAPL":
        fake_news = [
            {
                "title": "Apple posts record iPhone sales in Q4",
                "publisher": "Bloomberg",
                "content": (
                    "Apple reported record-breaking iPhone sales in the last quarter, "
                    "with demand surging in both North America and Asia. The company’s "
                    "services segment, including Apple Music and iCloud, also grew by 12%. "
                    "Analysts believe this shows Apple’s resilience even in a competitive market."
                )
            },
            {
                "title": "Apple faces EU antitrust fines over App Store policies",
                "publisher": "Reuters",
                "content": (
                    "The European Union has filed charges against Apple over alleged "
                    "anti-competitive practices related to its App Store policies. "
                    "If found guilty, Apple could face billions in fines. "
                    "Critics argue that these practices harm developers and limit consumer choice."
                )
            }
        ]

    elif symbol == "MSFT":
        fake_news = [
            {
                "title": "Microsoft Azure grows 30% amid AI adoption boom",
                "publisher": "CNBC",
                "content": (
                    "Microsoft announced that Azure revenues jumped 30% year-over-year, "
                    "fueled by strong demand for AI-powered cloud solutions. "
                    "Partnerships with OpenAI and enterprise adoption of AI tools like Copilot "
                    "are expected to continue boosting revenue streams."
                )
            },
            {
                "title": "Microsoft under investigation for labor practices",
                "publisher": "BBC",
                "content": (
                    "Regulators are investigating Microsoft after reports of poor working "
                    "conditions in overseas data centers. Labor rights groups have criticized "
                    "the company for not ensuring fair wages and safe conditions. "
                    "The investigation could lead to regulatory penalties and reputational damage."
                )
            }
        ]

    elif symbol == "TSLA":
        fake_news = [
            {
                "title": "Tesla unveils breakthrough battery technology",
                "publisher": "TechCrunch",
                "content": (
                    "Tesla revealed a new solid-state battery technology expected to extend "
                    "EV range by 25% while reducing charging times significantly. "
                    "Experts suggest this innovation could strengthen Tesla’s leadership in the EV industry "
                    "and give it a competitive edge over rivals like Rivian and Lucid Motors."
                )
            },
            {
                "title": "Tesla recalls 500,000 vehicles over safety concerns",
                "publisher": "Wall Street Journal",
                "content": (
                    "Tesla has issued a recall for over 500,000 vehicles due to steering system malfunctions. "
                    "Safety regulators have raised concerns about potential accidents, "
                    "and analysts fear the recall could impact consumer confidence and profitability in the short term."
                )
            }
        ]

    elif symbol == "AMZN":
        fake_news = [
            {
                "title": "Amazon Prime Day breaks sales records",
                "publisher": "Forbes",
                "content": (
                    "Amazon’s Prime Day 2025 recorded the highest sales in company history, "
                    "with consumer spending rising 18% compared to last year. "
                    "Growth was fueled by strong demand in electronics and household goods, "
                    "as well as expansion of same-day delivery services in major cities."
                )
            },
            {
                "title": "Amazon faces antitrust lawsuit in the US",
                "publisher": "New York Times",
                "content": (
                    "The U.S. Department of Justice has filed an antitrust lawsuit against Amazon, "
                    "alleging monopolistic practices in its e-commerce business. "
                    "If the case proceeds, it could result in structural changes to Amazon’s operations "
                    "and increased regulatory oversight."
                )
            }
        ]

    elif symbol == "NVDA":
        fake_news = [
            {
                "title": "NVIDIA dominates AI chip market with record profits",
                "publisher": "Financial Times",
                "content": (
                    "NVIDIA reported quarterly profits surpassing Wall Street expectations, "
                    "driven by unprecedented demand for its AI GPUs in both data centers and autonomous vehicles. "
                    "The company has secured new contracts with major tech firms, solidifying its leadership in AI hardware."
                )
            },
            {
                "title": "NVIDIA sued for alleged patent infringement",
                "publisher": "Bloomberg",
                "content": (
                    "NVIDIA is facing a patent infringement lawsuit from a smaller competitor, "
                    "alleging unauthorized use of proprietary GPU designs. "
                    "If successful, the lawsuit could result in significant financial penalties or licensing costs, "
                    "potentially affecting NVIDIA’s margins."
                )
            }
        ]

    # Collect all publishers automatically
    sources = [n["publisher"] for n in fake_news]

    return {"news": fake_news, "sources": sources}


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
    # try:
    #     bing_key = os.getenv("BING_NEWS_API_KEY")
    #     if bing_key:
    #         before = len(out)
    #         headers = {"Ocp-Apim-Subscription-Key": bing_key}
    #         for q in queries:
    #             params = {
    #                 "q": q,
    #                 "mkt": "en-US",
    #                 "freshness": "Week",
    #                 "count": max_articles,
    #                 "safeSearch": "Off"
    #             }
    #             r = requests.get("https://api.bing.microsoft.com/v7.0/news/search",
    #                              headers=headers, params=params, timeout=6)
    #             if r.status_code == 200:
    #                 data = r.json()
    #                 for art in data.get("value", []):
    #                     title = art.get("name")
    #                     link = art.get("url")
    #                     publisher = ""
    #                     prov = art.get("provider") or []
    #                     if prov and isinstance(prov, list) and prov[0].get("name"):
    #                         publisher = prov[0]["name"]
    #                     pub_ts = None
    #                     dp = art.get("datePublished")
    #                     if dp:
    #                         try:
    #                             from dateutil import parser as dtp
    #                             pub_ts = _epoch(dtp.isoparse(dp))
    #                         except Exception:
    #                             pass
    #                     _add(title, publisher, link, pub_ts)
    #         if len(out) > before:
    #             used_sources.add("Bing News")
    # except Exception:
    #     pass

    # --------- Provider: Finnhub (optional, API key required) ----------
    # try:
    #     finnhub_key = os.getenv("FINNHUB_API_KEY")
    #     if finnhub_key:
    #         before = len(out)
    #         date_to = datetime.utcnow().date()
    #         date_from = (datetime.utcnow() - timedelta(days=lookback_days)).date()
    #         params = {"symbol": symbol, "from": str(date_from), "to": str(date_to), "token": finnhub_key}
    #         r = requests.get("https://finnhub.io/api/v1/company-news", params=params, timeout=6)
    #         if r.status_code == 200:
    #             for it in r.json():
    #                 _add(it.get("headline"), it.get("source"), it.get("url"), it.get("datetime"))
    #         if len(out) > before:
    #             used_sources.add("Finnhub")
    # except Exception:
    #     pass
    #
    # # --------- Provider: NewsAPI.org (optional, API key required) ----------
    # try:
    #     newsapi_key = os.getenv("NEWSAPI_KEY")
    #     if newsapi_key:
    #         before = len(out)
    #         for q in queries:
    #             params = {
    #                 "q": q,
    #                 "language": "en",
    #                 "sortBy": "publishedAt",
    #                 "pageSize": max_articles,
    #                 "apiKey": newsapi_key
    #             }
    #             r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=6)
    #             if r.status_code == 200:
    #                 data = r.json()
    #                 for art in data.get("articles", []):
    #                     title = art.get("title")
    #                     link = art.get("url")
    #                     src = (art.get("source") or {}).get("name")
    #                     pub_ts = None
    #                     dp = art.get("publishedAt")
    #                     if dp:
    #                         try:
    #                             from dateutil import parser as dtp
    #                             pub_ts = _epoch(dtp.isoparse(dp))
    #                         except Exception:
    #                             pass
    #                     _add(title, src, link, pub_ts)
    #         if len(out) > before:
    #             used_sources.add("NewsAPI")
    # except Exception:
    #     pass

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


# --------------------- AI Analysis that gives top 5 from 50 ---------------------
def analyze_stock(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    hist = stock.history(period="7d")
    news_result = get_recent_news(symbol, max_articles=10)
    news_items = news_result["news"]
    sources_used = news_result["sources"]

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
        news_result = get_recent_fake_news(symbol, max_articles=8)
        news_items = news_result["news"]

        # Prepare news content for GPT
        news_list = "\n\n".join([
            f"{i+1}. Title: {n['title']}\n   Content: {n.get('content','')}"
            for i, n in enumerate(news_items)
        ])

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



# if __name__ == "__main__":
#     main()
if __name__ == "__main__":
    top5 = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"]
    print(aiAnalyzeTopFiveStocks(top5))
