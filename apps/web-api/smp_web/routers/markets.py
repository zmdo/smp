from __future__ import annotations

from fastapi import APIRouter, Depends

from smp_web.deps import require_user
from smp_web.schemas import MarketQuoteOut
from smp_web.secrets_client import market_quote

router = APIRouter(prefix="/api/markets", dependencies=[Depends(require_user)])


@router.get("/quote", response_model=MarketQuoteOut)
def quote(venue: str, symbol: str, timeframe: str = "1h") -> dict:
    return market_quote(venue, symbol, timeframe)
