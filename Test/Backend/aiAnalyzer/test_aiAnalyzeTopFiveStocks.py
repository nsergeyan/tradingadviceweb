import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.aiAnalyzer.deep_research import aiAnalyzeTopFiveStocks


# ---------- Fixtures ----------

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
def mock_initial_ranking():
    with patch("backend.aiAnalyzer.deep_research.initial_stock_ranking") as mock_ranking:
        mock_ranking.return_value = ["MOCK1", "MOCK2", "MOCK3", "MOCK4", "MOCK5"]
        yield mock_ranking


# ---------- Tests ----------

def test_openai_success(mock_initial_ranking, mock_yfinance, mock_news):
    """Ensure OpenAI (gpt) is called successfully."""
    with patch("backend.prompt_ai.gpt", return_value="Mock AI Analysis") as mock_gpt:
        result = aiAnalyzeTopFiveStocks()
        assert "Mock AI Analysis" in result
        mock_gpt.assert_called_once()
        mock_yfinance.assert_called()
        mock_news.assert_called()


def test_openai_failure_then_gemini_success(mock_initial_ranking, mock_yfinance, mock_news):
    """If OpenAI fails, Gemini should be used instead."""
    with patch("backend.prompt_ai.gpt", side_effect=Exception("OpenAI down")) as mock_gpt, \
         patch("backend.prompt_ai.gemini", return_value="Gemini AI Analysis") as mock_gemini:
        result = aiAnalyzeTopFiveStocks()
        assert "Gemini AI Analysis" in result
        mock_gpt.assert_called_once()
        mock_gemini.assert_called_once()


def test_both_apis_fail(mock_initial_ranking, mock_yfinance, mock_news):
    """If both AI services fail, fallback message should appear."""
    with patch("backend.prompt_ai.gpt", side_effect=Exception("OpenAI down")), \
         patch("backend.prompt_ai.gemini", side_effect=Exception("Gemini error")):
        result = aiAnalyzeTopFiveStocks()
        assert "Both AI services failed" in result


def test_empty_news(mock_initial_ranking, mock_yfinance):
    """Handles case when no news articles are available."""
    with patch("backend.aiAnalyzer.deep_research.get_recent_news", return_value={"news": [], "sources": []}), \
         patch("backend.prompt_ai.gpt", return_value="Empty news analysis"):
        result = aiAnalyzeTopFiveStocks()
        assert "Empty news analysis" in result
