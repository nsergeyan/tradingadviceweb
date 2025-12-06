from starlette.responses import JSONResponse

from backend.views import router as views_router #needed for frontend

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from backend.aiAnalyzer import deep_research
from backend.database.database import get_db, db
from backend.database.models import PriceData, MetaData
from backend.list_stocks import get_50_stocks



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
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://localhost:63342"] in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(views_router)

analysis_cache = {}

@app.get("/")
def root():
    return {"message": "Welcome to the Trading Helper API!"}

@app.get("/analyze/top5/{index}", dependencies=[Depends(get_db)])
def analyze_specific_by_index(index: int):
    """
    Example: GET /analyze/top5/3
    """
    stocks = get_50_stocks()

    # Python list is 0-based, user is 1-based → adjust
    if index < 0 or index > len(stocks):
        raise HTTPException(
            status_code=404,
            detail=f"Index {index} out of range (1–{len(stocks)})."
        )

    stock = stocks[index]

    try:
        return JSONResponse(content=deep_research.aiAnalyzeTopFiveStocks(stock))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from backend.final_strat import final_strategy  # <- import

@app.get("/signals/top5", dependencies=[Depends(get_db)])
def get_top5_signals():
    """
    Returns top-5 stocks + decision BUY/HOLD/SELL using final_strategy.
    """
    try:
        symbols = get_50_stocks()[:5]  # first 5 symbols
        results = {}

        for sym in symbols:
            try:
                results[sym] = final_strategy(1000, sym)  # call the imported function
            except Exception as e:
                results[sym] = {"error": str(e)}

        return JSONResponse(content={"symbols": symbols, "signals": results})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



