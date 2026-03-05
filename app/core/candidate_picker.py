from __future__ import annotations

import json
from pathlib import Path

from app.core.data_manager import get_symbol_name_map
from app.core.forecaster import forecast_all


def _load_decision_rules() -> dict:
    path = Path("config/decision_rules.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _mock_current_price(symbol: str) -> float:
    base = (sum(ord(c) for c in symbol) % 800) + 80
    return round(base / 10, 2)


def _build_trade_plan(symbol: str, confidence: float) -> dict:
    rules = _load_decision_rules()
    position_rule = rules.get("position", {})
    stop_loss_pct = float(rules.get("stop_loss_pct", 0.08))
    max_single = float(position_rule.get("max_single_pct", 0.1))
    current_price = _mock_current_price(symbol)
    entry_price = current_price
    take_profit_price = round(entry_price * (1 + (0.08 + confidence * 0.06)), 2)
    stop_loss_price = round(entry_price * (1 - stop_loss_pct), 2)
    suggested_position_pct = round(min(max_single, max(0.02, confidence * 0.15)), 4)
    return {
        "current_price": current_price,
        "entry_price": entry_price,
        "take_profit_price": take_profit_price,
        "stop_loss_price": stop_loss_price,
        "suggested_position_pct": suggested_position_pct,
    }


def pick() -> dict:
    names = get_symbol_name_map()
    raw = [
        {"symbol": "600519.SH", "confidence": 0.72, "reason": "估值和趋势共振"},
        {"symbol": "300750.SZ", "confidence": 0.65, "reason": "资金连续净流入"},
    ]
    candidates = []
    for item in raw:
        c = dict(item)
        c["name"] = names.get(c["symbol"], c["symbol"])
        c["target_type"] = "stock"
        c.update(_build_trade_plan(c["symbol"], float(c["confidence"])))
        candidates.append(c)
    return {"date": "today", "candidates": candidates}


def annotate_risk_with_llm(candidates: list[dict]) -> list[dict]:
    enriched = []
    for item in candidates:
        c = dict(item)
        c["risk_tag"] = "中"
        c["risk_reason"] = "波动可控，仍需跟踪政策节奏"
        enriched.append(c)
    return enriched


def build_buy_candidates() -> dict:
    stock_candidates = annotate_risk_with_llm(pick()["candidates"])
    fc = forecast_all()

    sectors = []
    for s in fc.get("sectors", {}).get("bullish", [])[:3]:
        confidence = float(s.get("confidence", 0.55))
        pseudo_symbol = f"SECTOR::{s.get('name','未知')}"
        plan = _build_trade_plan(pseudo_symbol, confidence)
        sectors.append(
            {
                "target_type": "sector",
                "name": s.get("name", "未知板块"),
                "symbol": pseudo_symbol,
                "confidence": confidence,
                "reason": "板块预测看好",
                **plan,
            }
        )

    market = fc.get("market", {})
    m_conf = float(market.get("confidence", 0.5))
    direction = market.get("direction", "flat")
    action = "观望"
    target_position_pct = 0.4
    if direction == "up" and m_conf >= 0.6:
        action = "加仓"
        target_position_pct = 0.6
    elif direction == "down" and m_conf >= 0.55:
        action = "减仓"
        target_position_pct = 0.3
    market_plan = {
        "target_type": "market",
        "benchmark": market.get("symbol", "000300.SH"),
        "direction": direction,
        "confidence": m_conf,
        "action": action,
        "target_position_pct": target_position_pct,
        "trigger_add": "沪深300站上MA20且北向连续净流入",
        "trigger_reduce": "沪深300跌破MA20且成交放大",
    }

    return {
        "date": "today",
        "stocks": stock_candidates,
        "sectors": sectors,
        "market": market_plan,
    }
