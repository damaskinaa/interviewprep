import os
from pathlib import Path


def data_path(name: str) -> Path:
    base = os.getenv("DATA_DIR", "")
    return Path(base).expanduser() / name if base else Path(name)


def lua_data_path(name: str) -> Path:
    base = os.getenv("LUA_DB_BASE_DIR", "") or os.getenv("DATA_DIR", "")
    return Path(base).expanduser() / name if base else Path(name)
