import yfinance as yf
import requests
from openai import OpenAI
import calendar
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlencode, parse_qs, urlsplit, urlunsplit, quote_plus
from newspaper import Article
from backend.list_stocks import get_50_stocks
from backend.aiAnalyzer import prompt_ai

# Set your OpenAI API key
# You can put your own api if you have a better one
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
    Faster version: collects metadata first, then resolves URLs + fetches article content in parallel.
    Returns:
      {
        "news": [ {title, publisher, link, timestamp, content, paywalled}, ... ],
        "sources": [...]
      }
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # -------- tuning knobs --------NEW
    MAX_PER_SOURCE = max_articles           # per-source cap
    MAX_WORKERS = 8                         # parallel fetchers
    FETCH_TIMEOUT = 8                       # seconds per HTTP
    HEADERS = {"User-Agent": "Mozilla/5.0"}

    # -------- caches (per run) --------NEW
    RESOLVE_CACHE = {}
    CONTENT_CACHE = {}

    out, used_sources = [], set()
    candidates = []  # stage-1 raw items (title, publisher, link, ts)
    seen_titles, seen_links = set(), set()
    look_from = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    PAYWALLED_DOMAINS = {"seekingalpha.com", "mtnewswires.com"}

    def _is_paywalled(url: str) -> bool:
        try:
            host = urlparse(url).netloc.lower()
            return any(d in host for d in PAYWALLED_DOMAINS)
        except Exception:
            return False

    def _epoch(dt: datetime) -> int:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())

    def _strip_tracking(u: str) -> str:
        try:
            parts = urlsplit(u)
            q = parse_qs(parts.query)
            safe_q = {k: v for k, v in q.items() if not k.lower().startswith(("utm_", "gclid", "fbclid", "mc_cid", "mc_eid"))}
            new_query = urlencode([(k, vv) for k, vs in safe_q.items() for vv in vs])
            return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, new_query, ""))
        except Exception:
            return u

    def _resolve_url(u: str) -> str:
        """Follow redirects and unwrap Google News 'rss/articles' links.NEW"""
        if not u:
            return u
        if u in RESOLVE_CACHE:
            return RESOLVE_CACHE[u]
        try:
            p = urlparse(u)
            if "news.google.com" in p.netloc and "/rss/" in p.path:
                qs = parse_qs(p.query)
                if "url" in qs and qs["url"]:
                    RESOLVE_CACHE[u] = qs["url"][0]
                    return RESOLVE_CACHE[u]
            r = requests.get(u, headers=HEADERS, timeout=FETCH_TIMEOUT, allow_redirects=True)
            RESOLVE_CACHE[u] = r.url
            return RESOLVE_CACHE[u]
        except Exception:
            RESOLVE_CACHE[u] = u
            return u

    def _fetch_article_content(url: str) -> str:
        """Try newspaper3k, then fallback to trafilatura. Cached per final URL."""
        if not url:
            return ""
        if url in CONTENT_CACHE:
            return CONTENT_CACHE[url]
        # newspaper3k
        try:
            art = Article(url)
            art.download()
            art.parse()
            txt = (art.text or "").strip()
            if txt:
                CONTENT_CACHE[url] = txt
                return txt
        except Exception:
            pass
        # trafilatura fallback NEW for extracting more data
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url, no_ssl=True, timeout=FETCH_TIMEOUT)
            txt = trafilatura.extract(downloaded, include_comments=False, include_tables=False) if downloaded else ""
            if txt:
                CONTENT_CACHE[url] = txt.strip()
                return CONTENT_CACHE[url]
        except Exception:
            pass
        CONTENT_CACHE[url] = ""
        return ""

    # --- setup: try to get company name for better queries ---
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
        queries, comp_name = [symbol], ""

    # --------- Provider: Yahoo Finance (stage-1: metadata only) ----------
    try:
        before = len(candidates)
        for q in queries:
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={quote_plus(q)}"
            resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            for item in (data.get("news") or [])[:MAX_PER_SOURCE]:
                ts = item.get("providerPublishTime")
                pub_ts = int(ts) if isinstance(ts, (int, float)) and ts and ts > 0 else None
                title = item.get("title")
                link = item.get("link")
                publisher = item.get("publisher")
                if title and link and pub_ts:
                    candidates.append((title, publisher, link, pub_ts))
        if len(candidates) > before:
            used_sources.add("Yahoo Finance")
    except Exception:
        pass

    # --------- Provider: Google News (RSS) ----------
    try:
        import feedparser
        before = len(candidates)
        rss_q = quote_plus(f'("{symbol}" OR "{comp_name}" OR "NASDAQ:{symbol}")') if len(queries) > 1 else quote_plus(f'"{symbol}" OR "NASDAQ:{symbol}"')
        rss_url = (
            f"https://news.google.com/rss/search?q={rss_q}+when:{lookback_days}d"
            f"&hl={lang}&gl={region.split('-')[0] if '-' in region else region}&ceid={region}:{lang.split('-')[0]}"
        )
        feed = feedparser.parse(rss_url)
        for e in feed.entries[:MAX_PER_SOURCE * 2]:
            title = getattr(e, "title", None)
            link = getattr(e, "link", None)
            pub_ts = None
            if getattr(e, "published_parsed", None):
                pub_ts = calendar.timegm(e.published_parsed)
            elif getattr(e, "updated_parsed", None):
                pub_ts = calendar.timegm(e.updated_parsed)
            if title and link and pub_ts:
                candidates.append((title, "", link, pub_ts))
        if len(candidates) > before:
            used_sources.add("Google News")
    except Exception:
        pass

    # --------- Stage-2: dedupe + filter by lookback ----------NEW
    min_ts = _epoch(look_from)
    filtered = []
    for title, publisher, link, ts in candidates:
        if ts and ts >= min_ts:
            norm_title = title.strip().lower()
            norm_link = _strip_tracking(link)
            if norm_title in seen_titles or norm_link in seen_links:
                continue
            seen_titles.add(norm_title)
            seen_links.add(norm_link)
            filtered.append((title, publisher, norm_link, ts))

    # --------- Stage-3: resolve + fetch content in parallel ----------NEW
    def _process_item(item):
        title, publisher, link, ts = item
        # resolve redirects
        final_link = _resolve_url(link)
        # optional early skip for paywalls (ускоряет, если не нужен paywalled контент)
        # if _is_paywalled(final_link):
        #     return None
        # fetch content
        content = _fetch_article_content(final_link)
        # relevance check (symbol or company name must appear in title/content)
        text_check = f"{title.lower()} {content.lower()}"
        if symbol.lower() not in text_check and (comp_name and comp_name.lower() not in text_check):
            return None
        return {
            "title": title.strip(),
            "publisher": (publisher or "").strip(),
            "link": final_link,
            "timestamp": ts,
            "content": content,
            "paywalled": _is_paywalled(final_link),
        }

    results = []
    if filtered:
        # keep a little headroom so we don't overfetch way more than needed
        filtered = filtered[: max_articles * 4]

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = [ex.submit(_process_item, it) for it in filtered]
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    if res:
                        results.append(res)
                except Exception:
                    pass

    # --------- Stage-4: sort + final slice ----------NEW
    if results:
        results.sort(key=lambda x: x["timestamp"], reverse=True)
        results = results[:max_articles]

    return {"news": results, "sources": sorted(list(used_sources))}


def initial_stock_ranking() -> list:

    stocks = get_50_stocks()[:10]
    prompt = """You are the worlds best trading advisor. You are having a meeting soon, and need to do in initial assessment of 15 stocks that have been of interest.
    Of those, you need rank them from worst to best (to invest in). You will be given some news on which to bace your assessment.  Return a simple list, with the stock symbols separated by a comma, and nothing else. The list starts with the worst, and ends with the best."""


    for stock in stocks:
        news_items = get_recent_news(stock, 3)["news"]
        news = "\n".join([f"{i + 1}. {n['title']} ({n['publisher']})" for i, n in enumerate(news_items)])

        print(f"{stock} news loaded")
        prompt += f"\n {stock}: \n {news}"

    print("sending")

    try:
        output = prompt_ai.gpt(prompt)
    except Exception as e:
        print(f"{e}, trying gemini")
        try:
            output = prompt_ai.gemini(prompt)
        except Exception as e:
            raise ValueError("Ai is unavalible, please try again later") #I used a random error for now, can make coustom later if needed


    return [s.strip() for s in output.split(",")[:5]]




# --------------------- Ai2 ---------------------
def aiAnalyzeTopFiveStocks(stock: str):
    """
    Analyze top 5 stocks using recent news (titles + full content) and AI reasoning.
    Input: list of 5 stock symbols
    Output: GPT-generated detailed analysis for all 5 stocks
    """
    # stocks = get_50_stocks()[:5]
    stocks = [stock]
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

        # NEW Console output with reason for empty content
        print("\nFull article content:\n")
        for i, n in enumerate(news_items, 1):
            print(f"[{i}] {n['title']}")
            print(f"Publisher: {n.get('publisher', '')}")
            print(f"URL: {n.get('link', '')}")
            if not n.get("content"):
                note = " (paywalled)" if n.get("paywalled") else " (no content extracted)"
                print(f"[!] Empty content{note}\n")
            else:
                print()
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
    DONT SAY "Here's an analysis of"
You are a financial analyst AI. YOU HAVE  TO WRITE DOWN THE SUMMARY OF THE NEWS FOR EACH STOCK.

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
   
### Tone and Style:
- Use bullet points and short sections.
- Be clear, simple, and structured.
- Always connect your recommendation directly to the news.

**IMPORTANT:** At the end of your analysis for each stock, **list all news sources (publishers) used** in a section called **Sources**.
DO NOT SAY HERE ARE THE ANALYSIS. JUST GO STRAIGHT TO ANALYSIS.
Stocks to analyze:
{chr(10).join(all_summaries)}
"""
    output_text = prompt_ai.local_llm(combined_prompt)
    return output_text


if __name__ == "__main__":
    print(aiAnalyzeTopFiveStocks(get_50_stocks()[1]))
