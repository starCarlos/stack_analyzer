from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core import replayer

router = APIRouter(tags=["replay"])


class ReplayRequest(BaseModel):
    start: str
    end: str
    symbols: list[str] | None = None


@router.post("/replay/run")
def replay_run(payload: ReplayRequest) -> dict:
    return replayer.replay(payload.start, payload.end, payload.symbols)


@router.get("/replay/sessions")
def replay_sessions() -> list[dict]:
    return replayer.get_replay_list()


@router.get("/replay/{session_id}")
def replay_detail(session_id: int) -> dict:
    return {"session_id": session_id, "detail": "占位详情"}
