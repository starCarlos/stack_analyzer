from __future__ import annotations

from app.llm.client import chat_json


def score(text: str) -> dict:
    schema = {
        "type": "object",
        "properties": {
            "score": {"type": "number"},
            "impact": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
            "level": {"type": "string", "enum": ["L1", "L2", "L3"]},
            "reason": {"type": "string"},
        },
        "required": ["score", "impact", "level", "reason"],
        "additionalProperties": False,
    }
    prompt = f"请对以下政策事件进行L1/L2/L3评级并输出JSON：{text}"
    resp = chat_json(
        prompt,
        system="你是政策分析助手，只输出符合schema的JSON。",
        json_schema=schema,
        schema_name="policy_score",
    )
    if resp.get("ok") and resp.get("parsed"):
        p = resp["parsed"]
        return {
            "score": float(p.get("score", 0.5)),
            "impact": str(p.get("impact", "neutral")),
            "level": str(p.get("level", "L2")),
            "reason": str(p.get("reason", "")),
            "source": "llm",
        }
    return {"score": 0.6, "impact": "neutral", "level": "L2", "reason": text[:60], "source": "fallback"}

