from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from app.utils.paths import config_path, default_db_path


@dataclass(slots=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 7788
    db_path: str = ""
    upstream_timeout_seconds: int = 300
    first_token_timeout_seconds: int = 60
    request_retry_attempts: int = 10
    upstream_proxy_enabled: bool = False
    upstream_proxy_url: str = "http://127.0.0.1:7890"
    local_token: str = ""
    launch_at_login: bool = False

    @property
    def resolved_db_path(self) -> Path:
        """优先使用用户指定路径；为空时落到系统用户数据目录。"""
        return Path(self.db_path).expanduser() if self.db_path else default_db_path()


def load_settings() -> Settings:
    """读取配置文件，并允许 AIMUX_* 环境变量覆盖对应配置。"""
    path = config_path()
    if not path.exists():
        settings = Settings()
        save_settings(settings)
    else:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        allowed = {key: value for key, value in raw.items() if key in Settings.__dataclass_fields__}
        settings = Settings(**allowed)
    overrides: dict[str, tuple[str, type]] = {
        "AIMUX_HOST": ("host", str),
        "AIMUX_PORT": ("port", int),
        "AIMUX_DB_PATH": ("db_path", str),
        "AIMUX_UPSTREAM_TIMEOUT_SECONDS": ("upstream_timeout_seconds", int),
        "AIMUX_FIRST_TOKEN_TIMEOUT_SECONDS": ("first_token_timeout_seconds", int),
        "AIMUX_REQUEST_RETRY_ATTEMPTS": ("request_retry_attempts", int),
        "AIMUX_UPSTREAM_PROXY_ENABLED": ("upstream_proxy_enabled", bool),
        "AIMUX_UPSTREAM_PROXY_URL": ("upstream_proxy_url", str),
        "AIMUX_LOCAL_TOKEN": ("local_token", str),
        "AIMUX_LAUNCH_AT_LOGIN": ("launch_at_login", bool),
    }
    for variable, (field, converter) in overrides.items():
        value = os.environ.get(variable)
        if value is None:
            continue
        if converter is bool:
            setattr(settings, field, value.strip().lower() in {"1", "true", "yes", "on"})
        else:
            setattr(settings, field, converter(value))
    settings.request_retry_attempts = max(1, min(20, settings.request_retry_attempts))
    return settings


def save_settings(settings: Settings) -> None:
    """将当前设置以 UTF-8 JSON 写入用户数据目录。"""
    config_path().write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8"
    )
