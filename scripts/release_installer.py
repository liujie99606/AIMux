from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def read_project_version() -> str:
    """从 pyproject.toml 读取唯一发布版本。"""
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return str(tomllib.loads(content)["project"]["version"])


def read_machine_architecture() -> str:
    """将当前 Windows 机器架构转换为发布产物使用的名称。"""
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        return "x64"
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    raise SystemExit(f"[AIMux] 不支持的 Windows 架构：{platform.machine()}")


def find_inno_compiler() -> Path | None:
    """从 PATH 和 Inno Setup 常见安装目录查找 ISCC。"""
    from_path = shutil.which("ISCC.exe")
    if from_path:
        return Path(from_path)
    candidates = (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    )
    return next((path for path in candidates if path.is_file()), None)


def main() -> None:
    """将 PyInstaller onedir 产物封装为单个 Windows 安装包。"""
    if "--check-only" in sys.argv:
        compiler = find_inno_compiler()
        if compiler is None:
            raise SystemExit(
                "[AIMux] 未找到 Inno Setup 6。\n"
                "[AIMux] 请先执行：winget install --id JRSoftware.InnoSetup -e"
            )
        print(f"[AIMux] 已找到 Inno Setup：{compiler}", flush=True)
        print(f"[AIMux] 当前发布版本：{read_project_version()}", flush=True)
        return
    executable = ROOT / "dist" / "AIMux" / "AIMux.exe"
    if not executable.is_file():
        raise SystemExit(f"[AIMux] 未找到应用构建产物：{executable}")
    compiler = find_inno_compiler()
    if compiler is None:
        raise SystemExit(
            "[AIMux] 未找到 Inno Setup 6。\n"
            "[AIMux] 请先执行：winget install --id JRSoftware.InnoSetup -e"
        )
    version = read_project_version()
    architecture = read_machine_architecture()
    print(f"[AIMux] 正在生成 {version} {architecture} 单文件安装包 ...", flush=True)
    subprocess.run(
        [
            str(compiler),
            "/Qp",
            f"/DMyAppVersion={version}",
            f"/DMyAppArch={architecture}",
            str(ROOT / "installer" / "AIMux.iss"),
        ],
        cwd=ROOT,
        check=True,
    )
    output = ROOT / "release" / f"AIMux-Windows-{architecture}.exe"
    if not output.is_file():
        raise SystemExit(f"[AIMux] 未找到预期安装包：{output}")
    print(f"[AIMux] 安装包：{output}", flush=True)


if __name__ == "__main__":
    main()
