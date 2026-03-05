from __future__ import annotations

from fastapi import APIRouter, Depends

from hotspot.api.app_state import get_services

router = APIRouter(prefix='/api/v1', tags=['pipeline'])


@router.post('/pipeline/run')
def run_pipeline(date: str | None = None, services=Depends(get_services)) -> dict:
    return services.pipeline.run(date)
