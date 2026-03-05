from __future__ import annotations

import os
from datetime import date, timedelta

from app.archive.archiver import archive_daily
from app.checks.quality import run_data_quality_checks, run_signal_quality_checks
from app.core import advisor_panel, alerter, candidate_picker, data_manager, evaluator, forecaster, learner, paper_trader
from app.crawler import news_crawler
from app.db.database import ensure_tables
from app.db.ops import (
    save_archive_log,
    save_pipeline_run,
    save_quality_check,
    save_signal_pack,
)
from app.signals.pack_builder import build_signal_pack


class PipelineCriticalError(RuntimeError):
    pass


def _is_enabled(env_key: str, default: str = "true") -> bool:
    return os.getenv(env_key, default).lower() == "true"


async def daily_pipeline() -> dict:
    ensure_tables()
    log: dict[str, object] = {"date": str(date.today()), "steps": [], "status": "ok"}

    def run_step(name: str, level: str, fn, enabled: bool = True):
        if not enabled:
            log["steps"].append({"name": name, "level": level, "status": "skipped"})
            return None
        try:
            result = fn()
            log["steps"].append({"name": name, "level": level, "status": "ok", "result": result})
            return result
        except Exception as exc:  # noqa: BLE001
            item = {"name": name, "level": level, "status": "failed", "error": str(exc)}
            log["steps"].append(item)
            if level == "critical":
                raise PipelineCriticalError(f"[{name}] critical step failed: {exc}") from exc
            return None

    symbols = data_manager.get_symbols()
    quality_result: dict | None = None
    signal_pack: dict | None = None
    archive_result: dict | None = None
    try:
        # 1 刷新数据
        run_step("refresh_data", "critical", lambda: data_manager.refresh_all(symbols))
        # 2 数据质量检查
        quality_result = run_step("data_quality_check", "warn", run_data_quality_checks)
        # 3 抓取新闻
        news_result = run_step("crawl_news", "warn", news_crawler.crawl_today) or {"items": []}
        # 4 信号包+LLM打分
        candidates_result = candidate_picker.pick()
        signal_pack = run_step(
            "build_signal_pack",
            "critical",
            lambda: build_signal_pack(news_result.get("items", []), candidates_result.get("candidates", [])),
        )
        # 5 信号质量检查
        run_step("signal_quality_check", "warn", lambda: run_signal_quality_checks(signal_pack or {}))
        # 6 预测
        run_step("forecast", "critical", forecaster.forecast_all)
        # 7 评估
        run_step("evaluate_due_forecasts", "critical", evaluator.evaluate_due_forecasts)
        # 8 误差诊断
        run_step("diagnose_forecast_errors", "warn", learner.diagnose_forecast_errors)
        # 9 自动学习调参
        auto_learn_result = run_step(
            "auto_learn",
            "warn",
            learner.learn_from_evaluations,
            enabled=_is_enabled("ENABLE_AUTO_LEARN", "true"),
        )
        # 10 稳健性验证
        validate_result = run_step(
            "walk_forward_validate",
            "warn",
            learner.walk_forward_validate,
            enabled=_is_enabled("ENABLE_AUTO_LEARN", "true"),
        )
        # 10.1 验证失败触发回滚
        if (
            _is_enabled("ENABLE_AUTO_LEARN", "true")
            and isinstance(auto_learn_result, dict)
            and auto_learn_result.get("status") == "ok"
            and auto_learn_result.get("param_changes")
            and isinstance(validate_result, dict)
            and validate_result.get("status") == "ok"
            and (validate_result.get("pass") is False)
        ):
            run_step(
                "rollback_param_changes",
                "warn",
                lambda: learner.rollback_param_changes(
                    auto_learn_result.get("param_changes", []),
                    reason=f"walk_forward_failed:{validate_result.get('note','')}",
                ),
            )
        # 11 候选筛选+定性风控
        enriched_candidates = run_step(
            "candidate_pick_and_risk_annotate",
            "warn",
            lambda: {
                "candidates": candidate_picker.annotate_risk_with_llm(candidates_result.get("candidates", [])),
            },
        ) or {"candidates": []}
        # 12 Advisor多角色分析
        advisor_results = run_step(
            "advisor_multi_role",
            "warn",
            lambda: [advisor_panel.analyze(item["symbol"]) for item in enriched_candidates.get("candidates", [])[:3]],
            enabled=_is_enabled("ENABLE_ADVISOR_PANEL", "true"),
        )
        if signal_pack and advisor_results:
            dirs = [x.get("consensus", {}).get("direction") for x in advisor_results if x.get("consensus")]
            agreements = [x.get("consensus", {}).get("agreement") for x in advisor_results if x.get("consensus")]
            dirs = [d for d in dirs if d]
            agreements = [float(a) for a in agreements if a is not None]
            if dirs and agreements:
                top = max(set(dirs), key=dirs.count)
                signal_pack["consensus"] = {
                    "direction": top,
                    "role_agreement": round(sum(agreements) / len(agreements), 4),
                    "advisor_consensus_count": len(agreements),
                }
        # 13 纸面交易
        run_step(
            "paper_trade_execute",
            "warn",
            lambda: paper_trader.execute_daily(enriched_candidates.get("candidates", []), {}),
            enabled=_is_enabled("ENABLE_PAPER_TRADING", "true"),
        )
        # 14 学习报告
        run_step("build_learning_report", "critical", learner.build_daily_report)
        # 15 告警推送
        run_step("alert_push", "warn", alerter.check_and_push, enabled=_is_enabled("ENABLE_PUSH", "false"))
        # 16 归档治理
        archive_result = run_step("archive_daily", "warn", lambda: archive_daily(str(date.today()), log))
        save_pipeline_run(log)
        if quality_result:
            save_quality_check(str(date.today()), quality_result)
        if signal_pack:
            save_signal_pack(str(date.today()), signal_pack)
        if archive_result:
            save_archive_log(str(date.today()), archive_result)
        return log
    except PipelineCriticalError as exc:
        log["status"] = "failed"
        log["critical_error"] = str(exc)
        save_pipeline_run(log)
        if quality_result:
            save_quality_check(str(date.today()), quality_result)
        if signal_pack:
            save_signal_pack(str(date.today()), signal_pack)
        return log


async def crawl_news_job() -> dict:
    return news_crawler.crawl_latest()


async def history_learning_job() -> dict:
    end_date = date.today().strftime("%Y-%m-%d")
    start_date = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    return learner.learn_from_history(start_date=start_date, end_date=end_date)
