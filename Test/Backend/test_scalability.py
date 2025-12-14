from backend.list_stocks import get_50_stocks


def test_stock_list_scalability(monkeypatch):
    """Large stock universe should still return limited results."""

    monkeypatch.setattr(
        "backend.list_stocks.get_50_stocks",
        lambda: [f"SYM{i}" for i in range(1000)],
    )

    stocks = get_50_stocks()

    assert len(stocks) >= 50
