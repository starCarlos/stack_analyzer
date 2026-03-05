from __future__ import annotations

from datetime import datetime

from app.db.database import get_news_conn
from app.core.data_manager import get_symbols


def _to_ak_symbol(symbol: str) -> str:
    return symbol.split(".")[0].strip()


def _fetch_real_news(limit_per_symbol: int = 20) -> list[dict]:
    items: list[dict] = []
    try:
        import akshare as ak  # type: ignore

        for s in get_symbols():
            code = _to_ak_symbol(s)
            try:
                df = ak.stock_news_em(symbol=code)
                if df is None or df.empty:
                    continue
                for _, row in df.head(limit_per_symbol).iterrows():
                    title = str(row.get("新闻标题") or row.get("标题") or "").strip()
                    if not title:
                        continue
                    items.append(
                        {
                            "title": title,
                            "publish_time": str(row.get("发布时间") or row.get("时间") or "")[:19],
                            "source": str(row.get("文章来源") or row.get("来源") or "akshare"),
                            "url": str(row.get("新闻链接") or row.get("链接") or ""),
                            "content": str(row.get("新闻内容") or row.get("内容") or "")[:4000],
                            "sentiment": "neutral",
                            "symbol": s,
                        }
                    )
            except Exception:
                continue
    except Exception:
        return []
    return items

def crawl_today() -> dict:
    real_items = _fetch_real_news()
    use_mock = not real_items
    items = (
        [
            {"id": 1, "title": "央行释放流动性信号", "sentiment": "positive"},
            {"id": 2, "title": "行业补贴政策窗口期结束", "sentiment": "negative"},
            {"id": 3, "title": "交易制度优化征求意见", "sentiment": "neutral"},
        ]
        if use_mock
        else [{"id": i + 1, "title": x["title"], "sentiment": x.get("sentiment", "neutral")} for i, x in enumerate(real_items[:50])]
    )
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_news_conn() as conn:
        for idx, item in enumerate(items):
            pub = now
            source = "mock_feed"
            url = ""
            content = ""
            symbol = ""
            if not use_mock:
                detail = real_items[idx]
                pub = detail.get("publish_time") or now
                source = detail.get("source") or "akshare"
                url = detail.get("url") or ""
                content = detail.get("content") or ""
                symbol = detail.get("symbol") or ""
            exists = conn.execute(
                """
                SELECT 1 FROM news_items
                WHERE title=? AND publish_time=?
                LIMIT 1
                """,
                (item["title"], pub),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO news_items(publish_time, title, source, url, content, sentiment, affected_symbols, llm_score, llm_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pub,
                    item["title"],
                    source,
                    url,
                    content,
                    item["sentiment"],
                    symbol,
                    0.65,
                    "自动摘要占位",
                ),
            )
        conn.commit()
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "count": len(items),
        "items": items,
        "source": "mock" if use_mock else "akshare",
    }


def crawl_latest() -> dict:
    return {"status": "ok", "message": "定时新闻抓取完成", "result": crawl_today()}
