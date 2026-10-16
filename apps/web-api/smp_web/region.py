"""Turn a server address into a short place name."""

from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Callable
from urllib.request import Request, urlopen


def format_place(country: str, region: str, city: str) -> str:
    country, region, city = country.strip(), region.strip(), city.strip()
    parts = [country] if country else []
    if region and region not in parts and len(region) <= 8:
        parts.append(region)
    elif city and city not in parts:
        parts.append(city)
    return " ".join(parts)[:80]


def lookup_region(
    host: str,
    *,
    fetch: Callable[[str], dict] | None = None,
    resolve: Callable[[str], str | None] | None = None,
) -> str | None:
    address = (resolve or _resolve)(host.strip())
    if address is None:
        return None
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return None
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return "内网"
    payload = (fetch or _fetch)(str(ip))
    if payload.get("status") != "success":
        return None
    place = format_place(
        str(payload.get("country") or ""),
        str(payload.get("regionName") or ""),
        str(payload.get("city") or ""),
    )
    return place or None


def _resolve(host: str) -> str | None:
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return None
    public = ""
    fallback = ""
    for info in infos:
        raw = info[4][0]
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        fallback = fallback or raw
        if not (ip.is_private or ip.is_loopback or ip.is_link_local):
            public = raw
            break
    return public or fallback or None


def _fetch(ip: str) -> dict:
    request = Request(
        f"https://ipwho.is/{ip}?lang=zh-CN",
        headers={"User-Agent": "smp"},
    )
    try:
        with urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {"status": "fail"}
    if not isinstance(payload, dict) or not payload.get("success"):
        return {"status": "fail"}
    return {
        "status": "success",
        "country": str(payload.get("country") or ""),
        "regionName": str(payload.get("region") or ""),
        "city": str(payload.get("city") or ""),
    }
