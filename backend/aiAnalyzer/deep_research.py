import yfinance as yf
import requests
from openai import OpenAI

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
def get_recent_news(symbol, max_articles=10):
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print("Error fetching news:", e)
        return []

    news_items = data.get("news", [])
    headlines = []
    for item in news_items[:max_articles]:
        headlines.append({
            "title": item.get("title"),
            "publisher": item.get("publisher"),
            "link": item.get("link"),
            "timestamp": item.get("providerPublishTime")
        })
    return headlines

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
    news_items = get_recent_news(symbol, max_articles=10)

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