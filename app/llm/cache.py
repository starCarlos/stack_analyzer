from __future__ import annotations

_CACHE: dict[str, dict] = {}


def get(key: str) -> dict | None:
    return _CACHE.get(key)


def set_(key: str, value: dict) -> None:
    _CACHE[key] = value
