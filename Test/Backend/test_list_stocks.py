import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock

import backend.list_stocks as list_stocks


def _write_volume_file(data_dir, week, rows):
    content = [str(week), "Symbol,Volume"]
    for symbol, volume in rows:
        content.append(f"{symbol},{volume}")
    (data_dir / "stocks_volume.csv").write_text("\n".join(content))


def test_get_50_stocks_sorts_and_filters(stock_data_dir):
    """Ensure rows are filtered/sorted and only valid symbols returned."""
    current_week = datetime.now().isocalendar()[1]
    rows = [("AAA", "200"), ("BBB", " 50"), ("CCC", ""), ("DDD", "300")]
    _write_volume_file(stock_data_dir, current_week, rows)

    picked = list_stocks.get_50_stocks()

    assert picked == ["DDD", "AAA", "BBB"]


def test_get_50_stocks_triggers_update_when_outdated(stock_data_dir, monkeypatch):
    """An outdated CSV should force-update before returning sorted symbols."""
    current_week = datetime.now().isocalendar()[1]
    stale_week = 52 if current_week == 1 else current_week - 1
    rows = [("AAA", "100"), ("BBB", "200")]
    _write_volume_file(stock_data_dir, stale_week, rows)

    called = {}

    def fake_update():
        called["invoked"] = True

    monkeypatch.setattr(list_stocks, "update_stock_volume", fake_update)

    picked = list_stocks.get_50_stocks()

    assert called.get("invoked") is True
    assert picked == ["BBB", "AAA"]


def test_update_stock_volume_overwrites_csv(stock_data_dir, monkeypatch):
    """Verify volume file is rewritten with new week header and filtered symbols."""
    history = pd.DataFrame([{"Volume": 12345}], index=[0])

    def ticker_factory(symbol):
        stub = MagicMock()
        if symbol == "AAA":
            stub.history.return_value = history
        else:
            stub.history.return_value = pd.DataFrame()
        return stub

    monkeypatch.setattr(list_stocks.yf, "Ticker", ticker_factory)

    list_stocks.update_stock_volume()

    contents = (stock_data_dir / "stocks_volume.csv").read_text().strip().splitlines()
    assert contents[0] == str(datetime.now().isocalendar()[1])
    assert contents[1] == "Symbol,Volume"
    assert "AAA,12345" in contents
    assert all("BBB" not in line for line in contents[2:])
