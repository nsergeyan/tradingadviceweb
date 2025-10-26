import pytest
from unittest.mock import patch, MagicMock
from backend.aiAnalyzer.deep_research import aiAnalyzeTopFiveStocks
import pandas as pd

# ---------- Mocks ----------

@pytest.fixture
def mock_yfinance():
    with patch("backend.aiAnalyzer.deep_research.yf.Ticker") as mock_ticker:
        ticker = MagicMock()
        ticker.info = {"longName": "MockCorp", "exchange": "NMS"}
        ticker.history.return_value = pd.DataFrame({"Close": [100, 101, 102]})
        mock_ticker.return_value = ticker
        yield mock_ticker

@pytest.fixture
def mock_news():
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
    with patch("backend.aiAnalyzer.deep_research.client.chat.completions.create") as mock_openai_func:
        yield mock_openai_func

@pytest.fixture
def mock_gemini():
    with patch("backend.aiAnalyzer.deep_research.requests.post") as mock_post:
        yield mock_post

@pytest.fixture
def mock_initial_ranking():
    with patch("backend.aiAnalyzer.deep_research.initial_stock_ranking") as mock_ranking:
        mock_ranking.return_value = ["MOCK1", "MOCK2", "MOCK3", "MOCK4", "MOCK5"]
        yield mock_ranking

# ---------- Tests ----------

def test_openai_success(mock_initial_ranking, mock_yfinance, mock_news, mock_openai):
    mock_openai.return_value.choices = [
        MagicMock(message=MagicMock(content="Mock AI Analysis"))
    ]

    result = aiAnalyzeTopFiveStocks()

    assert "Mock AI Analysis" in result
    mock_yfinance.assert_called()
    mock_news.assert_called()

def test_openai_failure_then_gemini_success(mock_initial_ranking, mock_yfinance, mock_news, mock_openai, mock_gemini):
    mock_openai.side_effect = Exception("OpenAI down")

    mock_gemini.return_value.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Gemini AI Analysis"}]}}]
    }
    mock_gemini.return_value.raise_for_status = lambda: None

    result = aiAnalyzeTopFiveStocks()
    assert "Gemini AI Analysis" in result
    mock_gemini.assert_called_once()

def test_both_apis_fail(mock_initial_ranking, mock_yfinance, mock_news, mock_openai, mock_gemini):
    mock_openai.side_effect = Exception("OpenAI error")
    mock_gemini.side_effect = Exception("Gemini network error")

    result = aiAnalyzeTopFiveStocks()
    assert "Both AI services failed" in result

def test_empty_news(mock_initial_ranking, mock_yfinance, mock_openai):
    with patch("backend.aiAnalyzer.deep_research.get_recent_news", return_value={"news": [], "sources": []}):
        mock_openai.return_value.choices = [
            MagicMock(message=MagicMock(content="Empty news analysis"))
        ]
        result = aiAnalyzeTopFiveStocks()

    assert "Empty news analysis" in result
