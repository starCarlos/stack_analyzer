from __future__ import annotations

from fastapi import APIRouter

from app.core import advisor_panel

router = APIRouter(tags=["advisor"])


@router.get("/advisor/{symbol}")
def advisor_latest(symbol: str) -> dict:
    return advisor_panel.analyze(symbol)


@router.post("/advisor/{symbol}/refresh")
def advisor_refresh(symbol: str) -> dict:
    return advisor_panel.analyze(symbol)
