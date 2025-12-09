import pandas as pd
import pytest

from backend.orb_strategy import orb_strategy


def _df(values):
    return pd.DataFrame(values, columns=["open", "high", "low", "close"])


def test_orb_strategy_without_breakout_is_neutral():
    """If no breakout occurs the strategy should stay neutral."""
    data = _df([
        (100, 104, 98, 102),
        (101, 105, 99, 103),
        (103, 104, 100, 103),
        (104, 105, 101, 103.5),
        (103.5, 104.5, 100.5, 103.4),
    ])

    price, risk, gains = orb_strategy(data)

    assert price == pytest.approx(103.4)
    assert risk == 0
    assert gains == 0.0


def test_orb_strategy_breakout_with_increasing_trend():
    """Uptrend past the opening range must trigger aggressive buy output."""
    data = _df([
        (100, 105, 99, 104),
        (101, 104, 98, 102),
        (103, 106, 101, 104.5),
        (104.5, 107, 103, 106),
        (106, 109, 104, 108),
    ])

    price, risk, gains = orb_strategy(data)

    assert risk == 2
    assert price > data.iloc[-1]["close"]
    assert gains > 0


def test_orb_strategy_all_decreasing_branch():
    """All bearish candles should lower price expectations and keep risk 0."""
    data = _df([
        (120, 125, 115, 122),
        (121, 124, 116, 118),
        (118, 122, 94, 115),
        (115, 118, 93, 110),
        (110, 116, 92, 105),
    ])

    price, risk, gains = orb_strategy(data)

    assert risk == 0
    assert price < data.iloc[-1]["close"]
    assert gains == 0.0


def test_orb_strategy_mixed_increasing_branch():
    """Mixed candles ending above range should award a bullish follow-up."""
    data = _df([
        (100, 106, 95, 104),
        (102, 105, 96, 100),
        (101, 110, 97, 107),
        (106, 112, 98, 105),
        (120, 125, 110, 112),
    ])

    price, risk, gains = orb_strategy(data)

    assert risk == 2
    assert price > data.iloc[-1]["close"]
    assert gains > 0


def test_orb_strategy_last_below_range_branch():
    """Downside breakout path should degrade price yet keep gains positive."""
    data = _df([
        (150, 160, 140, 158),
        (152, 158, 145, 150),
        (151, 170, 142, 160),
        (160, 165, 130, 140),
        (140, 150, 120, 125),
    ])

    price, risk, gains = orb_strategy(data)

    assert risk == 1
    assert price > data.iloc[-1]["close"]
    assert gains > 0


def test_orb_strategy_else_branch_handles_neutral_close():
    """Neutral close branch should exit with zero gain and non-positive price delta."""
    data = _df([
        (90, 95, 85, 94),
        (92, 94, 86, 90),
        (90, 101, 80, 85),
        (85, 100, 83, 88),
        (94, 94, 90, 94),
    ])

    price, risk, gains = orb_strategy(data)

    assert risk == 0
    assert gains == 0.0
    assert price <= data.iloc[-1]["close"]
