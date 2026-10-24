"""JSON-first command line interface to yfinance."""
import argparse
import contextlib
import csv
import json
import io
import math
import sys
import time

import yfinance as yf
from yfinance.exceptions import YFRateLimitError


class MarketDataError(Exception):
    """An actionable market data failure."""


def number(value):
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def fetch(args):
    ticker = yf.Ticker(args.ticker)
    if args.command == "history":
        frame = ticker.history(period=args.period, raise_errors=True)
        if frame.empty:
            raise MarketDataError(f"No price history found for {args.ticker}")
        return [dict(date=index.isoformat(), **{
            key.lower(): number(row[key]) for key in ("Open", "High", "Low", "Close", "Volume")
        }) for index, row in frame.iterrows()]
    data = ticker.get_info()
    if args.command == "info":
        name = data.get("longName") or data.get("shortName")
        if not name:
            raise MarketDataError(f"No instrument information found for {args.ticker}")
        return dict(ticker=args.ticker, name=name, sector=data.get("sector"),
                    market=data.get("fullExchangeName") or data.get("exchange"))
    price = number(data.get("regularMarketPrice"))
    previous = number(data.get("regularMarketPreviousClose") or data.get("previousClose"))
    if price is None or previous is None or not data.get("currency"):
        raise MarketDataError(f"No valid quote found for {args.ticker}")
    change = price - previous
    return dict(ticker=args.ticker, price=price, change=change,
                change_percent=change / previous * 100 if previous else None,
                currency=data["currency"])


def fetch_with_retry(args):
    for attempt in range(3):
        try:
            return fetch(args)
        except MarketDataError:
            raise
        except Exception as exc:
            limited = isinstance(exc, YFRateLimitError) or "429" in str(exc)
            if attempt == 2:
                if limited:
                    raise MarketDataError("Yahoo Finance rate limit (429) persisted after 2 retries; try again later.") from exc
                raise MarketDataError(f"Unable to fetch {args.ticker}: {exc}") from exc
            time.sleep(2 ** attempt)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise MarketDataError(message)


def main(argv=None):
    try:
        parser = Parser(prog="marketdata")
        sub = parser.add_subparsers(dest="command", required=True)
        for command in ("quote", "history", "info"):
            child = sub.add_parser(command)
            child.add_argument("ticker")
            if command == "history":
                child.add_argument("--period", default="1mo")
                child.add_argument("--format", choices=("json", "csv"), default="json")
        args = parser.parse_args(argv)
        # Some yfinance diagnostics use stdout; keep the data stream parseable.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = fetch_with_retry(args)
        if getattr(args, "format", "json") == "csv":
            writer = csv.DictWriter(sys.stdout, fieldnames=["date", "open", "high", "low", "close", "volume"])
            writer.writeheader()
            writer.writerows(result)
        else:
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
