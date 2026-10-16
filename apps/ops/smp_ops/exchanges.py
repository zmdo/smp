"""Exchange balances and public quotes through ccxt. Credentials stay inside ops."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from smpcore.exchanges import clean_credentials, venue_by_id


class ExchangeError(Exception):
    pass


TIMEFRAMES = ("1m", "15m", "1h", "4h", "1d")
_BALANCE_SKIP = {"info", "free", "used", "total", "timestamp", "datetime", "debt"}
_BALANCE_PARAMS = {
    "binance": {"type": "spot"},
    "okx": {"type": "trading"},
    "bybit": {},
    "gate": {"type": "spot"},
}


def fetch_balances(venue: str, credentials: dict) -> list[dict]:
    cleaned = _credentials(venue, credentials)
    client = _client(venue, cleaned)
    try:
        balance = client.fetch_balance(_BALANCE_PARAMS[venue])
    except Exception as exc:
        raise _wrap(exc, cleaned) from exc
    finally:
        _close(client)
    if not isinstance(balance, dict):
        raise ExchangeError("交易所没有返回余额")
    rows = []
    for asset, item in balance.items():
        if asset in _BALANCE_SKIP or not isinstance(item, dict):
            continue
        free = _decimal(item.get("free"))
        locked = _decimal(item.get("used"))
        total = item.get("total")
        total_amount = free + locked if total is None else _decimal(total)
        if free == 0 and locked == 0 and total_amount == 0:
            continue
        rows.append(
            {
                "asset": str(asset),
                "free": _plain(free),
                "locked": _plain(locked),
                "total": _plain(total_amount),
            }
        )
    return sorted(rows, key=lambda item: item["asset"])


def fetch_quote(venue: str, symbol: str, timeframe: str) -> dict:
    _known_venue(venue)
    pair = clean_symbol(symbol)
    period = clean_timeframe(timeframe)
    client = _client(venue, None)
    try:
        ticker = client.fetch_ticker(pair)
        candles = client.fetch_ohlcv(pair, period, limit=120)
    except Exception as exc:
        raise _wrap(exc, {}) from exc
    finally:
        _close(client)
    if not isinstance(ticker, dict):
        raise ExchangeError("交易所没有返回行情")
    return {
        "symbol": pair,
        "timeframe": period,
        "last": _text(ticker.get("last")),
        "bid": _text(ticker.get("bid")),
        "ask": _text(ticker.get("ask")),
        "high": _text(ticker.get("high")),
        "low": _text(ticker.get("low")),
        "percentage": _text(ticker.get("percentage")),
        "change": _text(ticker.get("change")),
        "base_volume": _text(ticker.get("baseVolume")),
        "quote_volume": _text(ticker.get("quoteVolume")),
        "candles": _candles(candles),
    }


def clean_symbol(symbol: str) -> str:
    text = str(symbol or "").strip().upper().replace("-", "/").replace("_", "/")
    base, separator, quote = text.partition("/")
    if not separator or not base.isalnum() or not quote.isalnum():
        raise ExchangeError("交易码格式应为 BTC/USDT")
    if len(base) > 20 or len(quote) > 20:
        raise ExchangeError("交易码过长")
    return f"{base}/{quote}"


def clean_timeframe(timeframe: str) -> str:
    text = str(timeframe or "").strip()
    if text not in TIMEFRAMES:
        raise ExchangeError("不支持这个周期")
    return text


def _credentials(venue: str, credentials: dict) -> dict[str, str]:
    try:
        return clean_credentials(venue, credentials)
    except ValueError as exc:
        raise ExchangeError(str(exc)) from exc


def _known_venue(venue: str) -> None:
    try:
        venue_by_id(venue)
    except ValueError as exc:
        raise ExchangeError(str(exc)) from exc


def _client(venue: str, credentials: dict[str, str] | None):
    import ccxt

    _known_venue(venue)
    config: dict = {"enableRateLimit": True, "timeout": 15000, "options": {"defaultType": "spot"}}
    if credentials:
        config["apiKey"] = credentials["api_key"]
        config["secret"] = credentials["api_secret"]
        if credentials.get("passphrase"):
            config["password"] = credentials["passphrase"]
    return getattr(ccxt, venue)(config)


def _close(client) -> None:
    close = getattr(client, "close", None)
    if close is not None:
        close()


def _wrap(exc: Exception, secrets: dict[str, str]) -> ExchangeError:
    if isinstance(exc, ExchangeError):
        return exc
    import ccxt

    if isinstance(exc, ccxt.RequestTimeout):
        return ExchangeError("连接交易所超时")
    if isinstance(exc, ccxt.NetworkError):
        return ExchangeError("无法连接交易所")
    if isinstance(exc, ccxt.BadSymbol):
        return ExchangeError("这个交易所没有该交易码")
    if isinstance(exc, ccxt.BaseError):
        return ExchangeError(_public(exc, secrets))
    return ExchangeError("查询失败")


def _public(exc: Exception, secrets: dict[str, str]) -> str:
    text = str(exc)
    for value in secrets.values():
        if value:
            text = text.replace(value, "")
    text = " ".join(text.split())
    if not text:
        return "交易所拒绝了这次查询"
    return text[:180]


def _decimal(value: object) -> Decimal:
    if value is None or value == "":
        return Decimal(0)
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal(0)


def _plain(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _text(value: object) -> str | None:
    if value is None or value == "":
        return None
    return _plain(_decimal(value))


def _candles(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    rows = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) < 6:
            continue
        try:
            moment = int(item[0])
        except (TypeError, ValueError):
            continue
        if moment > 10_000_000_000:
            moment //= 1000
        rows.append(
            {
                "time": moment,
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
            }
        )
    return rows
