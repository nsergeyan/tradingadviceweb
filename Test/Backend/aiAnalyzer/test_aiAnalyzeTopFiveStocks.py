import pytest
from unittest.mock import patch, MagicMock
from backend.aiAnalyzer.deep_research import aiAnalyzeTopFiveStocks
import pandas as pd


# ---------- Shared fixtures ----------

@pytest.fixture
def stocks():
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]


@pytest.fixture
def mock_yfinance():
    """Mock yfinance.Ticker behavior."""
    with patch("backend.aiAnalyzer.deep_research.yf.Ticker") as mock_ticker:
        ticker = MagicMock()
        ticker.info = {"longName": "MockCorp", "exchange": "NMS"}
        ticker.history.return_value = pd.DataFrame({"Close": [100, 101, 102]})
        mock_ticker.return_value = ticker
        yield mock_ticker


@pytest.fixture
def mock_news():
    """Mock get_recent_news() to return fake data."""
    with patch("backend.aiAnalyzer.deep_research.get_recent_news") as mock_news_func:
        mock_news_func.return_value = {
            "news": [
                {
                    "title": "Mock Stock jumps after earnings",
                    "publisher": "Mock Times",
                    "link": "http://mocknews.com/article1",
                    "content": "Mock content of the article.",
                }
            ],
            "sources": ["Mock Times"],
        }
        yield mock_news_func


@pytest.fixture
def mock_openai():
    """Mock OpenAI API client."""
    with patch("backend.aiAnalyzer.deep_research.client.chat.completions.create") as mock_openai_func:
        yield mock_openai_func


@pytest.fixture
def mock_gemini():
    """Mock Gemini API (requests.post)."""
    with patch("backend.aiAnalyzer.deep_research.requests.post") as mock_post:
        yield mock_post


# ---------- Actual tests ----------

def test_openai_success(stocks, mock_yfinance, mock_news, mock_openai):
    mock_openai.return_value.choices = [
        MagicMock(message=MagicMock(content="Mock AI Analysis"))
    ]

    result = aiAnalyzeTopFiveStocks(stocks)

    assert "Mock AI Analysis" in result
    mock_yfinance.assert_called()
    mock_news.assert_called()


def test_openai_failure_then_gemini_success(stocks, mock_yfinance, mock_news, mock_openai, mock_gemini):
    mock_openai.side_effect = Exception("OpenAI down")

    mock_gemini.return_value.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Gemini AI Analysis"}]}}],
    }
    mock_gemini.return_value.raise_for_status = lambda: None

    result = aiAnalyzeTopFiveStocks(stocks)
    assert "Gemini AI Analysis" in result
    mock_gemini.assert_called_once()


def test_both_apis_fail(stocks, mock_yfinance, mock_news, mock_openai, mock_gemini):
    mock_openai.side_effect = Exception("OpenAI error")
    mock_gemini.side_effect = Exception("Gemini network error")

    result = aiAnalyzeTopFiveStocks(stocks)
    assert "Both AI services failed" in result


def test_empty_news(stocks, mock_yfinance, mock_openai):
    with patch("backend.aiAnalyzer.deep_research.get_recent_news", return_value={"news": [], "sources": []}):
        mock_openai.return_value.choices = [
            MagicMock(message=MagicMock(content="Empty news analysis"))
        ]
        result = aiAnalyzeTopFiveStocks(stocks)

    assert "Empty news analysis" in result
