MARKETS = ["BIST", "Forex", "Crypto", "NASDAQ"]

TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]

EXCHANGE_MAPPINGS = {
    "BIST": "BIST",
    "Forex": "FX",
    "Crypto": "BINANCE",
    "NASDAQ": "NASDAQ",
}

SYMBOL_PREFIXES = {
    "BIST": "BIST:",
    "Forex": "FX:",
    "Crypto": "BINANCE:",
    "NASDAQ": "NASDAQ:",
}

TIMEFRAME_INTERVALS = {
    "1m": 60,  # 60 seconds
    "5m": 300,  # 5 minutes
    "15m": 900,  # 15 minutes
    "30m": 1800,  # 30 minutes
    "1h": 3600,  # 1 hour
    "4h": 14400,  # 4 hours
    "1d": 86400,  # 1 day
    "1w": 604800,  # 1 week
    "1M": 2592000,  # 1 month (30 days)
}
