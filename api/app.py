from __future__ import annotations

from fastapi import FastAPI

from hotspot.api.app_state import ServiceContainer, set_services
from hotspot.api.routes import health, dashboard, pipeline, learning
from hotspot.core.config import load_settings
from hotspot.infrastructure.sqlite_repo import SQLiteRepo
from hotspot.pipeline.runner import PipelineRunner
from hotspot.services.dashboard_service import DashboardService
from hotspot.services.market_data_service import MarketDataService
from hotspot.services.recommendation_service import RecommendationService
from hotspot.services.replay_service import ReplayService


def create_app() -> FastAPI:
    settings = load_settings()
    repo = SQLiteRepo(str(settings.db_path))
    market_data_svc = MarketDataService()
    dashboard_svc = DashboardService(repo, market_data_svc)
    recommendation_svc = RecommendationService(repo, settings.watchlist_path, market_data_svc)
    replay_svc = ReplayService(repo)
    pipeline_runner = PipelineRunner(dashboard_svc, recommendation_svc, replay_svc)
    set_services(
        ServiceContainer(
            dashboard=dashboard_svc,
            recommendation=recommendation_svc,
            replay=replay_svc,
            pipeline=pipeline_runner,
        )
    )

    app = FastAPI(title='HotSpot Stock Analyzer API', version='2.0.0')
    app.include_router(health.router)
    app.include_router(dashboard.router)
    app.include_router(pipeline.router)
    app.include_router(learning.router)
    return app


app = create_app()
