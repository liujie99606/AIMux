"""Build a native desktop package with PyInstaller."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[1]
ASSETS = ROOT / "assets"
ICON_DIR = ASSETS / "icons"
REQUIRED_ICONS = tuple(ICON_DIR / name for name in ("aimux.png", "aimux.ico", "aimux.icns"))
OUTPUT_EXECUTABLE = ROOT / "dist" / "AIMux" / "AIMux.exe"


def _log(message: str) -> None:
    """输出带本地时间的打包阶段日志。"""
    print(f"[{time.strftime('%H:%M:%S')}] [AIMux] {message}", flush=True)


def _parse_args() -> argparse.Namespace:
    """读取打包选项；默认保留 PyInstaller 增量缓存。"""
    parser = argparse.ArgumentParser(description="构建 AIMux 桌面应用")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="清理 PyInstaller 缓存后执行一次完整构建",
    )
    return parser.parse_args()


def _windows_output_is_running(executable: Path) -> bool:
    """判断指定打包产物是否正在 Windows 中运行。"""
    if sys.platform != "win32" or not executable.exists():
        return False
    escaped_path = str(executable.resolve()).replace("'", "''")
    command = (
        "$process = Get-CimInstance Win32_Process -Filter \"Name = 'AIMux.exe'\" "
        f"| Where-Object {{ $_.ExecutablePath -eq '{escaped_path}' }}; "
        "if ($process) { exit 0 } else { exit 1 }"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _ensure_icons() -> None:
    """仅在任一平台图标缺失时重新生成整套图标。"""
    missing = [path.name for path in REQUIRED_ICONS if not path.is_file()]
    if not missing:
        _log("阶段 1/4：图标已存在，跳过生成")
        return
    _log(f"阶段 1/4：缺少 {', '.join(missing)}，正在生成应用图标")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_icon.py")], check=True)


def _phase_for_line(line: str) -> str | None:
    """将 PyInstaller 内部日志映射为用户可理解的构建阶段。"""
    if "Building Analysis" in line or " Analyzing " in line:
        return "阶段 2/4：正在分析 Python、PySide6 和项目依赖"
    if "Building PYZ" in line or "Building PKG" in line:
        return "阶段 3/4：正在生成 Python 归档"
    if "Building EXE" in line:
        return "阶段 3/4：正在生成 AIMux 可执行文件"
    if "Building COLLECT" in line or "Removing dir" in line:
        return "阶段 4/4：正在复制运行库和资源到输出目录"
    return None


def _pyinstaller_command(clean: bool) -> list[str]:
    """构造默认复用缓存、按需全量清理的 PyInstaller 命令。"""
    icon = ICON_DIR / ("aimux.ico" if sys.platform == "win32" else "aimux.icns")
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--onedir",
        "--name",
        "AIMux",
        "--paths",
        str(ROOT),
        "--icon",
        str(icon),
        "--add-data",
        f"{ASSETS}{os.pathsep}assets",
    ]
    if clean:
        command.append("--clean")
    command.append(str(ROOT / "app" / "__main__.py"))
    return command


def _run_pyinstaller(clean: bool) -> None:
    """运行 PyInstaller，实时输出内部日志和中文阶段提示。"""
    command = _pyinstaller_command(clean)
    cache_message = "已请求全量清理" if clean else "保留增量缓存"
    _log(f"阶段 2/4：启动 PyInstaller（{cache_message}）")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    current_phase: str | None = None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        phase = _phase_for_line(line)
        if phase is not None and phase != current_phase:
            _log(phase)
            current_phase = phase
        print(f"[{time.strftime('%H:%M:%S')}] [PyInstaller] {line}", flush=True)
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)


def main() -> None:
    """检查运行状态、准备图标并执行可增量复用的桌面打包。"""
    args = _parse_args()
    _log("开始检查打包环境")
    if _windows_output_is_running(OUTPUT_EXECUTABLE):
        _log(
            "打包已停止：dist\\AIMux\\AIMux.exe 正在运行；"
            "请从系统托盘退出 AIMux 后重新打包"
        )
        raise SystemExit(1)
    _ensure_icons()
    started = time.perf_counter()
    _run_pyinstaller(args.clean)
    elapsed = time.perf_counter() - started
    output_name = "AIMux.exe" if sys.platform == "win32" else "AIMux"
    output = ROOT / "dist" / "AIMux" / output_name
    if not output.is_file():
        raise SystemExit(f"打包失败：未找到输出文件 {output}")
    _log(f"打包完成，PyInstaller 用时 {elapsed:.1f} 秒：{output}")


if __name__ == "__main__":
    main()
