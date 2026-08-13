from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def project_version() -> str:
    """读取项目发布版本；源码和 PyInstaller 运行时均使用同一份元数据。"""
    bundle_root = getattr(sys, "_MEIPASS", None)
    metadata = (Path(bundle_root) if bundle_root else Path(__file__).resolve().parents[2]) / "pyproject.toml"
    try:
        return str(tomllib.loads(metadata.read_text(encoding="utf-8"))["project"]["version"])
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        return "0.0.0"
