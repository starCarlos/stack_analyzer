from __future__ import annotations

from fastapi import APIRouter

from app.core import forecaster

router = APIRouter(tags=["forecast"])


@router.get("/forecast/today")
def forecast_today() -> dict:
    return forecaster.forecast_all()


@router.get("/forecast/stock/{symbol}")
def forecast_stock(symbol: str) -> dict:
    return forecaster.get_stock_forecast(symbol)


@router.get("/forecast/sector/{name}")
def forecast_sector(name: str) -> dict:
    return forecaster.get_sector_forecast(name)


@router.get("/forecast/market")
def forecast_market() -> dict:
    return forecaster.get_market_forecast()


@router.post("/forecast/refresh")
def refresh_forecast() -> dict:
    return forecaster.forecast_all()


@router.get("/forecast/refresh")
def refresh_forecast_get() -> dict:
    return forecaster.forecast_all()
