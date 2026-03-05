from __future__ import annotations

from dataclasses import dataclass

from hotspot.services.dashboard_service import DashboardService
from hotspot.services.recommendation_service import RecommendationService
from hotspot.services.replay_service import ReplayService
from hotspot.pipeline.runner import PipelineRunner


@dataclass
class ServiceContainer:
    dashboard: DashboardService
    recommendation: RecommendationService
    replay: ReplayService
    pipeline: PipelineRunner


_services: ServiceContainer | None = None


def set_services(services: ServiceContainer) -> None:
    global _services
    _services = services


def get_services() -> ServiceContainer:
    if _services is None:
        raise RuntimeError('services not initialized')
    return _services
