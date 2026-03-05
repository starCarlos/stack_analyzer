from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any

import yaml

from hotspot.infrastructure.sqlite_repo import SQLiteRepo
from hotspot.services.market_data_service import MarketDataService


def _stable_score(seed: str) -> float:
    h = hashlib.md5(seed.encode('utf-8')).hexdigest()
    return (int(h[:6], 16) % 1000) / 100.0


class RecommendationService:
    def __init__(self, repo: SQLiteRepo, watchlist_path: Path, market_data: MarketDataService) -> None:
        self.repo = repo
        self.watchlist_path = watchlist_path
        self.market_data = market_data

    def _default_watchlist(self) -> list[dict[str, Any]]:
        return [
            {'symbol': '01810.HK', 'name': '小米集团', 'market': 'hk', 'sector': '消费电子', 'listed': True},
            {'symbol': '300750.SZ', 'name': '宁德时代', 'market': 'cn-a', 'sector': '新能源', 'listed': True},
            {'symbol': '600519.SH', 'name': '贵州茅台', 'market': 'cn-a', 'sector': '消费', 'listed': True},
            {'symbol': '300024.SZ', 'name': '机器人龙头（估）', 'market': 'cn-a', 'sector': '机器人', 'listed': True},
            {'symbol': 'ZHIPU.AI', 'name': '智谱', 'market': 'private', 'sector': '大模型', 'listed': False},
        ]

    def _load_watchlist(self) -> list[dict[str, Any]]:
        if not self.watchlist_path.exists():
            self.watchlist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {'watchlist': self._default_watchlist()}
            self.watchlist_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding='utf-8')
            return payload['watchlist']
        data = yaml.safe_load(self.watchlist_path.read_text(encoding='utf-8')) or {}
        items = data.get('watchlist', [])
        return items if isinstance(items, list) else self._default_watchlist()

    @staticmethod
    def _score_by_quote(change_pct: float) -> float:
        # map roughly [-5, +5] pct to [1, 9] score
        raw = 5.0 + (change_pct * 0.8)
        return max(0.0, min(10.0, raw))

    def generate(self, trade_date: str | None = None) -> list[dict[str, Any]]:
        trade_date = trade_date or datetime.now().strftime('%Y-%m-%d')
        items = self._load_watchlist()
        listed_symbols = [str(x.get('symbol', '')).strip().upper() for x in items if bool(x.get('listed', True))]
        quotes = self.market_data.fetch_quotes(listed_symbols)

        rows: list[dict[str, Any]] = []
        for item in items:
            symbol = str(item.get('symbol', '')).strip().upper()
            if not symbol:
                continue
            listed = bool(item.get('listed', True))
            if not listed:
                rows.append(
                    {
                        'symbol': symbol,
                        'name': item.get('name', symbol),
                        'market': item.get('market', 'private'),
                        'sector': item.get('sector', '其他'),
                        'score': 0.0,
                        'action': 'watch',
                        'reason': '未上市，仅跟踪',
                        'listed': False,
                    }
                )
                continue

            ysym = self.market_data.to_yahoo_symbol(symbol)
            q = quotes.get(ysym)
            if q:
                score = self._score_by_quote(q.change_pct)
                if score >= 7.0:
                    action = 'buy'
                elif score >= 5.0:
                    action = 'hold'
                else:
                    action = 'watch'
                reason = f"实时行情: {q.price:.2f} ({q.change_pct:+.2f}%)"
            else:
                score = _stable_score(f"{trade_date}:{symbol}")
                if score >= 7.0:
                    action = 'buy'
                    reason = '回退规则评分偏积极（实时行情不可用）'
                elif score >= 5.0:
                    action = 'hold'
                    reason = '回退规则评分中性（实时行情不可用）'
                else:
                    action = 'watch'
                    reason = '回退规则评分偏谨慎（实时行情不可用）'

            rows.append(
                {
                    'symbol': symbol,
                    'name': item.get('name', symbol),
                    'market': item.get('market', 'cn-a'),
                    'sector': item.get('sector', '其他'),
                    'score': round(score, 2),
                    'action': action,
                    'reason': reason,
                    'listed': True,
                }
            )
        self.repo.save_recommendations(trade_date, rows)
        return rows
