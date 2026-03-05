from __future__ import annotations


def execute_daily(candidates: list[dict] | None = None, current_prices: dict | None = None) -> dict:
    return {
        "executed": True,
        "trade_count": 1 if candidates else 0,
        "summary": "占位纸面交易执行完成",
    }


def get_status() -> dict:
    return {"cash": 845000.0, "total_value": 1052000.0, "cumulative_return": 0.052, "max_drawdown": -0.031}
