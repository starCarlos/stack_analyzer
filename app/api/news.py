from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.crawler.news_crawler import crawl_today

router = APIRouter(tags=["news"])


@router.get("/news/today")
def news_today() -> dict:
    return crawl_today()


@router.get("/news/{news_id}")
def news_detail(news_id: int) -> dict:
    return {"id": news_id, "title": "示例新闻", "detail": "这里是新闻详情占位内容"}


@router.get("/news/{news_id}/detail", response_class=HTMLResponse)
def news_detail_htmx(news_id: int) -> str:
    return f"<div class='mt-2 text-sm text-gray-300'>LLM分析摘要（ID={news_id}）：该事件短期偏中性，建议结合资金面确认。</div>"


@router.get("/news/by-symbol/{symbol}")
def news_by_symbol(symbol: str) -> dict:
    return {"symbol": symbol, "items": crawl_today()["items"]}
