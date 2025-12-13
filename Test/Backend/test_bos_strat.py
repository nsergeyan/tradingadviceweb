import pandas as pd
import pytest

import backend.bos_strat as bos_module


def _df_for(values):
    return pd.DataFrame(values, columns=["open", "close", "high", "low", "volume"])


def _patch_data(monkeypatch, rows):
    monkeypatch.setattr(bos_module, "fetch_ohlcv", lambda *args, **kwargs: _df_for(rows))
    monkeypatch.setattr(bos_module, "update_ohlcv", lambda *args, **kwargs: None)


def test_bos_strat_requires_three_rows(monkeypatch):
    """Return None tuple when there is not enough OHLC data."""
    rows = [
        [100, 101, 102, 99, 1000],
        [101, 102, 103, 100, 1100],
    ]
    _patch_data(monkeypatch, rows)

    result = bos_module.bos_strat(1000, "AAA")

    assert result == [None, None, None]


def test_bos_strat_full_bullish_signal(monkeypatch):
    """Confirm bullish structure yields risk 2 and proper gain calc."""
    rows = [
        [100, 101, 102, 99, 1000],
        [102, 104, 105, 101, 1000],
        [105, 108, 110, 104, 1000],
    ]
    _patch_data(monkeypatch, rows)

    price, risk, gains, signal = bos_module.bos_strat(1000, "AAA")

    assert price == 108
    assert risk == 2
    assert signal == "BUY (risk level = low)"
    assert gains == pytest.approx((110 - 104) / 104)


def test_bos_strat_partial_bullish_signal(monkeypatch):
    """Mixed higher highs/lows should give medium risk signal."""
    rows = [
        [100, 101, 105, 99, 1000],
        [102, 101, 104, 100, 1000],
        [103, 105, 108, 98, 1000],
    ]
    _patch_data(monkeypatch, rows)

    price, risk, gains, signal = bos_module.bos_strat(500, "BBB")

    assert risk == 1
    assert signal == "BUY (risk level = medium)"
    assert gains == pytest.approx((105 - 101) / 101)


def test_bos_strat_no_bullish_signal(monkeypatch):
    """Descending structure should produce sell signal and zero gains."""
    rows = [
        [105, 102, 107, 100, 1000],
        [103, 101, 104, 99, 1000],
        [101, 100, 103, 98, 1000],
    ]
    _patch_data(monkeypatch, rows)

    price, risk, gains, signal = bos_module.bos_strat(500, "CCC")

    assert risk == 0
    assert gains == 0.0
    assert signal == "SELL/DO NOT BUY"
