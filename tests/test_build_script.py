from __future__ import annotations

from pathlib import Path

from scripts import build
from scripts import release_installer


def test_existing_icons_skip_regeneration(tmp_path: Path, monkeypatch) -> None:
    """三种图标都存在时不能重复生成并破坏增量缓存。"""
    icons = tuple(tmp_path / name for name in ("aimux.png", "aimux.ico", "aimux.icns"))
    for icon in icons:
        icon.write_bytes(b"icon")
    calls: list[list[str]] = []
    monkeypatch.setattr(build, "REQUIRED_ICONS", icons)
    monkeypatch.setattr(build.subprocess, "run", lambda command, **_: calls.append(command))

    build._ensure_icons()

    assert calls == []


def test_missing_icon_triggers_regeneration(tmp_path: Path, monkeypatch) -> None:
    """任一平台图标缺失时应调用统一图标生成脚本。"""
    icons = tuple(tmp_path / name for name in ("aimux.png", "aimux.ico", "aimux.icns"))
    icons[0].write_bytes(b"icon")
    calls: list[tuple[list[str], bool]] = []
    monkeypatch.setattr(build, "REQUIRED_ICONS", icons)
    monkeypatch.setattr(
        build.subprocess,
        "run",
        lambda command, check: calls.append((command, check)),
    )

    build._ensure_icons()

    assert calls == [
        ([build.sys.executable, str(build.ROOT / "scripts" / "generate_icon.py")], True)
    ]


def test_pyinstaller_command_only_cleans_when_requested() -> None:
    """普通构建复用缓存，只有显式 --clean 才传给 PyInstaller。"""
    incremental = build._pyinstaller_command(False)
    clean = build._pyinstaller_command(True)

    assert "--clean" not in incremental
    assert "--clean" in clean
    assert f"{build.MIGRATIONS}{build.os.pathsep}migrations" in incremental
    assert incremental[-1] == str(build.ROOT / "app" / "__main__.py")


def test_windows_output_detection_matches_exact_executable(monkeypatch, tmp_path: Path) -> None:
    """Windows 检测应查询目标绝对路径，避免误拦其他 AIMux 进程。"""
    executable = tmp_path / "AIMux.exe"
    executable.write_bytes(b"")
    calls: list[list[str]] = []

    class Result:
        returncode = 0

    def fake_run(command: list[str], **_: object) -> Result:
        calls.append(command)
        return Result()

    monkeypatch.setattr(build.sys, "platform", "win32")
    monkeypatch.setattr(build.subprocess, "run", fake_run)

    assert build._windows_output_is_running(executable)
    assert str(executable.resolve()) in calls[0][-1]


def test_phase_log_mapping_covers_slow_build_steps() -> None:
    """PyInstaller 的主要耗时节点都应映射为明确阶段。"""
    assert "分析" in (build._phase_for_line("123 INFO: Building Analysis") or "")
    assert "Python 归档" in (build._phase_for_line("123 INFO: Building PYZ") or "")
    assert "可执行文件" in (build._phase_for_line("123 INFO: Building EXE") or "")
    assert "复制" in (build._phase_for_line("123 INFO: Building COLLECT") or "")


def test_output_path_matches_macos_app_bundle_layout(monkeypatch, tmp_path: Path) -> None:
    """macOS PyInstaller app bundle 位于 dist 根目录。"""
    monkeypatch.setattr(build, "ROOT", tmp_path)
    monkeypatch.setattr(build.sys, "platform", "darwin")

    assert build._output_path() == tmp_path / "dist" / "AIMux.app"


def test_windows_release_installer_preserves_user_data_and_supports_upgrade() -> None:
    """安装器应固定 AppId、按用户安装，且不能打包或删除用户数据目录。"""
    installer = (build.ROOT / "installer" / "AIMux.iss").read_text(encoding="utf-8")

    assert "AppId={#MyAppId}" in installer
    assert "DefaultDirName={localappdata}\\Programs\\{#MyAppName}" in installer
    assert "PrivilegesRequired=lowest" in installer
    assert 'Source: "..\\dist\\AIMux\\*"' in installer
    assert '#define MyAppArchitecture "arm64"' in installer
    assert '#define MyAppArchitecture "x64compatible"' in installer
    assert "ArchitecturesAllowed={#MyAppArchitecture}" in installer
    assert "ArchitecturesInstallIn64BitMode={#MyAppArchitecture}" in installer
    assert "AIMux-Windows-{#MyAppArch}" in installer
    assert "ChineseSimplified.isl" not in installer
    assert "%appdata%" not in installer.lower()
    assert "{userappdata}" not in installer.lower()


def test_windows_release_script_reads_project_version_and_uses_clean_build() -> None:
    """发布入口应先执行全量应用构建，再调用可测试的安装包脚本。"""
    script_path = build.ROOT / "scripts" / "win_release.bat"
    script_bytes = script_path.read_bytes()
    script = script_bytes.decode("ascii")

    assert 'call "%~dp0win_build.bat" --clean' in script
    assert '".venv\\Scripts\\python.exe" scripts\\release_installer.py' in script
    assert 'scripts\\release_installer.py --check-only' in script
    assert all(byte < 128 for byte in script_bytes)


def test_release_installer_reads_project_version() -> None:
    """安装包名称应使用 pyproject.toml 中的统一版本。"""
    assert release_installer.read_project_version() == "0.1.2"


def test_release_installer_maps_supported_windows_architectures(monkeypatch) -> None:
    """Windows 发布脚本应区分 x64 与 ARM64 原生产物。"""
    monkeypatch.setattr(release_installer.platform, "machine", lambda: "AMD64")
    assert release_installer.read_machine_architecture() == "x64"

    monkeypatch.setattr(release_installer.platform, "machine", lambda: "ARM64")
    assert release_installer.read_machine_architecture() == "arm64"


def test_release_installer_finds_common_user_install(monkeypatch, tmp_path: Path) -> None:
    """ISCC 不在 PATH 时应识别当前用户的 Inno Setup 默认位置。"""
    compiler = tmp_path / "Programs" / "Inno Setup 6" / "ISCC.exe"
    compiler.parent.mkdir(parents=True)
    compiler.write_bytes(b"")
    monkeypatch.setattr(release_installer.shutil, "which", lambda _: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "x86"))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "x64"))

    assert release_installer.find_inno_compiler() == compiler
