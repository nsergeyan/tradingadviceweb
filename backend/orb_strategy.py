import pandas as pd

from backend.database.crud import fetch_ohlcv, update_ohlcv


def orb_strategy(df: pd.DataFrame):
    """
    Opening Range Breakout (ORB) based on daily candlestick data.

    :param df: OHLCV DataFrame with columns ["open", "high", "low", "close"].
    :return: A list of signals in the format:
             [estimated_price, risk_level, estimated_gains]
             - estimated_price: next estimated price based on FVG
             - risk_level: 0=no signal, 1=weak signal, 2=strong signal
             - estimated_gains: expected gains by this strategy
    """

    # Default Signal: latest_close, risk = 0, no gains
    signals = [(float(df["close"].iloc[-1]), 0, 0.0)]

    # We analise the data from the last week.
    analysis_days = df.iloc[-5:]

    or_high = max(analysis_days.iloc[0]["high"], analysis_days.iloc[1]["high"])
    or_low = min(analysis_days.iloc[0]["low"], analysis_days.iloc[1]["low"])
    or_range = or_high - or_low

    remaining_days = analysis_days.iloc[2:]

    breakout_up = False
    breakout_down = False
    trend_increases = []
    trend_decreases = []

    for i in range(len(remaining_days)):
        day_high = remaining_days.iloc[i]["high"]
        day_low = remaining_days.iloc[i]["low"]
        day_open = remaining_days.iloc[i]["open"]
        day_close = remaining_days.iloc[i]["close"]

        if day_high > or_high:
            breakout_up = True
        elif day_low < or_low:
            breakout_down = True

        if day_close > day_open:
            trend_increases.append(True)
            trend_decreases.append(False)
        elif day_close < day_open:
            trend_increases.append(False)
            trend_decreases.append(True)
        elif day_close == day_open:
            trend_increases.append(True)
            trend_decreases.append(True)

    estimated_price = float(df["close"].iloc[-1])
    risk_level = 0
    estimated_gains = 0.0

    # If there's no breakout, the value stays constant. It is not recommended to invest.
    if not breakout_up and not breakout_down:
        # estimated_price stays the same.
        risk_level = 0
        estimated_gains = 0.0

    else:
        all_increasing = all(trend_increases)
        all_decreasing = all(trend_decreases)
        last_open = remaining_days.iloc[-1]["open"]
        last_close = remaining_days.iloc[-1]["close"]
        last_change = last_close - last_open
        if last_change < 0:
            last_change *= -1

        # If there's increasing trend.
        if all_increasing is True:
            if breakout_up is True: # And breakout above the or_range.
                estimated_price = last_close + ((last_close - or_high) / 3)
                risk_level = 2
                estimated_gains = ((estimated_price - last_close) / last_close) * 100
            else: # And no breakout.
                return signals[-1]

        # If there's decreasing trend (No need to check if there's a breakout).
        elif all_decreasing is True:
            estimated_price = last_close - ((or_low - last_close) / 3)
            risk_level = 0
            estimated_gains = 0.0

        # If there's mixed trend
        else:
            if last_close > last_open:
                last_increasing = False
                last_decreasing =  True
                last_neutral = False
            elif last_close < last_open:
                last_increasing = True
                last_decreasing = False
                last_neutral = False
            elif last_close == last_open:
                last_increasing = False
                last_decreasing = False
                last_neutral = True

            if last_close > or_high:
                last_above_range = True
                last_below_range = False
            elif last_close < or_low:
                last_above_range = False
                last_below_range = True
            else:
                last_above_range = False
                last_below_range = False

            if (last_increasing is True) and (last_above_range is True):
                estimated_price = last_close + last_change
                risk_level = 2
                estimated_gains = ((estimated_price - last_close) / last_close) * 100
            elif ((last_decreasing is True) or (last_neutral is True)) and (last_above_range is True):
                estimated_price = last_close + (last_change * 0.2)
                risk_level = 1
                estimated_gains = ((estimated_price - last_close) / last_close) * 100
            elif (last_increasing is True) and (last_below_range is True):
                estimated_price = last_close + (last_change * 0.5)
                risk_level = 1
                estimated_gains = ((estimated_price - last_close) / last_close) * 100
            else:
                estimated_price = last_close - (last_change * 0.5)
                risk_level = 0
                estimated_gains = 0.0

    signals.append((float(estimated_price), int(risk_level), float(estimated_gains)))
    return signals[-1]

if __name__ == '__main__':
    update_ohlcv("NVDA")
    df = fetch_ohlcv("NVDA", "Daily", limit=10)
    print(orb_strategy(df))