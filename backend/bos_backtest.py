import backtrader as bt
from database import fetch_ohlcv, update_weekly
import pandas as pd

def bos_strat(candles): #same strategy as in bos_strat.py onlt difference is
                        #that this backtrader sells at 10% profit and 5% loss
    if len(candles) < 3:
        return [None, None, None]

    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[1] for c in candles]

    current_price = closes[-1]

    hh = highs[-1] > highs[-2] and highs[-2] > highs[-3]
    hl = lows[-1] > lows[-2] and lows[-2] > lows[-3]

    if hh and hl:
        risk = 2
    elif hh or hl:
        risk = 1
    else:
        risk = 0

    if risk == 2:
        estimated_gains = (highs[-1] - closes[-2]) / closes[-2]
    elif risk == 1:
        estimated_gains = (closes[-1] - closes[-2]) / closes[-2]
    else:
        estimated_gains = 0.0

    return [current_price, risk, estimated_gains]


class BosStrategy(bt.Strategy):
    params = dict(symbol=None, cash=10000, take_profit=0.10, stop_loss=0.05)#sell at 10% profit or 5% loss

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

    def next(self):
        candles = []
        for i in range(-50, 0):  # Use last 50 candles
            if abs(i) > len(self.data):
                continue
            candles.append([
                self.data.open[i],
                self.data.close[i],
                self.data.high[i],
                self.data.low[i],
                self.data.volume[i]
            ])

        if len(candles) < 3:
            return

        current_price, risk, gains = bos_strat(candles)

        if current_price is None:
            return

        # Check actual position size, not just position object
        position_size = self.position.size if self.position else 0

        # BUY: Does not have a position & risk >= 1
        if position_size == 0 and risk >= 1:
            # Use percentage of cash instead of fixed size
            cash_available = self.broker.getcash()
            size = int((cash_available * 0.95) / current_price)
            if size > 0:
                self.buy(size=size)
                self.entry_price = current_price

        # SELL: Must have a position and risk of 0
        elif position_size > 0:
            if current_price >= self.entry_price * (1 + self.p.take_profit): #TP
                self.close()
            elif current_price <= self.entry_price * (1 - self.p.stop_loss): #TL
                self.close()

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Value: {order.executed.value:.2f}')

def get_bt_data(symbol, weeks=50):
    update_weekly(symbol)
    df = fetch_ohlcv(symbol, limit=None)

    # Makes sure of proper datetime index (doesn't work otherwise)
    if 'date' in df.columns:
        df['datetime'] = pd.to_datetime(df['date'])
        df.set_index('datetime', inplace=True)

    # Sort by date and get last N weeks
    df.sort_index(inplace=True)
    df = df.tail(weeks)

    print(f"Backtraded {df.shape[0]} weeks: from {df.index[0]} to {df.index[-1]}.")
    return df

def run_backtest(symbol, starting_cash=10000, weeks=50):
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(starting_cash)
    cerebro.broker.setcommission(commission=0.001)  # 0.5% commission (lower than usual)
                                                    # (usually, 1-2%)

    df = get_bt_data(symbol, weeks=weeks)
    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)

    cerebro.addstrategy(BosStrategy, symbol=symbol, cash=starting_cash)

    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    cerebro.run()
    print(f'\n{'=' * 30}\n')
    return cerebro.broker.getvalue()

# Running test case
if __name__ == "__main__":
    final_cash = run_backtest("AAPL", starting_cash=10000, weeks=20)
    print(f"Final Portfolio Value: ${final_cash:.2f}")
    print(f"Profit/Loss: ${final_cash - 10000:.2f} ({((final_cash / 10000 - 1) * 100):.2f}%)")