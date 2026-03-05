from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    db_path: Path
    watchlist_path: Path



def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parent.parent.parent
    data_dir = Path(os.environ.get('HOTSPOT_DATA_DIR', project_root / 'output'))
    db_path = Path(os.environ.get('HOTSPOT_DB_PATH', data_dir / 'runtime' / 'hotspot.db'))
    watchlist_path = Path(os.environ.get('HOTSPOT_WATCHLIST', project_root / 'config' / 'watchlist.yaml'))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        db_path=db_path,
        watchlist_path=watchlist_path,
    )
