"""Supported exchanges and the credential fields each one asks for."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExchangeField:
    key: str
    label: str


@dataclass(frozen=True)
class ExchangeVenue:
    id: str
    name: str
    wallet: str
    fields: tuple[ExchangeField, ...]


VENUES: tuple[ExchangeVenue, ...] = (
    ExchangeVenue(
        "binance",
        "币安",
        "现货账户",
        (ExchangeField("api_key", "API Key"), ExchangeField("api_secret", "API Secret")),
    ),
    ExchangeVenue(
        "okx",
        "欧易",
        "交易账户",
        (
            ExchangeField("api_key", "API Key"),
            ExchangeField("api_secret", "API Secret"),
            ExchangeField("passphrase", "口令短语"),
        ),
    ),
    ExchangeVenue(
        "bybit",
        "Bybit",
        "统一账户",
        (ExchangeField("api_key", "API Key"), ExchangeField("api_secret", "API Secret")),
    ),
    ExchangeVenue(
        "gate",
        "Gate",
        "现货账户",
        (ExchangeField("api_key", "API Key"), ExchangeField("api_secret", "API Secret")),
    ),
)


def venue_by_id(venue: str) -> ExchangeVenue:
    for item in VENUES:
        if item.id == venue:
            return item
    raise ValueError("不支持这个交易所")


def clean_credentials(venue: str, raw: dict) -> dict[str, str]:
    spec = venue_by_id(venue)
    if not isinstance(raw, dict):
        raise ValueError("请填写 API 凭证")
    cleaned: dict[str, str] = {}
    for field in spec.fields:
        value = raw.get(field.key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"请填写{field.label}")
        text = value.strip()
        if len(text) > 400:
            raise ValueError(f"{field.label}过长")
        cleaned[field.key] = text
    return cleaned
