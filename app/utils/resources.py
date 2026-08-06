from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """返回源码运行或 PyInstaller 打包运行时均有效的内置资源路径。"""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).joinpath(*parts)
    return Path(__file__).resolve().parents[2].joinpath(*parts)
