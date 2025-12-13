import threading

from backend.final_strat import final_strategy


def test_final_strategy_load(monkeypatch):
    """Multiple concurrent calls should not crash."""

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

    threads = []

    for i in range(20):
        t = threading.Thread(target=final_strategy, args=(1000, f"SYM{i}"))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert True
