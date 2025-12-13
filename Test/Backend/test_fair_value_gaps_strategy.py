import pandas as pd
import pytest

import backend.fair_value_gaps_strategy as fvg


def test_fvg_returns_default_without_gap():
    """No qualifying gaps should leave the default latest-close signal."""
    df = pd.DataFrame(
        [
            {"open": 10, "close": 10.2, "high": 10.5, "low": 9.8},
            {"open": 10.3, "close": 10.4, "high": 10.8, "low": 10.1},
            {"open": 10.5, "close": 10.6, "high": 11, "low": 10.2},
        ]
    )

    estimate, risk, gains = fvg.fair_value_gaps_strategy(df.copy(), threshold=0.95)

    assert estimate == pytest.approx(df["close"].iloc[-1])
    assert risk == 0
    assert gains == 0.0


def test_fvg_detects_recent_bullish_gap():
    """Recent bullish gap should raise risk and gains due to upper gap."""
    df = pd.DataFrame(
        [
            {"open": 10, "close": 11, "high": 11.5, "low": 9.8},
            {"open": 11, "close": 10.5, "high": 11.2, "low": 10.3},
            {"open": 10.6, "close": 10.4, "high": 11, "low": 10.2},
            {"open": 11.5, "close": 13.5, "high": 14.5, "low": 11.4},
            {"open": 13.4, "close": 13.6, "high": 15.5, "low": 12.8},
        ]
    )

    estimate, risk, gains = fvg.fair_value_gaps_strategy(df.copy(), threshold=0.1, max_bars=3)

    assert risk == 2
    assert estimate > df.loc[2, "high"]
    assert gains > 0


def test_fvg_detects_bearish_gap():
    """Bearish gap path should still emit nonzero risk and gains."""
    df = pd.DataFrame(
        [
            {"open": 20, "close": 19.8, "high": 20.2, "low": 19.5},
            {"open": 19.5, "close": 19.7, "high": 20, "low": 19.4},
            {"open": 19.6, "close": 17.5, "high": 19.8, "low": 17.4},
            {"open": 18.2, "close": 16.2, "high": 16.4, "low": 15.9},
            {"open": 16, "close": 16.5, "high": 16.8, "low": 15.2},
        ]
    )

    estimate, risk, gains = fvg.fair_value_gaps_strategy(df.copy(), threshold=0.2, max_bars=4)

    assert risk in (1, 2)
    assert estimate > df.loc[2, "low"]
    assert gains > 0
