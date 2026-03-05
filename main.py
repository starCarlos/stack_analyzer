from __future__ import annotations

import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import advisor, analysis, forecast, learning, news, paper, replay, system
from app.db.database import ensure_tables
from app.scheduler.jobs import crawl_news_job, daily_pipeline, history_learning_job
from app.web.router import router as web_router

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_tables()
    scheduler = AsyncIOScheduler()

    hour, minute = os.getenv("PIPELINE_TIME", "18:30").split(":")
    scheduler.add_job(
        daily_pipeline,
        "cron",
        hour=int(hour),
        minute=int(minute),
        day_of_week=os.getenv("PIPELINE_WEEKDAYS", "mon-fri"),
        id="daily_pipeline",
    )
    scheduler.add_job(
        crawl_news_job,
        "interval",
        hours=int(os.getenv("CRAWL_INTERVAL_HOURS", "4")),
        id="crawl_news",
    )

    if os.getenv("ENABLE_AUTO_LEARN", "true").lower() == "true":
        scheduler.add_job(
            history_learning_job,
            "cron",
            day_of_week="sat",
            hour=10,
            id="history_learning",
        )

    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title=os.getenv("APP_TITLE", "A股智能投研系统"), lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(web_router)
app.include_router(forecast.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(replay.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
app.include_router(paper.router, prefix="/api")
app.include_router(advisor.router, prefix="/api")
app.include_router(system.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "1236")),
    )
