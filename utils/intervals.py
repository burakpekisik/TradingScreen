from tvDatafeed import Interval


def get_interval(timeframe):
    """Convert string timeframe to TvDatafeed Interval enum"""
    intervals = {
        "1m": Interval.in_1_minute,
        "5m": Interval.in_5_minute,
        "15m": Interval.in_15_minute,
        "30m": Interval.in_30_minute,
        "1h": Interval.in_1_hour,
        "4h": Interval.in_4_hour,
        "1d": Interval.in_daily,
        "1w": Interval.in_weekly,
        "1M": Interval.in_monthly,
    }
    return intervals.get(timeframe, Interval.in_daily)
