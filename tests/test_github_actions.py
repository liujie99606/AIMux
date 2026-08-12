from __future__ import annotations

from pathlib import Path
import tomllib


def test_project_uses_installable_qdarktheme_package() -> None:
    """干净环境必须安装提供 qdarktheme 模块的当前维护包。"""
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = config["project"]["dependencies"]

    assert "pyqtdarktheme-fork>=2.3.6" in dependencies
    assert not any(item.startswith("pyqtdarktheme>=") for item in dependencies)


def test_cross_platform_workflow_builds_windows_and_macos_artifacts() -> None:
    """跨平台工作流应支持手动和 tag 触发，并交付两个平台产物。"""
    workflow = Path(".github/workflows/build-release.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert 'tags:\n      - "v*"' in workflow
    assert "runs-on: windows-latest" in workflow
    assert "runs-on: macos-14" in workflow
    assert 'PYTHONUTF8: "1"' in workflow
    assert "dist/AIMux.app AIMux-macOS.zip" in workflow
    assert "uses: actions/checkout@v5" in workflow
    assert "uses: actions/setup-python@v6" in workflow
    assert "AIMUX_PYTHON: python3.13" in workflow
    assert "python scripts/release_installer.py" in workflow
    assert "ditto -c -k --sequesterRsrc --keepParent" in workflow
    assert "AIMux-Windows-Installer" in workflow
    assert "AIMux-macOS-App" in workflow
    assert "contents: write" in workflow
    assert "if: startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "uses: actions/download-artifact@v5" in workflow
    assert workflow.count("uses: actions/upload-artifact@v5") == 2
    assert "gh release create" in workflow
    assert "gh release upload" in workflow
    assert "GH_REPO: ${{ github.repository }}" in workflow


def test_macos_build_checks_app_bundle_output(monkeypatch, tmp_path: Path) -> None:
    """macOS 打包完成后应校验 PyInstaller 生成的 app bundle。"""
    from scripts import build

    monkeypatch.setattr(build, "ROOT", tmp_path)
    monkeypatch.setattr(build.sys, "platform", "darwin")
    output = build.ROOT / "dist" / "AIMux.app"
    output.mkdir(parents=True)

    assert build._output_path() == output
    assert build._output_exists(output)
