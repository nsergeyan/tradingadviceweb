from __future__ import (absolute_import, division, print_function, unicode_literals)

import backtrader as bt
import pandas as pd

from backend.database import fetch_ohlcv, update_daily


class ORBStrategy(bt.Strategy):
    """
    Opening Range Breakout (ORB) strategy implemented for Backtrader backtesting.
    Uses the first two candles of the analysis period to define the range and checks
    for breakouts in the subsequent candles.
    """

    params = dict(
        stake=1.0,
        rr=2.0,       # risk-reward ratio
        lookback=5,   # number of recent bars to define the OR range
    )

    def __init__(self):
        self.order = None
        self.or_high = None
        self.or_low = None
        self.breakout_up = False
        self.breakout_down = False
        self.bar_counter = 0
        self.or_established = False

    def get_size(self, price):
        cash = self.broker.get_cash()
        risk_cash = cash * self.p.stake
        size = int(risk_cash // price)
        return max(size, 1)

    def next(self):
        self.bar_counter += 1

        # Wait until we have enough candles to define the Opening Range
        if len(self.data) < self.p.lookback:
            return

        # Define OR range from first 2 bars of lookback period
        if not self.or_established:
            last_bars = self.data.close.get(size=self.p.lookback)
            highs = self.data.high.get(size=self.p.lookback)
            lows = self.data.low.get(size=self.p.lookback)

            self.or_high = max(highs[0], highs[1])
            self.or_low = min(lows[0], lows[1])
            self.or_established = True
            return

        current_high = self.data.high[0]
        current_low = self.data.low[0]
        current_close = self.data.close[0]
        current_open = self.data.open[0]

        # Determine breakout conditions
        if current_high > self.or_high:
            self.breakout_up = True
        elif current_low < self.or_low:
            self.breakout_down = True

        # Manage entries
        if not self.position:
            or_range = abs(self.or_high - self.or_low)
            if or_range == 0:
                return

            # Bullish breakout
            if self.breakout_up:
                entry = current_close
                stop = entry - or_range
                target = entry + (entry - stop) * self.p.rr
                self.buy_bracket(size=self.get_size(entry), price=entry,
                                 stopprice=stop, limitprice=target)
                self.breakout_up = False  # reset

            # Bearish breakout
            elif self.breakout_down:
                entry = current_close
                stop = entry + or_range
                target = entry - (stop - entry) * self.p.rr
                self.sell_bracket(size=self.get_size(entry), price=entry,
                                  stopprice=stop, limitprice=target)
                self.breakout_down = False  # reset

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None


def run_multi_symbol_orb(symbols, cash=1000.0, timeframe="Daily", limit=50):
    results = []

    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, timeframe, limit=limit)
            if df is None or len(df) < 10:
                print(f"[Skip] {symbol}: insufficient data")
                continue

            df["datetime"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
            df.drop("date", axis=1, inplace=True)
            df = df.sort_values("datetime").reset_index(drop=True)
            df.set_index("datetime", inplace=True)

            cerebro = bt.Cerebro()
            cerebro.addstrategy(ORBStrategy)
            cerebro.adddata(bt.feeds.PandasData(dataname=df))
            cerebro.broker.setcash(cash)
            cerebro.broker.setcommission(commission=0.001)

            start_val = cerebro.broker.getvalue()
            cerebro.run()
            end_val = cerebro.broker.getvalue()

            gain = end_val - start_val
            gain_rate = (gain / start_val) * 100.0

            results.append({
                "symbol": symbol,
                "start": start_val,
                "end": end_val,
                "gain_rate": gain_rate,
                "gain": gain
            })

        except Exception as e:
            print(f"[Error] {symbol}: {e}")

    if not results:
        print("No results computed.")
        return None

    df_res = pd.DataFrame(results)
    avg_gain_rate = df_res["gain_rate"].mean()
    gain_count = (df_res["gain"] > 0).sum()
    loss_count = (df_res["gain"] <= 0).sum()

    print("\n====== Summary ======")
    print(f"Symbols tested: {len(df_res)}")
    print(f"Average gain rate: {avg_gain_rate:.2f}%")
    print(f"Win rate: {gain_count / len(df_res) * 100:.1f}%")
    print(f"Loss rate: {loss_count / len(df_res) * 100:.1f}%")

    return df_res


if __name__ == '__main__':
    # Single-symbol test (AAPL as example)
    cerebro = bt.Cerebro()
    cerebro.addstrategy(ORBStrategy)

    update_daily("AAPL")
    df = fetch_ohlcv("AAPL", "Daily", limit=50)
    df["datetime"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df.drop("date", axis=1, inplace=True)
    df = df.sort_values("datetime").reset_index(drop=True)
    df.set_index("datetime", inplace=True)

    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    cerebro.broker.setcash(1000.0)
    cerebro.broker.setcommission(commission=0.001)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.plot(style='candle', volume=True, barup='green', bardown='red')

