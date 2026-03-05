from __future__ import annotations

from app.llm.client import chat_json


def analyze(event_text: str) -> dict:
    schema = {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
            "confidence": {"type": "number"},
            "reasoning": {"type": "string"},
        },
        "required": ["direction", "confidence", "reasoning"],
        "additionalProperties": False,
    }
    prompt = f"分析该事件对A股影响并输出JSON：{event_text}"
    resp = chat_json(
        prompt,
        system="你是事件分析助手，只输出符合schema的JSON。",
        json_schema=schema,
        schema_name="event_analysis",
    )
    if resp.get("ok") and resp.get("parsed"):
        p = resp["parsed"]
        return {
            "direction": str(p.get("direction", "neutral")),
            "confidence": float(p.get("confidence", 0.5)),
            "reasoning": str(p.get("reasoning", "")),
            "source": "llm",
        }
    return {"direction": "neutral", "confidence": 0.55, "reasoning": f"事件占位分析: {event_text[:40]}", "source": "fallback"}

