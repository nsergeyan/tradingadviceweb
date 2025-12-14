import os
import pytest

os.environ.setdefault("DATABASE_PATH", ":memory:")
os.environ.setdefault("ALPHAVANTAGE_API_KEY", "demo")

import backend.list_stocks as list_stocks

@pytest.fixture
def stock_data_dir(tmp_path, monkeypatch):
    module_file = tmp_path / "list_stocks.py"
    module_file.write_text("")
    monkeypatch.setattr(list_stocks, "__file__", str(module_file))
    data_dir = tmp_path / "DbForStockUpdate"
    data_dir.mkdir()
    stocks_csv = data_dir / "stocks.csv"
    stocks_csv.write_text("Symbol\nAAA\nBBB\nCCC\n")
    return data_dir
