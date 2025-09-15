import os
import requests
from peewee import *
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database initialization (file will be created in the current folder)
db = SqliteDatabase('TradingAdvice.db')

# Get API key from environment
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")


# -------------------------
# Database Models
# -------------------------
class BaseModel(Model):
    class Meta:
        database = db


class MetaData(BaseModel):
    """Stores general information about the symbol and its time series."""
    symbol = CharField()  # Stock symbol, e.g. "IBM"
    info_type = CharField()  # "Weekly" / "Monthly" / "Daily"
    last_refreshed = CharField()  # Last refreshed date, e.g. "2025-09-12"
    time_zone = CharField()  # Time zone of the data, e.g. "US/Eastern"


class PriceData(BaseModel):
    """Stores open, high, low, close, and volume data for each date."""
    meta = ForeignKeyField(MetaData, backref='prices')
    date = CharField()  # e.g. "2025-09-12"
    open = FloatField()
    high = FloatField()
    low = FloatField()
    close = FloatField()
    volume = IntegerField()


# Connect to the database and create tables if not exist
db.connect()
db.create_tables([MetaData, PriceData])


# -------------------------
# Data Update Function
# -------------------------
def update_weekly(symbol: str):
    """
    Fetch weekly stock data from AlphaVantage API and update the database.

    Args:
        symbol (str): Stock symbol to update, e.g. "IBM".
    """
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_WEEKLY&symbol={symbol}&apikey={ALPHAVANTAGE_API_KEY}"
    )

    r = requests.get(url)
    data = r.json()

    # Extract meta information
    meta = data["Meta Data"]
    info_type = "Weekly"
    last_refreshed = meta["3. Last Refreshed"]
    time_zone = meta["4. Time Zone"]

    # Insert or update MetaData
    m, created = MetaData.get_or_create(
        symbol=symbol,
        info_type=info_type,
        defaults={"last_refreshed": last_refreshed, "time_zone": time_zone}
    )

    if not created:
        # Update existing meta record
        m.last_refreshed = last_refreshed
        m.time_zone = time_zone
        m.save()

    # Find the key that contains time series data (e.g., "Weekly Time Series")
    time_series_key = [k for k in data.keys() if "Time Series" in k][0]

    # Insert or update PriceData for each date
    for date, values in data[time_series_key].items():
        obj, created = PriceData.get_or_create(
            meta=m,
            date=date,
            defaults={
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            }
        )
        if not created:
            # Update existing record
            obj.open = float(values["1. open"])
            obj.high = float(values["2. high"])
            obj.low = float(values["3. low"])
            obj.close = float(values["4. close"])
            obj.volume = int(values["5. volume"])
            obj.save()

    print(f"{symbol} weekly data updated successfully ✅")


update_weekly("IBM")
