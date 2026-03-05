from __future__ import annotations

import argparse
import asyncio

from app.core import data_manager, replayer
from app.db.database import ensure_tables
from app.scheduler.jobs import daily_pipeline


def cmd_init() -> None:
    ensure_tables()
    data_manager.refresh_all(data_manager.get_symbols())
    print("初始化完成")


def cmd_backfill(start: str, end: str) -> None:
    data_manager.backfill_history(start, end)
    print(f"回填完成: {start} -> {end}")


def cmd_pipeline() -> None:
    asyncio.run(daily_pipeline())
    print("流水线执行完成")


def cmd_replay(start: str, end: str, symbols: str | None) -> None:
    symbol_list = [item.strip() for item in symbols.split(",")] if symbols else None
    result = replayer.replay(start, end, symbol_list)
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="A股投研系统 CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="初始化数据库和数据")

    bf = sub.add_parser("backfill", help="回填历史数据")
    bf.add_argument("--start", required=True)
    bf.add_argument("--end", required=True)

    sub.add_parser("pipeline", help="手动触发流水线")

    rp = sub.add_parser("replay", help="历史回放")
    rp.add_argument("--start", required=True)
    rp.add_argument("--end", required=True)
    rp.add_argument("--symbols", default=None)

    args = parser.parse_args()
    if args.command == "init":
        cmd_init()
    elif args.command == "backfill":
        cmd_backfill(args.start, args.end)
    elif args.command == "pipeline":
        cmd_pipeline()
    elif args.command == "replay":
        cmd_replay(args.start, args.end, args.symbols)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
