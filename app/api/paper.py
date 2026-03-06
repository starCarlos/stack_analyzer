from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.database import get_tracking_conn
from app.core import paper_trader

router = APIRouter(tags=["paper"])


@router.get("/paper/status")
def paper_status() -> dict:
    return paper_trader.get_status()


@router.get("/paper/trades")
def paper_trades(days: int = Query(default=30, ge=1, le=365)) -> dict:
    with get_tracking_conn() as conn:
        rows = conn.execute(
            """
            SELECT trade_date, symbol, action, quantity, price, commission, stamp_tax, reason
            FROM paper_trades
            WHERE trade_date >= date('now', ?)
            ORDER BY trade_date DESC, id DESC
            """,
            (f"-{days} day",),
        ).fetchall()
    items = [
        {
            "trade_date": r[0],
            "symbol": r[1],
            "action": r[2],
            "quantity": int(r[3] or 0),
            "price": float(r[4] or 0.0),
            "commission": float(r[5] or 0.0),
            "stamp_tax": float(r[6] or 0.0),
            "reason": r[7] or "",
        }
        for r in rows
    ]
    return {"days": days, "count": len(items), "items": items}


@router.get("/paper/equity-curve")
def paper_equity_curve() -> dict:
    with get_tracking_conn() as conn:
        rows = conn.execute(
            """
            SELECT snapshot_date, total_value, daily_return, cumulative_return, max_drawdown
            FROM paper_snapshots
            ORDER BY snapshot_date ASC
            """
        ).fetchall()
    points = [
        {
            "date": r[0],
            "value": float(r[1] or 0.0),
            "daily_return": float(r[2] or 0.0),
            "cumulative_return": float(r[3] or 0.0),
            "max_drawdown": float(r[4] or 0.0),
        }
        for r in rows
    ]
    return {"count": len(points), "points": points}
