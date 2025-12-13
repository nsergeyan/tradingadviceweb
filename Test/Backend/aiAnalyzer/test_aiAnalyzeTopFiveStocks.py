# Updated unit tests reflecting new deep_research.aiAnalyzeTopFiveStocks behavior
# using local_llm instead of OpenAI/Gemini

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
                    "paywalled": False,
                }
            ],
            "sources": ["Mock Times"],
        }
        yield mock_news_func


# ---------- Tests ----------


def test_llm_success(mock_yfinance, mock_news):
    """Ensure that local_llm is called and returns expected output."""
    with patch("backend.aiAnalyzer.deep_research.prompt_ai.local_llm", return_value="Mock Local LLM Output") as mock_llm:
        result = aiAnalyzeTopFiveStocks("MOCK")
        assert "Mock Local LLM Output" in result
        mock_llm.assert_called_once()
        mock_yfinance.assert_called()
        mock_news.assert_called()


def test_llm_failure_raises_exception(mock_yfinance, mock_news):
    """If local_llm fails, the exception should propagate upward."""
    with patch("backend.aiAnalyzer.deep_research.prompt_ai.local_llm",
               side_effect=Exception("LLM crashed")):
        with pytest.raises(Exception) as exc:
            aiAnalyzeTopFiveStocks("MOCK")

        assert "LLM crashed" in str(exc.value)


def test_empty_news(mock_yfinance):
    """Handles the case where no news articles exist."""
    with patch("backend.aiAnalyzer.deep_research.get_recent_news", return_value={"news": [], "sources": []}), \
         patch("backend.aiAnalyzer.deep_research.prompt_ai.local_llm", return_value="Empty news analysis"):
        result = aiAnalyzeTopFiveStocks("MOCK")
        assert "Empty news analysis" in result
