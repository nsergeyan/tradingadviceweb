from backend.database.crud import update_ohlcv, fetch_ohlcv


def bos_strat(cash, symbol):
    #------------------------------
    # Fetch Data and Create Candles List
    #------------------------------

    # Update or fetch weekly data
    update_ohlcv(symbol, "Weekly")

    # Get data
    df = fetch_ohlcv(symbol, limit=100)

    if len(df) < 3:
        return [None, None, None]

    # Convert to list of lists
    candles = [
        [row['open'], row['close'], row['high'], row['low'], row['volume']]
        for _, row in df.iterrows()  # '_' refers to not needed var, the index
    ]

    # -----------------------------------
    # Break of Structure Analysis
    # -----------------------------------

    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[1] for c in candles]

    # Current price = last close
    current_price = closes[-1]

    # Detect simple break of structure (higher high + higher low vs previous)
    hh = highs[-1] > highs[-2] and highs[-2] > highs[-3] #higher highs
    hl = lows[-1] > lows[-2] and lows[-2] > lows[-3] #higher lows

    # Assigning Risk
    # 0 = no bullish structure, 1 = partial bullish, 2 = clear bullish structure
    if hh and hl:
        risk = 2
    elif hh or hl:
        risk = 1
    else:
        risk = 0

    # Estimated P/L
    if risk == 2:
        estimated_gains = (highs[-1] - closes[-2]) / closes[-2]
    elif risk == 1:
        estimated_gains = (closes[-1] - closes[-2]) / closes[-2]
    else:
        estimated_gains = 0.0

    if risk == 2:
        signal = "BUY (risk level = low)"
    elif risk == 1:
        signal = "BUY (risk level = medium)"
    else:
        signal = "SELL/DO NOT BUY"

    return [current_price, risk, estimated_gains, signal]

if __name__ == "__main__":
    result = bos_strat(1000, "AAPL")
    print(result)
