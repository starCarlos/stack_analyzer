from __future__ import annotations

from datetime import date

from app.core.data_manager import get_symbols
from app.db.database import get_news_conn, get_tracking_conn


def _sqlite_health() -> dict:
    try:
        with get_tracking_conn() as conn:
            r1 = conn.execute("PRAGMA quick_check").fetchone()
        with get_news_conn() as conn:
            r2 = conn.execute("PRAGMA quick_check").fetchone()
        ok = (r1 and r1[0] == "ok") and (r2 and r2[0] == "ok")
        return {"status": "pass" if ok else "warn", "detail": f"tracking={r1[0] if r1 else 'n/a'}, news={r2[0] if r2 else 'n/a'}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "warn", "detail": f"quick_check 异常: {exc}"}


def _data_health() -> dict:
    today = str(date.today())
    with get_tracking_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM market_price_bars WHERE trade_date=?", (today,)).fetchone()[0]
        valid_close = conn.execute(
            "SELECT COUNT(*) FROM market_price_bars WHERE trade_date=? AND close IS NOT NULL",
            (today,),
        ).fetchone()[0]
    completeness = round(valid_close / total, 4) if total else 0.0
    status = "pass" if completeness >= 0.95 else "warn"
    return {"status": status, "detail": f"今日行情条数={total}, close完整率={completeness:.2%}"}


def _source_consistency() -> dict:
    today = str(date.today())
    with get_tracking_conn() as conn:
        rows = conn.execute(
            """
            SELECT a.symbol, a.close close_a, y.close close_y
            FROM market_price_bars a
            JOIN market_price_bars y
              ON a.symbol = y.symbol AND a.trade_date = y.trade_date
            WHERE a.trade_date=? AND a.source='akshare' AND y.source='yahoo'
            """,
            (today,),
        ).fetchall()
    if not rows:
        return {"status": "warn", "detail": "缺少主备源同日同标的可比数据"}
    diffs = []
    for r in rows:
        close_a, close_y = float(r[1] or 0), float(r[2] or 0)
        if close_a <= 0 or close_y <= 0:
            continue
        diffs.append(abs(close_a - close_y) / close_a)
    if not diffs:
        return {"status": "warn", "detail": "价格字段不足，无法比对"}
    avg_diff = sum(diffs) / len(diffs)
    return {"status": "pass" if avg_diff <= 0.02 else "warn", "detail": f"akshare/yahoo 收盘价平均偏差={avg_diff:.2%}"}


def _sector_coverage() -> dict:
    today = str(date.today())
    symbols = get_symbols()
    with get_tracking_conn() as conn:
        rows = conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM market_price_bars WHERE trade_date=?",
            (today,),
        ).fetchone()[0]
    cov = round(rows / len(symbols), 4) if symbols else 1.0
    return {"status": "pass" if cov >= 0.9 else "warn", "detail": f"标的覆盖率={cov:.2%} ({rows}/{len(symbols)})"}


def run_data_quality_checks() -> dict:
    """5类数据质量检查（基于真实库状态）。"""
    with get_news_conn() as conn:
        news_count = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
    checks = {
        "sqlite_health": _sqlite_health(),
        "signal_quality": {"status": "pass" if news_count > 0 else "warn", "detail": f"news_items={news_count}"},
        "data_health": _data_health(),
        "source_consistency": _source_consistency(),
        "sector_coverage": _sector_coverage(),
    }
    warn_count = sum(1 for v in checks.values() if v["status"] == "warn")
    return {
        "date": str(date.today()),
        "checks": checks,
        "overall": "warn" if warn_count else "pass",
        "warn_count": warn_count,
    }


def run_signal_quality_checks(signal_pack: dict) -> dict:
    summary = signal_pack.get("summary", "")
    advisors = signal_pack.get("advisor_table", [])
    issues: list[str] = []
    if not summary:
        issues.append("summary 为空")
    if not advisors:
        issues.append("advisor_table 为空")
    return {
        "status": "pass" if not issues else "warn",
        "issue_count": len(issues),
        "issues": issues,
    }
