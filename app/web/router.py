from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates

from app.core import advisor_panel, analyzer, candidate_picker, forecaster, learner, paper_trader, replayer
from app.core.data_manager import get_symbol_name_map
from app.crawler.news_crawler import crawl_today
from app.db.ops import (
    get_latest_archive_log,
    get_latest_pipeline_run,
    get_latest_quality_check,
    get_latest_rollback_event,
    get_recent_archive_logs,
    get_recent_quality_checks,
    get_recent_signal_packs,
)
from app.signals.cross_market import build_cross_market_impact, market_thermometer

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


def _quality_points(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        status = r.get("overall_status", "unknown")
        score = 100 if status == "pass" else (60 if status == "warn" else 30)
        out.append({"label": r.get("run_date", "-"), "score": score, "status": status})
    return out


def _capacity_points(rows: list[dict]) -> list[dict]:
    vals = [float(r.get("capacity_mb") or 0) for r in rows]
    m = max(vals) if vals else 1.0
    out = []
    for r in rows:
        v = float(r.get("capacity_mb") or 0)
        out.append({"label": r.get("run_date", "-"), "value": round(v, 2), "pct": round(v / m * 100, 2) if m else 0})
    return out


def _agreement_points(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        v = float(r.get("role_agreement") or 0)
        out.append({"label": r.get("run_date", "-"), "value": round(v, 4), "pct": round(v * 100, 2)})
    return out


def _sparkline_payload(points: list[float], labels: list[str], width: int = 220, height: int = 64) -> dict:
    if not points:
        return {"line": "", "dots": []}
    mn, mx = min(points), max(points)
    span = (mx - mn) if mx != mn else 1.0
    step_x = width / (max(len(points) - 1, 1))
    pairs: list[str] = []
    dots: list[dict] = []
    for i, v in enumerate(points):
        x = round(i * step_x, 2)
        y = round(height - ((v - mn) / span) * height, 2)
        pairs.append(f"{x},{y}")
        dots.append({"x": x, "y": y, "value": v, "label": labels[i] if i < len(labels) else str(i)})
    return {"line": " ".join(pairs), "dots": dots}


@router.get("/")
async def index(request: Request):
    forecast_summary = forecaster.forecast_all()
    buy_pack = candidate_picker.build_buy_candidates()
    cross_market = build_cross_market_impact()
    learning_report = learner.build_daily_report()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "forecast_summary": forecast_summary,
            "forecast_refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "learning_report": learning_report,
            "top_news": crawl_today()["items"],
            "paper_status": paper_trader.get_status(),
            "market_thermometer": market_thermometer(),
            "buy_stock_candidates": buy_pack.get("stocks", []),
            "buy_sector_candidates": buy_pack.get("sectors", []),
            "market_plan": buy_pack.get("market", {}),
            "cross_market_impact": cross_market,
        },
    )


@router.get("/partials/forecast-section")
async def forecast_section_partial(request: Request):
    return templates.TemplateResponse(
        "_forecast_section.html",
        {
            "request": request,
            "forecast_summary": forecaster.forecast_all(),
            "forecast_refreshed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@router.get("/stock/{symbol}")
async def stock_detail(request: Request, symbol: str):
    name = get_symbol_name_map().get(symbol, symbol)
    return templates.TemplateResponse(
        "stock.html",
        {"request": request, "symbol": symbol, "name": name, "analysis": analyzer.analyze_stock(symbol)},
    )


@router.get("/sector/{name}")
async def sector_detail(request: Request, name: str):
    return templates.TemplateResponse("sector.html", {"request": request, "name": name, "analysis": analyzer.analyze_sector(name)})


@router.get("/news")
async def news_center(request: Request):
    return templates.TemplateResponse("news.html", {"request": request, "items": crawl_today()["items"]})


@router.get("/replay")
async def replay_page(request: Request):
    return templates.TemplateResponse("replay.html", {"request": request, "sessions": replayer.get_replay_list()})


@router.get("/forecast-log")
async def forecast_log(request: Request):
    return templates.TemplateResponse("forecast_log.html", {"request": request, "forecasts": forecaster.forecast_all()["stocks"]})


@router.get("/learning")
async def learning_page(request: Request, order: str = Query(default="desc", pattern="^(asc|desc)$")):
    quality_trend = get_recent_quality_checks(7)
    capacity_trend = get_recent_archive_logs(7)
    agreement_trend = get_recent_signal_packs(7)
    if order == "asc":
        quality_trend = list(reversed(quality_trend))
        capacity_trend = list(reversed(capacity_trend))
        agreement_trend = list(reversed(agreement_trend))
    quality_points = _quality_points(quality_trend)
    capacity_points = _capacity_points(capacity_trend)
    agreement_points = _agreement_points(agreement_trend)
    q_spark = _sparkline_payload([p["score"] for p in quality_points], [p["label"] for p in quality_points])
    c_spark = _sparkline_payload([p["value"] for p in capacity_points], [p["label"] for p in capacity_points])
    a_spark = _sparkline_payload([p["value"] for p in agreement_points], [p["label"] for p in agreement_points])
    return templates.TemplateResponse(
        "learning.html",
        {
            "request": request,
            "report": learner.build_daily_report(),
            "latest_run": get_latest_pipeline_run(),
            "latest_quality": get_latest_quality_check(),
            "latest_archive": get_latest_archive_log(),
            "latest_rollback": get_latest_rollback_event(),
            "quality_trend": quality_trend,
            "capacity_trend": capacity_trend,
            "agreement_trend": agreement_trend,
            "quality_points": quality_points,
            "capacity_points": capacity_points,
            "agreement_points": agreement_points,
            "quality_line": q_spark["line"],
            "capacity_line": c_spark["line"],
            "agreement_line": a_spark["line"],
            "quality_dots": q_spark["dots"],
            "capacity_dots": c_spark["dots"],
            "agreement_dots": a_spark["dots"],
            "order": order,
        },
    )


@router.get("/paper")
async def paper_page(request: Request):
    return templates.TemplateResponse("paper.html", {"request": request, "status": paper_trader.get_status()})


@router.get("/advisor/{symbol}")
async def advisor_page(request: Request, symbol: str):
    return templates.TemplateResponse("advisor.html", {"request": request, "result": advisor_panel.analyze(symbol)})


@router.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})
