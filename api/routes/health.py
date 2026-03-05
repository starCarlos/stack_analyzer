from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

router = APIRouter(tags=['health'])


@router.get('/health')
def health() -> dict:
    return {'status': 'ok', 'time': datetime.now().isoformat(timespec='seconds')}
