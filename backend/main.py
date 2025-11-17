from fastapi import FastAPI, HTTPException
from backend.aiAnalyzer import deep_research

app = FastAPI(
    title="Trading Helper API",
    description="AI-powered stock research and news analysis",
    version="1.1"
)

analysis_cache = {}

@app.get("/")
def root():
    return {"message": "Welcome to the Trading Helper API!"}


@app.get("/analyze/top5")
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


@app.get("/analyze/top5/{index}")
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
