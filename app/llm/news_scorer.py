from __future__ import annotations

from app.llm.client import chat_json


def score(title: str) -> dict:
    schema = {
        "type": "object",
        "properties": {
            "score": {"type": "number"},
            "summary": {"type": "string"},
            "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
        },
        "required": ["score", "summary", "sentiment"],
        "additionalProperties": False,
    }
    prompt = f"请对以下新闻标题做投资影响评分（0~1）并输出JSON：{title}"
    resp = chat_json(
        prompt,
        system="你是A股新闻分析助手，只输出符合schema的JSON。",
        json_schema=schema,
        schema_name="news_score",
    )
    if resp.get("ok") and resp.get("parsed"):
        p = resp["parsed"]
        return {
            "title": title,
            "score": float(p.get("score", 0.5)),
            "summary": str(p.get("summary", "")),
            "sentiment": str(p.get("sentiment", "neutral")),
            "source": "llm",
        }
    return {"title": title, "score": 0.66, "summary": "占位新闻评分", "sentiment": "neutral", "source": "fallback"}

