from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app.db.database import get_tracking_conn


def _load_rules() -> dict:
    path = Path("config/decision_rules.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest_snapshot() -> dict:
    with get_tracking_conn() as conn:
        row = conn.execute(
            """
            SELECT snapshot_date, cash, positions_json, total_value, daily_return, cumulative_return, max_drawdown
            FROM paper_snapshots
            ORDER BY snapshot_date DESC
            LIMIT 1
            """
        ).fetchone()
    if not row:
        init_cash = float(__import__("os").getenv("PAPER_INITIAL_CASH", "1000000"))
        return {
            "snapshot_date": str(date.today()),
            "cash": init_cash,
            "positions": {},
            "total_value": init_cash,
            "daily_return": 0.0,
            "cumulative_return": 0.0,
            "max_drawdown": 0.0,
        }
    return {
        "snapshot_date": row[0],
        "cash": float(row[1] or 0.0),
        "positions": json.loads(row[2] or "{}"),
        "total_value": float(row[3] or 0.0),
        "daily_return": float(row[4] or 0.0),
        "cumulative_return": float(row[5] or 0.0),
        "max_drawdown": float(row[6] or 0.0),
    }


def execute_daily(candidates: list[dict] | None = None, current_prices: dict | None = None) -> dict:
    candidates = candidates or []
    current_prices = current_prices or {}
    rules = _load_rules()
    pos = rules.get("position", {})
    a = rules.get("a_share_rules", {})
    max_daily_buy = float(pos.get("max_daily_buy_pct", 0.05))
    commission_rate = float(a.get("commission_rate", 0.0003))
    commission_min = float(a.get("commission_min", 5.0))
    stamp_tax_rate = float(a.get("stamp_tax_rate", 0.0005))
    lot_size = int(a.get("lot_size", 100))

    st = _latest_snapshot()
    initial_cash = float(__import__("os").getenv("PAPER_INITIAL_CASH", "1000000"))
    cash = float(st["cash"])
    positions = dict(st["positions"])
    total_value = float(st["total_value"]) if st["total_value"] > 0 else cash
    daily_budget = total_value * max_daily_buy
    used_budget = 0.0
    trades = []
    sell_count = 0
    buy_count = 0
    today = str(date.today())

    with get_tracking_conn() as conn:
        # 1) 先处理卖出（止损/止盈）
        stop_loss_pct = float(rules.get("stop_loss_pct", 0.08))
        default_take_profit_pct = float(__import__("os").getenv("PAPER_TAKE_PROFIT_PCT", "0.12"))
        candidate_map = {str(c.get("symbol")): c for c in candidates}
        for symbol, p in list(positions.items()):
            qty = int(p.get("qty", 0))
            if qty <= 0:
                continue
            avg_cost = float(p.get("avg_cost", 0) or 0)
            px = float(current_prices.get(symbol) or avg_cost)
            if px <= 0 or avg_cost <= 0:
                continue
            take_profit_price = float(candidate_map.get(symbol, {}).get("take_profit_price") or (avg_cost * (1 + default_take_profit_pct)))
            stop_loss_price = float(candidate_map.get(symbol, {}).get("stop_loss_price") or (avg_cost * (1 - stop_loss_pct)))
            should_sell = px >= take_profit_price or px <= stop_loss_price
            if not should_sell:
                continue
            gross = qty * px
            commission = max(commission_min, gross * commission_rate)
            stamp_tax = gross * stamp_tax_rate
            received = gross - commission - stamp_tax
            cash += received
            reason = "take_profit" if px >= take_profit_price else "stop_loss"
            trades.append(
                {
                    "symbol": symbol,
                    "action": "sell",
                    "quantity": qty,
                    "price": px,
                    "commission": commission,
                    "stamp_tax": stamp_tax,
                    "reason": reason,
                }
            )
            sell_count += 1
            conn.execute(
                """
                INSERT INTO paper_trades(symbol, trade_date, action, quantity, price, commission, stamp_tax, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (symbol, today, "sell", qty, px, commission, stamp_tax, reason),
            )
            positions.pop(symbol, None)

        # 2) 再处理买入
        for c in sorted(candidates, key=lambda x: float(x.get("confidence", 0)), reverse=True):
            symbol = str(c.get("symbol"))
            price = float(current_prices.get(symbol) or c.get("entry_price") or c.get("current_price") or 0)
            if price <= 0:
                continue
            target_cash = min(daily_budget - used_budget, total_value * float(c.get("suggested_position_pct", 0)))
            if target_cash <= 0:
                continue
            qty = int(target_cash // price // lot_size) * lot_size
            if qty <= 0:
                continue
            gross = qty * price
            commission = max(commission_min, gross * commission_rate)
            cost = gross + commission
            if cost > cash:
                continue
            cash -= cost
            used_budget += gross
            pos0 = positions.get(symbol, {"qty": 0, "cost": 0.0})
            new_qty = int(pos0.get("qty", 0)) + qty
            new_cost = float(pos0.get("cost", 0.0)) + cost
            positions[symbol] = {"qty": new_qty, "cost": round(new_cost, 2), "avg_cost": round(new_cost / new_qty, 4)}
            trades.append({"symbol": symbol, "action": "buy", "quantity": qty, "price": price, "commission": commission, "stamp_tax": 0.0})
            buy_count += 1
            conn.execute(
                """
                INSERT INTO paper_trades(symbol, trade_date, action, quantity, price, commission, stamp_tax, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (symbol, today, "buy", qty, price, commission, 0.0, c.get("reason", "candidate")),
            )

        # 估算账户价值
        market_value = 0.0
        for symbol, p in positions.items():
            px = float(current_prices.get(symbol) or p.get("avg_cost", 0))
            market_value += int(p.get("qty", 0)) * px
        total_value_new = cash + market_value
        cumulative_return = (total_value_new / initial_cash - 1) if initial_cash else 0.0
        peak = max(total_value_new, st["total_value"] or total_value_new)
        dd = (total_value_new / peak - 1) if peak else 0.0

        conn.execute(
            """
            INSERT OR REPLACE INTO paper_snapshots(snapshot_date, cash, positions_json, total_value, daily_return, cumulative_return, max_drawdown)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                today,
                cash,
                json.dumps(positions, ensure_ascii=False),
                total_value_new,
                (total_value_new / st["total_value"] - 1) if st["total_value"] else 0.0,
                cumulative_return,
                min(float(st["max_drawdown"]), dd),
            ),
        )
        conn.commit()

    return {
        "executed": True,
        "trade_count": len(trades),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "used_budget": round(used_budget, 2),
        "daily_budget": round(daily_budget, 2),
        "cash": round(cash, 2),
        "summary": "纸面交易执行完成",
    }


def get_status() -> dict:
    st = _latest_snapshot()
    return {
        "cash": round(float(st["cash"]), 2),
        "positions": st["positions"],
        "total_value": round(float(st["total_value"]), 2),
        "daily_return": round(float(st["daily_return"]), 4),
        "cumulative_return": round(float(st["cumulative_return"]), 4),
        "max_drawdown": round(float(st["max_drawdown"]), 4),
    }
