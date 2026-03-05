from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from hotspot.api.app_state import get_services
from hotspot.domain.models import ReplayRequest

router = APIRouter(prefix='/api/v1', tags=['learning'])


@router.post('/learning/replay')
def replay(payload: ReplayRequest, services=Depends(get_services)) -> dict:
    as_of = payload.as_of or datetime.now().strftime('%Y-%m-%d')
    return services.replay.run_replay(as_of, payload.symbols, payload.sample_size)
