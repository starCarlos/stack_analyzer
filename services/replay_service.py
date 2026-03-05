from __future__ import annotations

from datetime import datetime
import hashlib

from hotspot.infrastructure.sqlite_repo import SQLiteRepo


class ReplayService:
    def __init__(self, repo: SQLiteRepo) -> None:
        self.repo = repo

    def _predict_return(self, as_of: str, symbol: str) -> float:
        h = int(hashlib.md5(f'pred:{as_of}:{symbol}'.encode('utf-8')).hexdigest()[:8], 16)
        return round(((h % 3000) - 1500) / 10000.0, 4)

    def _actual_return(self, as_of: str, symbol: str) -> float:
        h = int(hashlib.md5(f'act:{as_of}:{symbol}'.encode('utf-8')).hexdigest()[:8], 16)
        return round(((h % 3000) - 1500) / 10000.0, 4)

    def run_replay(self, as_of: str, symbols: list[str], sample_size: int = 20) -> dict:
        picks = [s.upper() for s in symbols if s.strip()][:max(1, sample_size)]
        if not picks:
            picks = ['600519.SH', '300750.SZ', '01810.HK']
        now = datetime.now().isoformat(timespec='seconds')
        rows = []
        for s in picks:
            p = self._predict_return(as_of, s)
            a = self._actual_return(as_of, s)
            rows.append(
                {
                    'as_of': as_of,
                    'symbol': s,
                    'predicted_return': p,
                    'actual_return': a,
                    'abs_error': round(abs(p - a), 4),
                    'created_at': now,
                }
            )
        self.repo.insert_replay_results(rows)
        mae = self.repo.latest_replay_mae(as_of)
        weights = self.repo.latest_weights()
        # simple auto-learning: mae 高则增 risk，低则增 fundamental
        if mae > 0.03:
            weights['risk'] = min(0.7, round(weights.get('risk', 0.3) + 0.05, 2))
            weights['fundamental'] = max(0.1, round(weights.get('fundamental', 0.4) - 0.05, 2))
        else:
            weights['fundamental'] = min(0.7, round(weights.get('fundamental', 0.4) + 0.05, 2))
            weights['risk'] = max(0.1, round(weights.get('risk', 0.3) - 0.05, 2))
        weights['sentiment'] = round(max(0.1, 1.0 - weights['fundamental'] - weights['risk']), 2)
        self.repo.save_weights(as_of, weights)
        return {'as_of': as_of, 'sample_size': len(rows), 'mae': round(mae, 4), 'updated_weights': weights}
