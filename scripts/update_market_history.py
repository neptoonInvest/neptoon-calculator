    params = urllib.parse.urlencode({
        "api_token": token,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "period": "d",
        "fmt": "json",
        "order": "a",
    })
    url = "https://eodhd.com/api/eod/" + urllib.parse.quote(ticker, safe="") + "?" + params
    request = urllib.request.Request(url, headers={"User-Agent": "NeptoonHistory/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        rows = json.load(response)
    if not isinstance(rows, list):
        raise ValueError("EODHD response is not a list")
    prices = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        day, raw = row.get("date"), row.get("close")
        if not isinstance(day, str):
            continue
        try:
            parsed_day = date.fromisoformat(day)
            close = float(raw)
        except (ValueError, TypeError):
            continue
        if start <= parsed_day <= end and math.isfinite(close) and close > 0:
            prices[day] = close
    if not prices:
        raise ValueError("No valid closing prices")
    return [[day, prices[day]] for day in sorted(prices)]


def main():
    token = os.environ["EODHD_TOKEN"]
    with CONFIG.open(encoding="utf-8") as handle:
        tickers = json.load(handle)["tickers"]
    if len(tickers) != 25 or len(set(tickers)) != 25:
        raise ValueError("Configuration must contain 25 unique tickers")

    today = datetime.now(COPENHAGEN).date()
    start = three_years_ago(today)
    previous = load_previous()
    instruments = {}
    successful = 0

    for ticker in tickers:
        try:
            prices = fetch_closes(ticker, start, today, token)
            instruments[ticker] = {"prices": prices}
            successful += 1
            print(f"OK {ticker}: {len(prices)} observations through {prices[-1][0]}")
        except Exception as exc:
            print(f"FAILED {ticker}: {exc}")
            old = previous.get(ticker, {})
            old_prices = old.get("prices", []) if isinstance(old, dict) else []
            valid_old = [p for p in old_prices if isinstance(p, list) and len(p) == 2 and isinstance(p[0], str) and start.isoformat() <= p[0] <= today.isoformat()]
            if valid_old:
                instruments[ticker] = {"prices": valid_old}
                print(f"PRESERVED {ticker}: {len(valid_old)} cached observations")

    if not instruments:
        raise RuntimeError("No history available; existing JSON left unchanged")
    payload = {
        "version": "1.0",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "priceField": "close",
        "adjusted": False,
        "windowStart": start.isoformat(),
        "windowEnd": today.isoformat(),
        "instruments": instruments,
    }
    tmp = OUTPUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(OUTPUT)
    print(f"History cache saved: {successful} fresh / {len(instruments)} available / 25 configured")


if __name__ == "__main__":
    main()
