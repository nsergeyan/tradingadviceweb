# final_strategy.py

from backend.bos_strat import bos_strat
from backend.database.crud import fetch_ohlcv, update_ohlcv
from backend.fair_value_gaps_strategy import fair_value_gaps_strategy
from backend.orb_strategy import orb_strategy

def final_strategy(cash, symbol):
    # BOS strat
    bos_price, bos_risk, bos_gains, bos_signal = bos_strat(cash, symbol)

    # FVG strat
    df_weekly = fetch_ohlcv(symbol, "Weekly", limit=10)
    fvg_price, fvg_risk, fvg_gains = fair_value_gaps_strategy(df_weekly)

    # ORB strat
    update_ohlcv(symbol, "Daily")
    df_daily = fetch_ohlcv(symbol, "Daily", limit=10)
    orb_price, orb_risk, orb_gains = orb_strategy(df_daily)

    # Weighted average risk and gains
    risk = bos_risk*0.6 + fvg_risk*0.2 + orb_risk*0.2
    gains = bos_gains*0.6 + fvg_gains*0.2 + orb_gains*0.2

    # Final decision
    if risk >= 1.5:
        decision = "BUY"
        risk_comment = "Low risk / go for it"
    elif risk >= 1.0:
        decision = "BUY (caution)"
        risk_comment = "Medium risk / exercise caution"
    else:
        decision = "DO NOT BUY"
        risk_comment = "High risk / refrain from investing"

    # Print result
    print(f"Symbol: {symbol}")
    print(f"Decision: {decision}")
    print(f"Risk score: {risk:.2f} ({risk_comment})")
    print(f"Estimated gains: {gains:.2f}")
    print(f"BOS signal: {bos_signal}")
    print(f"FVG signal price: {fvg_price}")
    print(f"ORB signal price: {orb_price}")

if __name__ == "__main__":
    final_strategy(1000, "AAPL")

# to run: use "python -m backend.final_strat" from tradingadviceweb2, do not run from inside backend!