import peewee
from peewee import *
from .database import db


class BaseModel(peewee.Model):
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
