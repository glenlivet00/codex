import json
from unittest.mock import Mock

import pandas as pd
import pytest
from yfinance.exceptions import YFRateLimitError

from marketdata import cli


@pytest.fixture
def ticker(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(cli.yf, "Ticker", factory)
    monkeypatch.setattr(cli.time, "sleep", Mock())
    return factory


def test_quote(ticker, capsys):
    ticker.return_value.get_info.return_value = dict(regularMarketPrice=105, previousClose=100, currency="USD")
    assert cli.main(["quote", "AAPL"]) == 0
    assert json.loads(capsys.readouterr().out) == dict(ticker="AAPL", price=105, change=5, change_percent=5, currency="USD")
    ticker.assert_called_with("AAPL")


@pytest.mark.parametrize("format", ["json", "csv"])
def test_history(ticker, capsys, format):
    ticker.return_value.history.return_value = pd.DataFrame(
        {"Open": [1], "High": [3], "Low": [1], "Close": [2], "Volume": [100]},
        index=pd.to_datetime(["2026-10-23"]))
    assert cli.main(["history", "7203.T", "--period", "1mo", "--format", format]) == 0
    output = capsys.readouterr().out
    if format == "json":
        assert json.loads(output)[0]["volume"] == 100
    else:
        assert output.startswith("date,open,high,low,close,volume")
    ticker.assert_called_with("7203.T")
    ticker.return_value.history.assert_called_once_with(period="1mo", raise_errors=True)


def test_info(ticker, capsys):
    ticker.return_value.get_info.return_value = dict(longName="Bitcoin", exchange="CCC")
    assert cli.main(["info", "BTC-USD"]) == 0
    assert json.loads(capsys.readouterr().out)["market"] == "CCC"
    ticker.assert_called_with("BTC-USD")


def test_invalid(ticker, capsys):
    ticker.return_value.get_info.return_value = {}
    assert cli.main(["quote", "INVALIDTICKER"]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "No valid quote" in json.loads(captured.err)["error"]


def test_rate_limit(ticker, capsys):
    ticker.return_value.get_info.side_effect = YFRateLimitError()
    assert cli.main(["quote", "AAPL"]) == 1
    assert "429" in json.loads(capsys.readouterr().err)["error"]
    assert ticker.call_count == 3
    assert [call.args[0] for call in cli.time.sleep.call_args_list] == [1, 2]


def test_retry_success(ticker, capsys):
    ticker.return_value.get_info.side_effect = [ConnectionError("temporary"), dict(regularMarketPrice=10, previousClose=9, currency="USD")]
    assert cli.main(["quote", "AAPL"]) == 0
    assert json.loads(capsys.readouterr().out)["price"] == 10


def test_bad_arguments(capsys):
    assert cli.main(["history"]) == 1
    assert "error" in json.loads(capsys.readouterr().err)
