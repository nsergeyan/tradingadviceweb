import time
import threading

from backend.final_strat import final_strategy


def test_final_strategy_performance(monkeypatch):
    """Ensure final_strategy executes within acceptable time."""

    monkeypatch.setattr(
        "backend.final_strat.fetch_ohlcv",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "backend.final_strat.bos_strat",
        lambda *args, **kwargs: (100, 1, 0.1, "BOS"),
    )
    monkeypatch.setattr(
        "backend.final_strat.fair_value_gaps_strategy",
        lambda *args, **kwargs: (100, 1, 0.1),
    )
    monkeypatch.setattr(
        "backend.final_strat.orb_strategy",
        lambda *args, **kwargs: (100, 1, 0.1),
    )
    monkeypatch.setattr(
        "backend.final_strat.update_ohlcv",
        lambda *args, **kwargs: None,
    )

    start = time.time()
    final_strategy(1000, "AAA")
    duration = time.time() - start

    assert duration < 1.0
