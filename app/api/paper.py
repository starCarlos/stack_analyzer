from __future__ import annotations

from fastapi import APIRouter, Query

from app.core import paper_trader

router = APIRouter(tags=["paper"])


@router.get("/paper/status")
def paper_status() -> dict:
    return paper_trader.get_status()


@router.get("/paper/trades")
def paper_trades(days: int = Query(default=30, ge=1, le=365)) -> dict:
    return {"days": days, "items": [{"trade_date": "2026-03-05", "symbol": "600519.SH", "action": "buy", "quantity": 100}]}


@router.get("/paper/equity-curve")
def paper_equity_curve() -> dict:
    return {"points": [{"date": "2026-03-01", "value": 1000000}, {"date": "2026-03-05", "value": 1052000}]}
