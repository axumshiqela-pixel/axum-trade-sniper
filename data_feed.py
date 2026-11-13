import time
import requests

# TODO before going public: move to Render env var
TWELVE_DATA_KEY = "e7f4e10a0c6b41c8b4440183a40b2751"

SYMBOL_MAP = {
    "GBP/USD": "GBP/USD",
    "XAU/USD": "XAU/USD",
    "EUR/USD": "EUR/USD",
    "NASDAQ":  "QQQ",
    "AUD/USD": "AUD/USD",
}

_cache = {}
CACHE_SECONDS = 600


def get_price(pair: str):
    now = time.time()
    cached = _cache.get(pair)
    if cached and (now - cached["ts"]) < CACHE_SECONDS:
        return cached["price"]

    symbol = SYMBOL_MAP.get(pair)
    if not symbol:
        return None

    try:
        r = requests.get(
            "https://api.twelvedata.com/price",
            params={"symbol": symbol, "apikey": TWELVE_DATA_KEY},
            timeout=5,
        )
        data = r.json()
        if "price" not in data:
            print(f"[12DATA ERROR] {pair}: {data}")
            return cached["price"] if cached else None
        price = float(data["price"])
        _cache[pair] = {"price": price, "ts": now}
        return price
    except Exception as e:
        print(f"[12DATA EXCEPTION] {pair}: {e}")
        return cached["price"] if cached else None


def get_candles(pair: str, interval: str = "5min", count: int = 50):
    symbol = SYMBOL_MAP.get(pair)
    if not symbol:
        return None
    try:
        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": symbol,
                "interval": interval,
                "outputsize": count,
                "apikey": TWELVE_DATA_KEY,
            },
            timeout=8,
        )
        data = r.json()
        if "values" not in data:
            print(f"[12DATA CANDLES ERROR] {pair}: {data}")
            return None
        return list(reversed(data["values"]))
    except Exception as e:
        print(f"[12DATA CANDLES EXCEPTION] {pair}: {e}")
        return None
