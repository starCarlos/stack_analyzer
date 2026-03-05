from __future__ import annotations

from datetime import datetime

from hotspot.services.dashboard_service import DashboardService
from hotspot.services.recommendation_service import RecommendationService
from hotspot.services.replay_service import ReplayService


class PipelineRunner:
    def __init__(self, dashboard_svc: DashboardService, rec_svc: RecommendationService, replay_svc: ReplayService) -> None:
        self.dashboard_svc = dashboard_svc
        self.rec_svc = rec_svc
        self.replay_svc = replay_svc

    def run(self, trade_date: str | None = None) -> dict:
        d = trade_date or datetime.now().strftime('%Y-%m-%d')
        steps = []
        self.dashboard_svc.get_dashboard(d)
        steps.append({'step': 'seed_dashboard', 'status': 'ok'})
        recs = self.rec_svc.generate(d)
        steps.append({'step': 'generate_recommendations', 'status': 'ok', 'count': len(recs)})
        replay = self.replay_svc.run_replay(d, [r['symbol'] for r in recs if r.get('listed', True)], sample_size=10)
        steps.append({'step': 'auto_learn_from_replay', 'status': 'ok', 'mae': replay['mae']})
        return {'date': d, 'steps': steps, 'status': 'ok'}
