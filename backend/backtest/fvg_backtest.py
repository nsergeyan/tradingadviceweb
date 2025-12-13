from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
import pandas as pd

from backend.database.crud import fetch_ohlcv, update_ohlcv


class FVGStrategy(bt.Strategy):
    params = dict(
        threshold=0.7,
        stake=1,
        rr=3.0, # risk reward ratio
        gap=5
    )


    def get_size(self, price):
        cash = self.broker.get_cash()
        risk_cash = cash * self.p.stake
        size = int(risk_cash // price)
        return size if size > 0 else 1

    def __init__(self):
        self.order = None
        self.fvg_zones = []       # [(start, end, direction, id)]
        self.active_trades = set()  # finished order id

    def next(self):
        if len(self.data.close) < 3:
            return

        prev2_high, prev2_low = self.data.high[-2], self.data.low[-2]
        prev1_high, prev1_low = self.data.high[-1], self.data.low[-1]
        prev1_open, prev1_close = self.data.open[-1], self.data.close[-1]

        current_price = self.data.close[0]

        # big candle
        body = abs(prev1_close - prev1_open)
        full_range = max(prev1_high - prev1_low, 1e-9)
        big_ratio = body / full_range

        if big_ratio >= self.p.threshold:
            if prev2_low > self.data.high[0] and (prev2_low - self.data.high[0]) >= self.p.gap:
                zone_id = f"bull_{len(self.fvg_zones)}_{self.datetime.date(0)}"
                self.fvg_zones.append((prev2_high, prev1_low, "bullish", zone_id))

            elif prev2_high < self.data.low[0] and (self.data.low[0] - prev2_high) >= self.p.gap:
                zone_id = f"bear_{len(self.fvg_zones)}_{self.datetime.date(0)}"
                self.fvg_zones.append((prev1_high, prev2_low, "bearish", zone_id))

        for zone in list(self.fvg_zones):
            start, end, direction, zone_id = zone
            if zone_id in self.active_trades:
                continue

            zone_height = abs(end - start)
            if direction == "bullish" and current_price <= start:
                entry = current_price
                stop = entry - zone_height
                target = entry + (entry - stop) * self.p.rr
                self.buy_bracket(size=self.get_size(entry), price=entry, stopprice=stop, limitprice=target)
                self.active_trades.add(zone_id)

            elif direction == "bearish" and current_price >= end:
                entry = current_price
                stop = entry + zone_height
                target = entry - (stop - entry) * self.p.rr
                self.sell_bracket(size=self.get_size(entry), price=entry, stopprice=stop, limitprice=target)
                self.active_trades.add(zone_id)

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None

def run_multi_symbol_fvg(symbols, cash=1000.0, timeframe="Weekly", limit=50):
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
            cerebro.addstrategy(FVGStrategy)
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

            # print(f"[{symbol}] start={start_val:.2f}, end={end_val:.2f}, "
            #       f"gain={gain:.2f}, gain_rate={gain_rate:.2f}%")

        except Exception as e:
            print(f"[Error] {symbol}: {e}")

    if not results:
        print("No results computed.")
        return None

    df_res = pd.DataFrame(results)

    avg_gain_rate = df_res["gain_rate"].mean()
    gain_count = (df_res["gain"] > 0).sum()
    loss_count = (df_res["gain"] <= 0).sum()
    gain_rate_overall = gain_count / len(df_res)
    loss_rate_overall = loss_count / len(df_res)

    print("\n====== Summary ======")
    print(f"Symbols tested: {len(df_res)}")
    print(f"Average gain rate: {avg_gain_rate:.2f}%")
    print(f"Gain rate (symbols ended up >0): {gain_rate_overall*100:.1f}%")
    print(f"Loss rate (symbols ended up ≤0): {loss_rate_overall*100:.1f}%")

    return df_res

# if __name__ == "__main__":
#     symbols = ["AAPL", "MSFT", "AMZN", "NVDA", "TSLA", "IBM"]
#     summary = run_multi_symbol_fvg(symbols)
#     print(summary)

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(FVGStrategy)

    update_ohlcv("AAPL")
    df = fetch_ohlcv("AAPL", "Weekly", limit=100)
    df["datetime"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df.drop("date", axis=1, inplace=True)
    df = df.sort_values("datetime").reset_index(drop=True)
    df.set_index("datetime", inplace=True)

    print(df)
    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    cerebro.broker.setcash(1000.0)
    cerebro.broker.setcommission(commission=0.001)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.plot(style='candle', volume=True, barup='red', bardown='green')