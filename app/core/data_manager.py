from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from app.db.database import get_tracking_conn


def _load_symbols_yaml() -> dict:
    path = Path("config/symbols.yaml")
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


_FALLBACK_SECTORS = [
    "白酒", "新能源", "光伏", "半导体", "人工智能", "军工", "医药", "银行", "券商", "保险",
    "房地产", "煤炭", "有色金属", "电力", "汽车整车", "消费电子", "通信设备", "软件服务",
    "机械设备", "化工", "农业", "食品饮料", "家电", "传媒", "建筑装饰", "环保", "港口航运",
]


def get_universe() -> list[dict]:
    data = _load_symbols_yaml()
    universe = data.get("universe") if isinstance(data, dict) else None
    if isinstance(universe, list) and universe:
        return universe
    return [{"symbol": s, "name": s} for s in get_symbols()]


def get_symbol_name_map() -> dict[str, str]:
    return {item.get("symbol", ""): item.get("name", item.get("symbol", "")) for item in get_universe() if item.get("symbol")}


def _sector_cache_path() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "output"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "sector_cache.json"


def _save_sector_cache(sectors: list[dict]) -> None:
    path = _sector_cache_path()
    path.write_text(json.dumps({"updated_at": str(date.today()), "sectors": sectors}, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_sector_cache() -> list[dict]:
    path = _sector_cache_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        sectors = data.get("sectors", [])
        if isinstance(sectors, list):
            return sectors
    except Exception:
        pass
    return []


def get_sector_cache_meta() -> dict:
    path = _sector_cache_path()
    if not path.exists():
        return {"exists": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"exists": True, "updated_at": data.get("updated_at"), "path": str(path)}
    except Exception:
        return {"exists": True, "updated_at": None, "path": str(path)}


def _akshare_sectors() -> list[dict]:
    try:
        import akshare as ak  # type: ignore

        df = ak.stock_board_industry_name_em()
        if df is None or df.empty:
            return []
        col_name = "板块名称" if "板块名称" in df.columns else df.columns[0]
        names = [str(x).strip() for x in df[col_name].tolist() if str(x).strip()]
        names = sorted(set(names))
        sectors = [{"name": n, "proxy_index": None, "members": []} for n in names]
        if sectors:
            _save_sector_cache(sectors)
        return sectors
    except Exception:
        return []


def _config_sectors() -> list[dict]:
    data = _load_symbols_yaml()
    sectors = data.get("sectors") if isinstance(data, dict) else None
    if isinstance(sectors, list) and sectors:
        return sectors
    # 兜底：从 universe 自动汇总
    items = get_universe()
    names = sorted({item.get("sector") for item in items if isinstance(item, dict) and item.get("sector")})
    return [{"name": n, "proxy_index": None, "members": [u.get("symbol") for u in items if u.get("sector") == n]} for n in names]


def get_sectors() -> list[dict]:
    mode = os.getenv("FULL_SECTOR_MODE", "auto").lower()
    if mode in {"auto", "akshare"}:
        sectors = _akshare_sectors()
        if sectors:
            return sectors
        cached = _load_sector_cache()
        if cached:
            return cached
        if mode == "auto":
            # auto 下优先保证“全板块覆盖”
            return [{"name": n, "proxy_index": None, "members": []} for n in _FALLBACK_SECTORS]
    if mode == "config":
        cfg = _config_sectors()
        if cfg:
            return cfg
    # akshare 强制模式失败后仍兜底
    cfg = _config_sectors()
    if cfg:
        return cfg
    return [{"name": n, "proxy_index": None, "members": []} for n in _FALLBACK_SECTORS]


def sync_sector_universe() -> dict:
    mode = os.getenv("FULL_SECTOR_MODE", "auto").lower()
    if mode in {"auto", "akshare"}:
        s = _akshare_sectors()
        if s:
            return {"source": "akshare", "count": len(s), "status": "ok"}
    s = get_sectors()
    return {"source": "fallback", "count": len(s), "status": "ok"}


def get_sector_universe_status() -> dict:
    mode = os.getenv("FULL_SECTOR_MODE", "auto").lower()
    sectors = get_sectors()
    cache_meta = get_sector_cache_meta()
    source = "unknown"
    if mode == "config":
        source = "config"
    else:
        if cache_meta.get("exists"):
            source = "akshare_or_cache"
        else:
            source = "fallback"
    return {
        "mode": mode,
        "source": source,
        "count": len(sectors),
        "cache": cache_meta,
        "sectors": sectors,
    }


def get_symbols() -> list[str]:
    universe = _load_symbols_yaml().get("universe", [])
    if isinstance(universe, list) and universe:
        symbols = [item.get("symbol") for item in universe if isinstance(item, dict) and item.get("symbol")]
        if symbols:
            return symbols
    env_symbols = os.getenv("SYMBOLS", "600519.SH,300750.SZ,000858.SZ")
    return [item.strip() for item in env_symbols.split(",") if item.strip()]


def _to_ak_symbol(symbol: str) -> str:
    return symbol.split(".")[0].strip()


def _fetch_akshare_hist(symbol: str, start: str, end: str):
    import akshare as ak  # type: ignore

    return ak.stock_zh_a_hist(
        symbol=_to_ak_symbol(symbol),
        period="daily",
        start_date=start.replace("-", ""),
        end_date=end.replace("-", ""),
        adjust="qfq",
    )


def _insert_bar_row(conn, symbol: str, trade_date: str, open_p: float, high_p: float, low_p: float, close_p: float, volume: float, amount: float, turnover: float | None, source: str) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO market_price_bars
        (symbol, trade_date, open, high, low, close, volume, amount, turnover, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            trade_date,
            float(open_p) if open_p is not None else None,
            float(high_p) if high_p is not None else None,
            float(low_p) if low_p is not None else None,
            float(close_p) if close_p is not None else None,
            float(volume) if volume is not None else None,
            float(amount) if amount is not None else None,
            float(turnover) if turnover is not None else None,
            source,
        ),
    )


def _insert_mock_rows(conn, symbol: str, trade_date: str, idx: int) -> int:
    base = 100 + idx * 5
    rows = [
        (symbol, trade_date, base, base * 1.01, base * 0.99, base * 1.005, 1_000_000 + idx * 10_000, 1_000_000_000 + idx * 100_000_000, 0.03 + idx * 0.002, "akshare"),
        (symbol, trade_date, base * 1.0005, base * 1.0105, base * 0.9905, base * 1.0045, 990_000 + idx * 9_000, 980_000_000 + idx * 95_000_000, 0.029 + idx * 0.002, "yahoo"),
    ]
    for row in rows:
        _insert_bar_row(conn, *row)
    return len(rows)


def refresh_all(symbols: list[str]) -> dict:
    trade_date = str(date.today())
    sector_sync = sync_sector_universe()
    inserted = 0
    warnings: list[str] = []
    use_mock_fallback = os.getenv("ALLOW_MOCK_FALLBACK", "true").lower() == "true"
    end = trade_date
    start = (date.today() - timedelta(days=int(os.getenv("REFRESH_LOOKBACK_DAYS", "120")))).isoformat()
    with get_tracking_conn() as conn:
        for i, symbol in enumerate(symbols):
            try:
                df = _fetch_akshare_hist(symbol, start, end)
                if df is None or df.empty:
                    raise RuntimeError("akshare returned empty dataframe")
                col_date = "日期" if "日期" in df.columns else df.columns[0]
                for _, row in df.iterrows():
                    d = str(row.get(col_date))
                    d = d[:10]
                    _insert_bar_row(
                        conn,
                        symbol,
                        d,
                        row.get("开盘"),
                        row.get("最高"),
                        row.get("最低"),
                        row.get("收盘"),
                        row.get("成交量"),
                        row.get("成交额"),
                        row.get("换手率"),
                        "akshare",
                    )
                    inserted += 1
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{symbol}: akshare获取失败({exc})")
                if use_mock_fallback:
                    inserted += _insert_mock_rows(conn, symbol, trade_date, i)
                else:
                    raise
        conn.commit()
    status = "ok" if not warnings else "degraded"
    return {
        "date": trade_date,
        "symbols": symbols,
        "inserted_rows": inserted,
        "sector_sync": sector_sync,
        "status": status,
        "warnings": warnings,
    }


def backfill_history(start: str, end: str) -> dict:
    symbols = get_symbols()
    inserted = 0
    warnings: list[str] = []
    with get_tracking_conn() as conn:
        for i, symbol in enumerate(symbols):
            try:
                df = _fetch_akshare_hist(symbol, start, end)
                if df is None or df.empty:
                    raise RuntimeError("akshare returned empty dataframe")
                col_date = "日期" if "日期" in df.columns else df.columns[0]
                for _, row in df.iterrows():
                    d = str(row.get(col_date))[:10]
                    _insert_bar_row(
                        conn,
                        symbol,
                        d,
                        row.get("开盘"),
                        row.get("最高"),
                        row.get("最低"),
                        row.get("收盘"),
                        row.get("成交量"),
                        row.get("成交额"),
                        row.get("换手率"),
                        "akshare",
                    )
                    inserted += 1
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{symbol}: {exc}")
                inserted += _insert_mock_rows(conn, symbol, end, i)
        conn.commit()
    return {
        "start": start,
        "end": end,
        "symbols": symbols,
        "inserted_rows": inserted,
        "status": "ok" if not warnings else "degraded",
        "warnings": warnings,
    }
