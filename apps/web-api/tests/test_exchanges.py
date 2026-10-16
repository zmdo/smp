import ccxt

from smp_ops.exchanges import ExchangeError, clean_symbol, fetch_balances, fetch_quote
from smpcore.exchanges import clean_credentials


class FakeExchange:
    def __init__(self, config):
        self.config = config

    def fetch_balance(self, params):
        self.params = params
        return {
            "info": {"raw": True},
            "USDT": {"free": "1.50000000", "used": "0.50000000", "total": "2"},
            "BTC": {"free": "0", "used": "0", "total": "0"},
            "free": {"USDT": "1.5"},
            "used": {},
            "total": {},
        }

    def fetch_ticker(self, symbol):
        assert symbol == "BTC/USDT"
        return {
            "last": "100.5",
            "bid": "100",
            "ask": "101",
            "high": "110",
            "low": "90",
            "percentage": "1.25",
            "change": "1.2",
            "baseVolume": "12",
            "quoteVolume": "1200",
        }

    def fetch_ohlcv(self, symbol, timeframe, limit):
        assert symbol == "BTC/USDT"
        assert timeframe == "1h"
        assert limit == 120
        return [[1_700_000_000_000, 1, 2, 0.5, 1.5, 3]]

    def close(self):
        self.closed = True


def test_okx_requires_a_passphrase():
    try:
        clean_credentials("okx", {"api_key": "k", "api_secret": "s"})
    except ValueError as exc:
        assert "口令短语" in str(exc)
    else:
        raise AssertionError("missing passphrase should be rejected")


def test_symbol_accepts_each_exchange_separator():
    assert clean_symbol("btc/usdt") == "BTC/USDT"
    assert clean_symbol("BTC-USDT") == "BTC/USDT"
    assert clean_symbol("btc_usdt") == "BTC/USDT"
    try:
        clean_symbol("BTCUSDT")
    except ExchangeError as exc:
        assert "BTC/USDT" in str(exc)
    else:
        raise AssertionError("a symbol without a separator should be rejected")


def test_ccxt_balance_keeps_nonzero_coins(monkeypatch):
    created = {}

    def factory(config):
        client = FakeExchange(config)
        created["client"] = client
        return client

    monkeypatch.setattr(ccxt, "binance", factory)
    monkeypatch.setattr(ccxt, "okx", factory)
    rows = fetch_balances("binance", {"api_key": "k", "api_secret": "s"})
    assert rows == [{"asset": "USDT", "free": "1.5", "locked": "0.5", "total": "2"}]
    assert created["client"].config["apiKey"] == "k"
    assert created["client"].config["secret"] == "s"
    assert created["client"].params == {"type": "spot"}
    assert created["client"].closed is True

    fetch_balances("okx", {"api_key": "k", "api_secret": "s", "passphrase": "phrase"})
    assert created["client"].config["password"] == "phrase"
    assert created["client"].params == {"type": "trading"}


def test_ccxt_quote_uses_unified_symbol(monkeypatch):
    monkeypatch.setattr(ccxt, "gate", lambda config: FakeExchange(config))
    quote = fetch_quote("gate", "btc-usdt", "1h")
    assert quote["symbol"] == "BTC/USDT"
    assert quote["last"] == "100.5"
    assert quote["candles"] == [{"time": 1_700_000_000, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 3.0}]


def test_network_errors_hide_the_secret(monkeypatch):
    secret = "super-secret-value"

    class Broken(FakeExchange):
        def fetch_balance(self, params):
            raise ccxt.NetworkError(f"https://example.test?signature={secret}")

    monkeypatch.setattr(ccxt, "binance", lambda config: Broken(config))
    try:
        fetch_balances("binance", {"api_key": "k", "api_secret": secret})
    except ExchangeError as exc:
        assert str(exc) == "无法连接交易所"
        assert secret not in str(exc)
    else:
        raise AssertionError("network failures should surface as a connection error")
