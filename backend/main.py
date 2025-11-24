from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from backend.aiAnalyzer import deep_research
from backend.database.crud import update_ohlcv, fetch_ohlcv
from backend.database.database import get_db, db
from backend.database.models import PriceData, MetaData
from backend.list_stocks import get_50_stocks
from backend.bos_strat import bos_strat
from backend.fair_value_gaps_strategy import fair_value_gaps_strategy
from backend.orb_strategy import orb_strategy

@asynccontextmanager
async def lifespan(app: FastAPI):

    db.connect()
    db.create_tables([
        MetaData,
        PriceData,
    ])
    db.close()

    yield

app = FastAPI(
    title="Trading Helper API",
    description="AI-powered stock research and news analysis",
    version="1.1",
    lifespan=lifespan
)

analysis_cache = {}

@app.get("/")
def root():
    return {"message": "Welcome to the Trading Helper API!"}


@app.get("/analyze/top5", dependencies=[Depends(get_db)])
def analyze_top5():
    """
    Example: GET /analyze/top5
    Runs deep research and returns dictionary of 5 stock analyses.
    """
    try:
        result = deep_research.aiAnalyzeTopFiveStocks()
        analysis_cache.clear()
        analysis_cache.update(result)  # cache result
        return {"analyzed": list(result.keys()), "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep research failed: {e}")


@app.get("/analyze/top5/{index}", dependencies=[Depends(get_db)])
def analyze_specific_by_index(index: int):
    """
    Example: GET /analyze/top5/3
    Returns the 3rd stock from the last deep analysis run.
    """
    if not analysis_cache:
        raise HTTPException(status_code=400, detail="Run /analyze/top5 first to generate data.")

    keys = list(analysis_cache.keys())

    if not (1 <= index <= len(keys)):
        raise HTTPException(status_code=404, detail=f"Index {index} out of range (1–{len(keys)}).")

    symbol = keys[index - 1]
    return {symbol: analysis_cache[symbol]}

@app.get("/signals/top5", dependencies=[Depends(get_db)])
def get_top5_signals():
    """
    Returns top-5 stocks + decision BUY/HOLD/SELL
    """
    try:
        symbols = get_50_stocks()[:5]  # первые 5
        results = {}

        for sym in symbols:
            try:
                results[sym] = _build_signal_for_symbol(sym)
            except Exception as e:
                results[sym] = {"error": str(e)}

        return {"symbols": symbols, "signals": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_signal_for_symbol(symbol: str, cash: float = 1000.0) -> dict:
    """
    Create signal (BUY / HOLD / SELL) by 3 strategies.
    """

    # --- BOS strategy (weekly) ---
    update_ohlcv(symbol, "Weekly")
    df_weekly = fetch_ohlcv(symbol, "Weekly", limit=120)
    bos_price, bos_risk, bos_gains, bos_signal = bos_strat(cash, symbol)

    # --- Fair Value Gaps (weekly) ---
    fvg_price, fvg_risk, fvg_gains = fair_value_gaps_strategy(df_weekly)

    # --- ORB strategy (daily) ---
    update_ohlcv(symbol, "Daily")
    df_daily = fetch_ohlcv(symbol, "Daily", limit=15)
    orb_price, orb_risk, orb_gains = orb_strategy(df_daily)

    # --- Average risk/gains ---
    avg_risk = (bos_risk + fvg_risk + orb_risk) / 3
    avg_gains = (bos_gains + fvg_gains + orb_gains) / 3

    # --- Final decision ---
    if avg_risk >= 1.5:
        decision = "BUY"
    elif avg_risk >= 1.0:
        decision = "HOLD"
    else:
        decision = "SELL"

    return {
        "symbol": symbol,
        "decision": decision,
        "avg_risk": avg_risk,
        "avg_gains": avg_gains,
        "bos": {
            "risk": bos_risk,
            "gains": bos_gains,
            "signal": bos_signal
        },
        "fvg": {
            "risk": fvg_risk,
            "gains": fvg_gains
        },
        "orb": {
            "risk": orb_risk,
            "gains": orb_gains
        }
    }



