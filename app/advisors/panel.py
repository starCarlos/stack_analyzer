from __future__ import annotations

from collections import Counter
from datetime import date

ROLES = [
    {"id": "fundamental", "name": "基本面角色", "focus": "盈利质量与估值"},
    {"id": "risk", "name": "风险角色", "focus": "下行风险与黑天鹅"},
    {"id": "policy", "name": "政策角色", "focus": "政策与监管方向"},
    {"id": "supply_chain", "name": "产业链角色", "focus": "供需与库存周期"},
]

PERSONAS = [
    {"id": "li_xunlei", "name": "李迅雷风格"},
    {"id": "fu_peng", "name": "付鹏风格"},
    {"id": "ren_zeping", "name": "任泽平风格"},
]


def _mock_role_judgement(symbol: str, role_id: str) -> dict:
    base = {
        "fundamental": ("bullish", 0.72),
        "risk": ("neutral", 0.58),
        "policy": ("bullish", 0.68),
        "supply_chain": ("bullish", 0.64),
    }
    direction, confidence = base.get(role_id, ("neutral", 0.5))
    return {
        "symbol": symbol,
        "role": role_id,
        "direction": direction,
        "confidence": confidence,
        "reasoning": f"{role_id} 视角下结论",
    }


def role_agreement(votes: list[str]) -> float:
    if not votes:
        return 0.0
    cnt = Counter(votes)
    return max(cnt.values()) / len(votes)


def analyze_with_roles(symbol: str, min_agreement: float = 0.6) -> dict:
    role_outputs = [_mock_role_judgement(symbol, role["id"]) for role in ROLES]
    votes = [r["direction"] for r in role_outputs]
    agree = role_agreement(votes)
    top_vote = Counter(votes).most_common(1)[0][0] if votes else "neutral"
    final_direction = top_vote if agree >= min_agreement else "hold"
    return {
        "symbol": symbol,
        "date": str(date.today()),
        "roles": role_outputs,
        "role_agreement": round(agree, 4),
        "consensus_direction": final_direction,
        "personas": PERSONAS,
    }

