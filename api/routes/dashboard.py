from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from hotspot.api.app_state import get_services

router = APIRouter(prefix='/api/v1', tags=['dashboard'])


@router.get('/dashboard')
def dashboard(date: str | None = Query(default=None), services=Depends(get_services)) -> dict:
    return services.dashboard.get_dashboard(date)


@router.get('/recommended-buy')
def recommended_buy(date: str | None = Query(default=None), services=Depends(get_services)) -> dict:
    d = services.dashboard.get_dashboard(date)
    return {'date': d['date'], 'recommended_buy': d['recommended_buy']}


@router.get('/recommendations')
def recommendations(date: str | None = Query(default=None), services=Depends(get_services)) -> dict:
    return recommended_buy(date, services)
