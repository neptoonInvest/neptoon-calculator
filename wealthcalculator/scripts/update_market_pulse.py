
import os
import json
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path


# =====================================================
# NW-111 · MARKET PULSE
# EODHD REALTIME QUOTES
# =====================================================

TOKEN = os.environ["EODHD_TOKEN"]

# Replace these examples with the 10 agreed tickers.
# Use exact EODHD tickerExchange identifiers.

TICKERS = [
    "AAPL.US",
    "MSFT.US",
    "NVDA.US",
    "GOOGL.US",
    "AMZN.US",
    "META.US",
    "TSLA.US",
    "RHM.XETRA",
    "NOVO-B.CO",
    "ASML.AS",
]


# =====================================================
# 01 · SAFE NUMBER
# =====================================================

def safe_num(value):

    try:
        n = float(value)
        return n if math.isfinite(n) else None

    except (TypeError, ValueError):
        return None


# =====================================================
# 02 · FETCH SINGLE QUOTE
# =====================================================

def fetch_quote(ticker):

    params = urllib.parse.urlencode({
        "api_token": TOKEN,
        "fmt": "json"
    })

    url = (
        "https://eodhd.com/api/real-time/"
        + urllib.parse.quote(ticker, safe="")
        + "?"
        + params
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NeptoonMarketPulse/1.0"}
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        data = json.load(response)

    price = safe_num(
        data.get("close", data.get("price"))
    )

    change = safe_num(
        data.get("change_p")
    )

    return {
        "realtimePrice": price,
        "return": change / 100 if change is not None else None,
        "timestamp": data.get("timestamp")
    }


# =====================================================
# 03 · BUILD MARKET DATA
# =====================================================

def main():

    quotes = {}

    for ticker in TICKERS:

        try:

            quotes[ticker] = fetch_quote(ticker)

            print("OK:", ticker)

        except Exception as error:

            print("ERROR:", ticker, error)

            quotes[ticker] = {
                "realtimePrice": None,
                "return": None,
                "timestamp": None
            }

    result = {
        "updatedAt": datetime.now(
            timezone.utc
        ).isoformat(),

        "quotes": quotes
    }

    Path("market_pulse.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    print("Market Pulse JSON updated")


if __name__ == "__main__":
    main()

