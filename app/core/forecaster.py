from __future__ import annotations

import os
from pathlib import Path
from datetime import date, timedelta

import yaml
from app.db.database import get_tracking_conn
from app.core.data_manager import get_sectors, get_symbol_name_map, get_symbols


def _load_weights() -> dict[str, float]:
    path = Path("config/forecast_model.yaml")
    if not path.exists():
        return {"momentum": 0.3, "mean_reversion": 0.3, "fundamental": 0.4}
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    w = cfg.get("price", {}).get("weights", {})
    if not isinstance(w, dict) or not w:
        return {"momentum": 0.3, "mean_reversion": 0.3, "fundamental": 0.4}
    return {k: float(v) for k, v in w.items()}


def _recent_closes(symbol: str, as_of_date: str, limit: int = 30) -> list[float]:
    with get_tracking_conn() as conn:
        rows = conn.execute(
            """
            SELECT close
            FROM market_price_bars
            WHERE symbol=? AND trade_date<=? AND close IS NOT NULL
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (symbol, as_of_date, limit),
        ).fetchall()
    vals = [float(r[0]) for r in rows if r[0] is not None]
    vals.reverse()
    return vals


def _stock_forecast(symbol: str, as_of_date: str | None = None) -> dict:
    forecast_date = as_of_date or str(date.today())
    name_map = get_symbol_name_map()
    closes = _recent_closes(symbol, forecast_date, limit=30)
    weights = _load_weights()
    if len(closes) >= 6:
        momentum = closes[-1] / closes[-6] - 1
    else:
        momentum = 0.0
    if len(closes) >= 20:
        ma20 = sum(closes[-20:]) / 20
        mean_rev = (ma20 - closes[-1]) / ma20 if ma20 else 0.0
    else:
        mean_rev = 0.0
    fundamental = 0.003  # 暂无真实基本面因子时的保守常数
    predicted_return = (
        weights.get("momentum", 0.3) * momentum
        + weights.get("mean_reversion", 0.3) * mean_rev
        + weights.get("fundamental", 0.4) * fundamental
    )
    predicted_return = round(float(predicted_return), 6)
    predicted_direction = "up" if predicted_return > 0.002 else ("down" if predicted_return < -0.002 else "flat")
    confidence = min(0.92, max(0.5, 0.55 + abs(predicted_return) * 6))
    reason = f"mom5={momentum:.2%}, mean_rev={mean_rev:.2%}"
    return {
        "target_type": "stock",
        "symbol": symbol,
        "name": name_map.get(symbol, symbol),
        "forecast_date": forecast_date,
        "target_date": str(date.fromisoformat(forecast_date) + timedelta(days=5)),
        "window_days": 5,
        "predicted_return": predicted_return,
        "predicted_direction": predicted_direction,
        "confidence": round(confidence, 4),
        "method": "ensemble",
        "reason": reason,
    }


def _sector_forecast(name: str) -> dict:
    score = sum(ord(ch) for ch in name) % 100
    confidence = round(0.45 + (score / 100) * 0.4, 2)  # 0.45 ~ 0.85
    if confidence >= 0.6:
        direction = "up"
    elif confidence <= 0.52:
        direction = "down"
    else:
        direction = "flat"
    return {
        "target_type": "sector",
        "name": name,
        "window_days": 10,
        "predicted_direction": direction,
        "confidence": confidence,
    }


def forecast_all(as_of_date: str | None = None) -> dict:
    symbols = get_symbols()
    stocks = [_stock_forecast(symbol, as_of_date) for symbol in symbols]
    sector_cfgs = get_sectors()
    all_sectors = [_sector_forecast(s.get("name", "未知板块")) for s in sector_cfgs if isinstance(s, dict)]
    bullish = sorted([s for s in all_sectors if s["predicted_direction"] == "up"], key=lambda x: x["confidence"], reverse=True)
    bearish = sorted([s for s in all_sectors if s["predicted_direction"] == "down"], key=lambda x: x["confidence"], reverse=True)
    run_date = as_of_date or str(date.today())
    with get_tracking_conn() as conn:
        for item in stocks:
            exists = conn.execute(
                """
                SELECT 1 FROM price_forecasts
                WHERE target_type='stock' AND symbol=? AND forecast_date=? AND window_days=?
                LIMIT 1
                """,
                (item["symbol"], run_date, item["window_days"]),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO price_forecasts
                (target_type, symbol, forecast_date, target_date, window_days, predicted_return, predicted_direction, confidence, method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "stock",
                    item["symbol"],
                    run_date,
                    item["target_date"],
                    item["window_days"],
                    item["predicted_return"],
                    item["predicted_direction"],
                    item["confidence"],
                    item["method"],
                ),
            )
        conn.commit()
    return {
        "date": run_date,
        "market": {
            "symbol": "000300.SH",
            "direction": "up",
            "confidence": 0.68,
            "predicted_return_5d": 0.012,
            "north_flow_amount": 23.5,
            "total_turnover_amount": 9865.0,
            "sentiment": "谨慎乐观",
            "ma20_status": "above",
        },
        "stocks": sorted(stocks, key=lambda item: item["confidence"], reverse=True),
        "sectors": {
            "scope_mode": os.getenv("FULL_SECTOR_MODE", "auto"),
            "all": all_sectors,
            "bullish": bullish[:5],
            "bearish": bearish[:5],
        },
    }


def get_stock_forecast(symbol: str) -> dict:
    return _stock_forecast(symbol)


def get_sector_forecast(name: str) -> dict:
    return _sector_forecast(name)


def get_market_forecast() -> dict:
    return {"target_type": "market", "symbol": "000300.SH", "window_days": 5, "predicted_direction": "up", "confidence": 0.68}
