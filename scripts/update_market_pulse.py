
import os
import json
import math
import urllib.request
import urllib.parse

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path


# =====================================================
# NW-111 · MARKET PULSE
# EODHD LIVE + OFFICIAL US INDEX CLOSE
# =====================================================

TOKEN = os.environ["EODHD_TOKEN"]

MODE = os.getenv(
    "MARKET_PULSE_MODE",
    "live"
).strip().lower()

OUTPUT = Path("market_pulse.json")

NEW_YORK = ZoneInfo("America/New_York")




# =====================================================
# 00 · INSTRUMENTS
# SHARED WITH DAILY MARKET HISTORY
# =====================================================

CONFIG = Path("market_instruments.json")


def load_tickers():

    with CONFIG.open(
        "r",
        encoding="utf-8"
    ) as file:

        payload = json.load(file)

    # Same configuration used by
    # update_market_history.py

    tickers = payload["tickers"]

    if not isinstance(tickers, list):
        raise ValueError(
            "Invalid market instrument configuration"
        )

    tickers = [
        str(t).strip().upper()
        for t in tickers
    ]

    if (
        len(tickers) != 25
        or len(set(tickers)) != 25
        or any(not t for t in tickers)
    ):
        raise ValueError(
            "Expected exactly 25 unique tickers"
        )

    return tickers


TICKERS = load_tickers()


# Official close override remains unchanged.

US_INDICES = [
    "GSPC.INDX",
    "IXIC.INDX"
]

if not set(US_INDICES).issubset(TICKERS):
    raise ValueError(
        "US indices missing from shared configuration"
    )


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
# 02 · API REQUEST
# =====================================================

def api_json(endpoint, ticker, extra=None):

    params = {
        "api_token": TOKEN,
        "fmt": "json"
    }

    if extra:
        params.update(extra)

    url = (
        "https://eodhd.com/api/"
        + endpoint
        + "/"
        + urllib.parse.quote(ticker, safe="")
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NeptoonMarketPulse/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:

        return json.load(response)


# =====================================================
# 03 · LIVE QUOTE
# =====================================================

def fetch_live_quote(ticker):

    data = api_json(
        "real-time",
        ticker
    )

    price = safe_num(
        data.get("close", data.get("price"))
    )

    change = safe_num(
        data.get("change_p")
    )

    if price is None:
        raise ValueError(
            f"No valid live price for {ticker}"
        )

    return {
        "realtimePrice": price,
        "return": (
            change / 100
            if change is not None
            else None
        ),
        "timestamp": data.get("timestamp")
    }


# =====================================================
# 04 · OFFICIAL US INDEX CLOSE
# =====================================================

def fetch_official_close(ticker):

    now_ny = datetime.now(NEW_YORK)

    today = now_ny.date()

    # Do not accept an official close before
    # the regular US market closing time.

    if (
        now_ny.hour < 16
        or (
            now_ny.hour == 16
            and now_ny.minute < 0
        )
    ):
        raise ValueError(
            "US market has not closed"
        )

    # Request enough calendar days to find
    # today's close and the previous trading close.

    start = today - timedelta(days=15)

    data = api_json(
        "eod",
        ticker,
        {
            "from": start.isoformat(),
            "to": today.isoformat(),
            "order": "d"
        }
    )

    if not isinstance(data, list):
        raise ValueError(
            f"Invalid EOD response for {ticker}"
        )

    rows = sorted(
        [
            row for row in data
            if isinstance(row, dict)
            and row.get("date")
        ],
        key=lambda row: row["date"],
        reverse=True
    )

    if len(rows) < 2:
        raise ValueError(
            f"Insufficient EOD history for {ticker}"
        )

    latest = rows[0]
    previous = rows[1]

    # Critical: reject yesterday's closing record.

    if latest["date"] != today.isoformat():
        raise ValueError(
            f"Official close not yet available: "
            f"{ticker} latest={latest['date']}"
        )

    price = safe_num(
        latest.get("close")
    )

    previous_price = safe_num(
        previous.get("close")
    )

    if (
        price is None
        or previous_price is None
        or previous_price <= 0
    ):
        raise ValueError(
            f"Invalid official closing prices: {ticker}"
        )

    daily_return = (
        price / previous_price
    ) - 1

    # Timestamp represents the regular
    # New York market closing time.

    market_close = datetime(
        today.year,
        today.month,
        today.day,
        16,
        0,
        tzinfo=NEW_YORK
    )

    return {
        "realtimePrice": price,
        "return": daily_return,
        "timestamp": int(
            market_close.timestamp()
        )
    }


# =====================================================
# 05 · LOAD EXISTING JSON
# =====================================================

def load_existing():

    if not OUTPUT.exists():
        return {
            "updatedAt": None,
            "quotes": {}
        }

    with OUTPUT.open(
        "r",
        encoding="utf-8"
    ) as file:

        result = json.load(file)

    if not isinstance(result, dict):
        raise ValueError(
            "Invalid existing Market Pulse JSON"
        )

    if not isinstance(
        result.get("quotes"),
        dict
    ):
        raise ValueError(
            "Existing JSON has no valid quotes object"
        )

    return result


# =====================================================
# 06 · MAIN UPDATE ENGINE
# =====================================================

def main():

    if MODE not in ("live", "close"):
        raise ValueError(
            f"Unknown Market Pulse mode: {MODE}"
        )

    print("================================")
    print("NW-111 MARKET PULSE")
    print("MODE:", MODE)
    print("================================")

    result = load_existing()

    quotes = result["quotes"]

    updated_count = 0

    # ---------------------------------------------
    # LIVE MODE · ALL 19 INSTRUMENTS
    # ---------------------------------------------

    if MODE == "live":

        for ticker in TICKERS:

            try:

                quote = fetch_live_quote(ticker)

                quotes[ticker] = quote

                updated_count += 1

                print(
                    "LIVE OK:",
                    ticker,
                    quote["realtimePrice"]
                )

            except Exception as error:

                print(
                    "LIVE ERROR:",
                    ticker,
                    error
                )

                # Preserve existing valid quote.
                # Never replace it with null values.

    # ---------------------------------------------
    # CLOSE MODE · TWO OFFICIAL US INDICES
    # ---------------------------------------------

    elif MODE == "close":

        for ticker in US_INDICES:

            try:

                quote = fetch_official_close(ticker)

                quotes[ticker] = quote

                updated_count += 1

                print(
                    "OFFICIAL CLOSE OK:",
                    ticker,
                    quote["realtimePrice"],
                    quote["return"]
                )

            except Exception as error:

                print(
                    "OFFICIAL CLOSE NOT UPDATED:",
                    ticker,
                    error
                )

                # Preserve the previous quote.

    # ---------------------------------------------
    # WRITE ONLY IF SOMETHING UPDATED
    # ---------------------------------------------

    if updated_count == 0:

        print(
            "No valid new quotes. "
            "Existing JSON preserved."
        )

        return

    result["updatedAt"] = datetime.now(
        timezone.utc
    ).isoformat()

    result["quotes"] = quotes

    # Write to a temporary file first.

    temporary = OUTPUT.with_suffix(
        ".json.tmp"
    )

    temporary.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    temporary.replace(OUTPUT)

    print("--------------------------------")
    print("Market Pulse JSON updated")
    print("Mode:", MODE)
    print("Quotes updated:", updated_count)
    print("Total quotes:", len(quotes))
    print("--------------------------------")


if __name__ == "__main__":
    main()
