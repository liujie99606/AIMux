from __future__ import annotations

from pathlib import Path

from scripts import build


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
