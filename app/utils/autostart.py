from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

APP_ID = "aimux"
WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m app'


def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"


def is_enabled() -> bool:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
                winreg.QueryValueEx(key, APP_ID)
                return True
        except FileNotFoundError:
            return False
    if sys.platform == "darwin":
        return _mac_plist_path().exists()
    return (Path.home() / ".config" / "autostart" / f"{APP_ID}.desktop").exists()


def set_enabled(enabled: bool) -> None:
    if sys.platform == "win32":
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, APP_ID)
                except FileNotFoundError:
                    pass
        return
    if sys.platform == "darwin":
        path = _mac_plist_path()
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            arguments = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "app"]
            path.write_bytes(plistlib.dumps({"Label": APP_ID, "ProgramArguments": arguments, "RunAtLoad": True}))
        elif path.exists():
            path.unlink()
        return
    path = Path.home() / ".config" / "autostart" / f"{APP_ID}.desktop"
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"[Desktop Entry]\nType=Application\nName=AIMux\nExec={_command()}\n", encoding="utf-8")
    elif path.exists():
        path.unlink()
