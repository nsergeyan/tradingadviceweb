import pandas as pd

import backend.final_strat as final_strategy


def _stub_fetch(symbol, info_type, limit=None):
    return pd.DataFrame({"close": [100, 101]})


def _setup_common(monkeypatch, bos_values, fvg_values, orb_values):
    monkeypatch.setattr(final_strategy, "bos_strat", lambda cash, symbol: bos_values)
    monkeypatch.setattr(final_strategy, "fair_value_gaps_strategy", lambda df: fvg_values)
    monkeypatch.setattr(final_strategy, "orb_strategy", lambda df: orb_values)
    monkeypatch.setattr(final_strategy, "fetch_ohlcv", _stub_fetch)


def test_final_strategy_prefers_buy_signal(monkeypatch):
    """High combined risk should produce BUY and update weekly/daily data."""
    _setup_common(
        monkeypatch,
        (120, 2, 0.4, "BOS"),
        (115, 2, 0.2),
        (118, 2, 0.1),
    )

    called = {}

    def fake_update(symbol, info_type):
        called.setdefault("args", []).append((symbol, info_type))

    monkeypatch.setattr(final_strategy, "update_ohlcv", fake_update)

    result = final_strategy.final_strategy(1000, "AAA")

    assert result["decision"] == "BUY"
    assert result["avg_risk"] == 2.0
    assert result["avg_gains"] == round(0.4 * 0.6 + 0.2 * 0.2 + 0.1 * 0.2, 2)
    assert called["args"] == [("AAA", "Daily")]


def test_final_strategy_flags_cautious_buy(monkeypatch):
    """Intermediate risk needs BUY (caution) and weighted risk within range."""
    _setup_common(
        monkeypatch,
        (120, 2, 0.5, "BOS"),
        (110, 1, 0.1),
        (108, 0, 0.0),
    )
    monkeypatch.setattr(final_strategy, "update_ohlcv", lambda *args, **kwargs: None)

    result = final_strategy.final_strategy(500, "BBB")

    assert result["decision"] == "BUY (caution)"
    assert 1.0 <= result["avg_risk"] < 1.5


def test_final_strategy_rejects_high_risk(monkeypatch):
    """Low component risks must result in DO NOT BUY decision."""
    _setup_common(
        monkeypatch,
        (120, 0, 0.0, "BOS"),
        (110, 0, 0.0),
        (108, 0, 0.0),
    )
    monkeypatch.setattr(final_strategy, "update_ohlcv", lambda *args, **kwargs: None)

    result = final_strategy.final_strategy(500, "CCC")

    assert result["decision"] == "DO NOT BUY"
    assert result["avg_risk"] < 1.0
