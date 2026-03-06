from __future__ import annotations

import sqlite3
from datetime import date

from app.db.database import get_tracking_conn


def _get_close(conn: sqlite3.Connection, symbol: str, trade_date: str) -> float | None:
    row = conn.execute(
        """
        SELECT close FROM market_price_bars
        WHERE symbol=? AND trade_date=? AND source='akshare'
        LIMIT 1
        """,
        (symbol, trade_date),
    ).fetchone()
    if row and row[0] is not None:
        return float(row[0])
    row2 = conn.execute(
        """
        SELECT close FROM market_price_bars
        WHERE symbol=? AND trade_date=?
        ORDER BY source
        LIMIT 1
        """,
        (symbol, trade_date),
    ).fetchone()
    return float(row2[0]) if row2 and row2[0] is not None else None


def actual_return_from_bars(conn: sqlite3.Connection, symbol: str, forecast_date: str, window_days: int) -> float | None:
    start_row = conn.execute(
        """
        SELECT trade_date, close
        FROM market_price_bars
        WHERE symbol=? AND trade_date>=?
        ORDER BY trade_date ASC
        LIMIT 1
        """,
        (symbol, forecast_date),
    ).fetchone()
    if not start_row:
        return None
    start_date = start_row[0]
    start_close = float(start_row[1]) if start_row[1] is not None else None
    if not start_close or start_close <= 0:
        return None
    rows = conn.execute(
        """
        SELECT trade_date, close
        FROM market_price_bars
        WHERE symbol=? AND trade_date>=? AND close IS NOT NULL
        ORDER BY trade_date ASC
        LIMIT ?
        """,
        (symbol, start_date, max(1, int(window_days) + 1)),
    ).fetchall()
    if len(rows) < 2:
        return None
    end_close = float(rows[-1][1])
    return round(end_close / start_close - 1, 6)


def evaluate_due_forecasts() -> dict:
    today = str(date.today())
    evaluated = 0
    skipped_no_data = 0
    with get_tracking_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, symbol, window_days, predicted_return, predicted_direction, forecast_date, target_date
            FROM price_forecasts
            WHERE target_type='stock' AND target_date<=?
            """,
            (today,),
        ).fetchall()
        for r in rows:
            exists = conn.execute(
                "SELECT 1 FROM forecast_evaluations WHERE forecast_id=? LIMIT 1",
                (r["id"],),
            ).fetchone()
            if exists:
                continue
            actual = actual_return_from_bars(conn, r["symbol"], r["forecast_date"], int(r["window_days"] or 5))
            if actual is None:
                skipped_no_data += 1
                continue
            actual_dir = "up" if actual > 0.002 else ("down" if actual < -0.002 else "flat")
            pred_dir = r["predicted_direction"] or "flat"
            direction_hit = 1 if pred_dir == actual_dir else 0
            abs_error = abs(float(r["predicted_return"] or 0.0) - actual)
            conn.execute(
                """
                INSERT INTO forecast_evaluations
                (forecast_id, symbol, target_type, window_days, predicted_return, actual_return, direction_hit, abs_error)
                VALUES (?, ?, 'stock', ?, ?, ?, ?, ?)
                """,
                (
                    r["id"],
                    r["symbol"],
                    r["window_days"],
                    float(r["predicted_return"] or 0.0),
                    actual,
                    direction_hit,
                    abs_error,
                ),
            )
            evaluated += 1
        conn.commit()

    with get_tracking_conn() as conn:
        hit = conn.execute(
            "SELECT AVG(direction_hit) FROM (SELECT direction_hit FROM forecast_evaluations ORDER BY id DESC LIMIT 200)"
        ).fetchone()[0]
    return {
        "date": today,
        "evaluated_count": evaluated,
        "skipped_no_data": skipped_no_data,
        "hit_rate": round(float(hit or 0.0), 4),
        "status": "ok",
    }
