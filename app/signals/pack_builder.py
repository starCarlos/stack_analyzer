from __future__ import annotations

import sqlite3
from datetime import date

from app.db.database import get_news_conn, get_tracking_conn
from app.llm.news_scorer import score as score_news
from app.llm.policy_scorer import score as score_policy


def rate_policy_event(policy_text: str) -> dict:
    """政策事件矩阵 L1/L2/L3（占位）。"""
    llm = score_policy(policy_text)
    level = "L1" if "货币" in policy_text or "财政" in policy_text else "L2"
    return {
        "level": level,
        "impact": llm["impact"],
        "strength": llm["score"],
        "duration": "short",
    }


def build_signal_pack(news_items: list[dict], candidates: list[dict]) -> dict:
    if not news_items:
        with get_news_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, title, sentiment FROM news_items ORDER BY id DESC LIMIT 10"
            ).fetchall()
            news_items = [dict(r) for r in rows]
    if not candidates:
        with get_tracking_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT symbol, confidence
                FROM price_forecasts
                WHERE target_type='stock'
                ORDER BY id DESC
                LIMIT 5
                """
            ).fetchall()
            candidates = [dict(r) for r in rows]

    advisor_table = []
    for c in candidates[:4]:
        advisor_table.append(
            {
                "role": "fundamental",
                "symbol": c["symbol"],
                "direction": "bullish",
                "confidence": c.get("confidence", 0.6),
            }
        )
    news_scores = [score_news(item.get("title", "")) for item in news_items[:5]]
    policy_matrix = [rate_policy_event(item.get("title", "")) for item in news_items[:3]]
    direction = "bullish"
    if news_scores:
        avg = sum(x.get("score", 0.5) for x in news_scores) / len(news_scores)
        if avg < 0.45:
            direction = "bearish"
        elif avg < 0.55:
            direction = "neutral"
    return {
        "date": str(date.today()),
        "summary": f"基于{len(news_scores)}条新闻和{len(advisor_table)}个候选，市场整体判断为{direction}",
        "news_scores": news_scores,
        "policy_matrix": policy_matrix,
        "advisor_table": advisor_table,
        "consensus": {"direction": direction, "role_agreement": 0.75 if advisor_table else 0.0},
        "divergence_points": ["政策节奏不确定"],
        "triggers": ["跌破MA20减仓", "北向连续净流入增配"],
    }
