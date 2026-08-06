"""Build a native desktop package with PyInstaller."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).parents[1]
assets = root / "assets"
icon = assets / "icons" / ("aimux.ico" if sys.platform == "win32" else "aimux.icns")

subprocess.run([sys.executable, str(root / "scripts" / "generate_icon.py")], check=True)
subprocess.run(
    [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onedir",
        "--name", "AIMux", "--paths", str(root), "--icon", str(icon),
        "--add-data", f"{assets}{os.pathsep}assets", str(root / "app" / "__main__.py"),
    ],
    check=True,
)
