from tradingview_screener import get_all_symbols
from tvDatafeed import TvDatafeed
from .config import EXCHANGE_MAPPINGS, SYMBOL_PREFIXES
from datetime import datetime, time
import pandas as pd

tv = TvDatafeed()


def fetch_market_symbols(market):
    """Fetch symbols for given market"""
    try:
        if market == "BIST":
            symbols = get_all_symbols(market="turkey")
            return sorted([s.replace("BIST:", "") for s in symbols])
        elif market == "Forex":
            symbols = get_all_symbols(market="forex")
            return sorted([s.replace("FX:", "") for s in symbols])
        elif market == "Crypto":
            symbols = get_all_symbols(market="crypto")
            return sorted(
                [s.replace("BINANCE:", "") for s in symbols if s.endswith("USDT")]
            )
        elif market == "NASDAQ":
            symbols = get_all_symbols(market="america")
            return sorted([s.replace("NASDAQ:", "") for s in symbols])
        return []
    except Exception as e:
        return []


def get_full_symbol(market, symbol):
    """Add exchange prefix to symbol"""
    return f"{SYMBOL_PREFIXES.get(market, '')}{symbol}"


def is_market_open(timestamp, market):
    """Check if market is open at given timestamp"""
    weekday = timestamp.weekday()
    current_time = timestamp.time()

    market_hours = {
        "BIST": {
            "open": time(10, 0),
            "close": time(18, 0),
            "trading_days": range(0, 5),  # Monday to Friday
        },
        "NASDAQ": {
            "open": time(9, 30),
            "close": time(16, 0),
            "trading_days": range(0, 5),
        },
        "Forex": {
            "open": time(0, 0),
            "close": time(23, 59),
            "trading_days": range(0, 7),  # All week
        },
        "Crypto": {
            "open": time(0, 0),
            "close": time(23, 59),
            "trading_days": range(0, 7),
        },
    }

    market_schedule = market_hours.get(market)
    if not market_schedule:
        return True

    return (
        weekday in market_schedule["trading_days"]
        and market_schedule["open"] <= current_time <= market_schedule["close"]
    )


def clean_market_data(data, market):
    """Clean market data by removing gaps"""
    if data is None or data.empty:
        return data

    # Convert index to datetime
    data.index = pd.to_datetime(data.index)

    # Sort index
    data = data.sort_index()

    # Forward fill small gaps
    data = data.fillna(method="ffill", limit=3)

    return data


def fetch_market_data(symbol, exchange, interval, n_bars=2500):
    """Fetch and clean market data from TvDatafeed"""
    data = tv.get_hist(
        symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars
    )

    if data is not None and not data.empty:
        return clean_market_data(data, exchange)
    return data
