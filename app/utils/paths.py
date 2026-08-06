from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "aimux"


def data_dir() -> Path:
    """动态取得 AIMux 可写用户数据目录，测试可通过环境变量覆盖。"""
    override = os.environ.get("AIMUX_DATA_DIR")
    # `roaming=True` maps Windows to %APPDATA% and avoids platformdirs' author subdirectory.
    directory = Path(override) if override else Path(user_data_dir(APP_NAME, appauthor=False, roaming=True))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def default_db_path() -> Path:
    """返回默认 SQLite 文件路径。"""
    return data_dir() / "data.sqlite3"


def config_path() -> Path:
    """返回用户配置文件路径。"""
    return data_dir() / "config.json"
