"""Build a native desktop package with PyInstaller."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

root = Path(__file__).parents[1]

subprocess.run(
    [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onedir",
        "--name", "AIMux", "--paths", str(root), str(root / "app" / "__main__.py"),
    ],
    check=True,
)
