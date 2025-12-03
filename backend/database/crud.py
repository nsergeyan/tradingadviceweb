import requests
import pandas as pd
from backend.settings import ALPHAVANTAGE_API_KEY
from .models import MetaData, PriceData
from typing import Optional


API_FUNCTION_MAP = {
    "Daily": "TIME_SERIES_DAILY",
    "Weekly": "TIME_SERIES_WEEKLY",
    "Monthly": "TIME_SERIES_MONTHLY",
}

API_KEY_MAP = {
    "Daily": "Time Series (Daily)",
    "Weekly": "Weekly Time Series",
    "Monthly": "Monthly Time Series",
}


def update_ohlcv(symbol: str, info_type: str = "Weekly") -> None:
    """
    Args:
        symbol (str): "IBM"
        info_type (str): "Daily" | "Weekly" | "Monthly"
    """

    if info_type not in API_FUNCTION_MAP:
        raise ValueError(f"Invalid info_type: {info_type}")

    url = (
        f"https://www.alphavantage.co/query"
        f"?function={API_FUNCTION_MAP[info_type]}"
        f"&symbol={symbol}"
        f"&outputsize=compact"
        f"&apikey={ALPHAVANTAGE_API_KEY}"
    )

    r = requests.get(url)
    data = r.json()

    # -------- Extract Meta --------
    meta = data["Meta Data"]
    last_refreshed = meta.get("3. Last Refreshed")
    time_zone = meta.get("5. Time Zone") or meta.get("4. Time Zone")

    m, created = MetaData.get_or_create(
        symbol=symbol,
        info_type=info_type,
        defaults={"last_refreshed": last_refreshed, "time_zone": time_zone},
    )

    if not created:
        m.last_refreshed = last_refreshed
        m.time_zone = time_zone
        m.save()

    # -------- Extract Time Series --------
    time_series_key = API_KEY_MAP[info_type]
    series = data[time_series_key]

    # -------- Insert / Update OHLCV --------
    for date, values in series.items():
        obj, created = PriceData.get_or_create(
            meta=m,
            date=date,
            defaults={
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            },
        )

        if not created:
            obj.open = float(values["1. open"])
            obj.high = float(values["2. high"])
            obj.low = float(values["3. low"])
            obj.close = float(values["4. close"])
            obj.volume = int(values["5. volume"])
            obj.save()

    print(f"{symbol} {info_type} OHLCV updated successfully")


def fetch_ohlcv(
        symbol: str,
        info_type: str = "Weekly",
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns:
        pd.DataFrame: columns = ["date","open","high","low","close","volume"]
    """

    query = (
        PriceData.select(
            PriceData.date,
            PriceData.open,
            PriceData.high,
            PriceData.low,
            PriceData.close,
            PriceData.volume,
        )
        .join(MetaData)
        .where(MetaData.symbol == symbol, MetaData.info_type == info_type)
    )

    if start_date:
        query = query.where(PriceData.date >= start_date)
    if end_date:
        query = query.where(PriceData.date <= end_date)

    query = query.order_by(PriceData.date.desc())

    if limit:
        query = query.limit(limit)

    df = pd.DataFrame(list(query.dicts()))

    return df