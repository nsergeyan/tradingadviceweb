import pandas as pd

from backend.database.crud import fetch_ohlcv


# https://www.mql5.com/en/articles/14261
def fair_value_gaps_strategy(df: pd.DataFrame, threshold=0.7, max_bars=5):
    """
    Fair Value Gaps (FVG) based on candlestick data.

    :param df: OHLCV DataFrame with columns ["open", "high", "low", "close"].
    :param threshold: Minimum ratio of body size / full candle range to consider a "big candle".
    :param max_bars: Maximum number of bars after the FVG is formed to still consider it valid.
    :return: A list of signals in the format:
             [estimate_price, risk_level, estimated_gains]
             - estimate_price: next estimated price based on FVG
             - risk_level: 0=no signal, 1=weak signal, 2=strong signal
             - estimated_gains: expected gains by this strategy
    """

    # default signal: latest close, risk=0, no gains
    signals = [[float(df["close"].iloc[-1]), 0,  0.0]]

    # calculate each candle body size
    body = (df["close"] - df["open"]).abs()
    # each candle range (high - low), avoid divide-by-zero
    full_range = (df["high"] - df["low"]).replace(0, 1e-9)

    # body to total ratio
    df["big_ratio"] = (body / full_range)
    # mark big candle
    df["big_candle"] = df["big_ratio"] >= threshold

    # ignore first and last to avoid getting None prev or next
    for i in range(1, len(df)-1):
        # only consider big candles within max_bars distance from the latest bar
        if df.loc[i, "big_candle"] and (len(df)-1- i) <= max_bars:
            prev = df.iloc[i-1]
            nxt = df.iloc[i+1]

            # time decay factor (recent fvg signal aris more relevant)
            time_ratio = (max_bars - (len(df) - i) + 1) / max_bars

            # bullish
            if prev["high"] < nxt["low"]:
                gap_size = nxt["low"] - prev["high"]
                risk = 2 if df.loc[i, "close"] > df.loc[i, "open"] else 1

                signals.append([
                    float(prev["high"] * (1 + df.loc[i, "big_ratio"]/10)),
                    risk,
                    float(gap_size * time_ratio)
                ])

            # bearish
            elif prev["low"] > nxt["high"]:
                gap_size = prev["low"] - nxt["high"]
                risk = 2 if df.loc[i, "close"] < df.loc[i, "open"] else 1

                signals.append([
                    float(prev["low"] * (1 + df.loc[i, "big_ratio"]/10)),
                    risk,
                    float(gap_size * time_ratio)
                ])

    return signals[-1]


if __name__ == '__main__':
    df = fetch_ohlcv("IBM", "Weekly", limit=100)
    print(fair_value_gaps_strategy(df))
