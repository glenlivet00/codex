# marketdata

Python 3.10+ CLI using the unofficial Yahoo Finance API via yfinance. No API key required.

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/marketdata quote AAPL
.venv/bin/marketdata history 7203.T --period 1mo
.venv/bin/marketdata history 7203.T --period 1mo --format csv
.venv/bin/marketdata info BTC-USD
.venv/bin/python -m pytest
```

Quotes use the most recent regular market price (not guaranteed real-time), absolute change and percentage change against the previous close, and currency. History returns date, open, high, low, close and volume; yfinance's default price adjustments apply. Info returns name, sector and market; unavailable optional fields are null.

Successful data goes to stdout. Failures return exit code 1 and a JSON `error` on stderr. Transient failures retry at most twice with 1s and 2s delays; persistent rate limits produce an explicit 429 error. Yahoo may restrict cloud IPs. Unit tests mock yfinance and make no external requests.
