from __future__ import annotations

from fastapi import APIRouter

from app.core import analyzer

router = APIRouter(tags=["analysis"])


@router.get("/analysis/stock/{symbol}")
def analysis_stock(symbol: str) -> dict:
    return analyzer.analyze_stock(symbol)


@router.get("/analysis/sector/{name}")
def analysis_sector(name: str) -> dict:
    return analyzer.analyze_sector(name)


@router.get("/analysis/market")
def analysis_market() -> dict:
    return analyzer.analyze_market()
