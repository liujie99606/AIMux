from __future__ import annotations

import hashlib
import platform
import tempfile
from pathlib import Path

import httpx
from PySide6.QtCore import QProcess, QThread, QUrl, Qt, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout

from app.utils.version import project_version

_REPOSITORY = "quietforge-dev/AIMux"
_RELEASE_API = f"https://api.github.com/repos/{_REPOSITORY}/releases/latest"


def _architecture_asset() -> str:
    """返回当前系统应下载的 GitHub Release 资产名称。"""
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if platform.system() == "Windows":
        return f"AIMux-Windows-{arch}.exe"
    if platform.system() == "Darwin":
        return f"AIMux-macOS-{arch}.zip"
    raise RuntimeError(f"暂不支持当前系统：{platform.system()}")


def _version_key(version: str) -> tuple[int, ...]:
    """将 v1.2.3 等版本转换为可比较的整数元组。"""
    return tuple(int(part) if part.isdigit() else 0 for part in version.lstrip("vV").split(".")[:3])


class UpdateWorker(QThread):
    """在线程中检查 GitHub Release 并下载匹配当前架构的安装包。"""

    progress_changed = Signal(int, int)
    finished_success = Signal(str, str)
    failed = Signal(str)

    def run(self) -> None:
        try:
            current = project_version()
            headers = {"Accept": "application/vnd.github+json", "User-Agent": "AIMux"}
            with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
                release = client.get(_RELEASE_API)
                release.raise_for_status()
                payload = release.json()
                latest = str(payload.get("tag_name", ""))
                if not latest or _version_key(latest) <= _version_key(current):
                    self.finished_success.emit("", f"当前已是最新版本：v{current}")
                    return
                asset_name = _architecture_asset()
                asset = next((item for item in payload.get("assets", []) if item.get("name") == asset_name), None)
                if not asset:
                    raise RuntimeError(f"最新版本缺少当前架构安装包：{asset_name}")
                target_dir = Path(tempfile.gettempdir()) / "AIMux-updates"
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / asset_name
                temporary = target.with_suffix(target.suffix + ".part")
                total = int(asset.get("size") or 0)
                digest = hashlib.sha256()
                with client.stream("GET", str(asset["browser_download_url"])) as response:
                    response.raise_for_status()
                    downloaded = 0
                    with temporary.open("wb") as output:
                        for chunk in response.iter_bytes(1024 * 256):
                            output.write(chunk)
                            digest.update(chunk)
                            downloaded += len(chunk)
                            self.progress_changed.emit(downloaded, total)
                expected = str(asset.get("digest") or "")
                if expected.startswith("sha256:") and digest.hexdigest().lower() != expected[7:].lower():
                    temporary.unlink(missing_ok=True)
                    raise RuntimeError("下载文件校验失败，请重试")
                temporary.replace(target)
                self.finished_success.emit(str(target), f"v{latest} 下载完成：\n{target}")
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateDialog(QDialog):
    """检查更新并在应用内下载 GitHub Release 安装包。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("检查更新")
        self.setMinimumSize(760, 360)
        self.resize(820, 440)
        layout = QVBoxLayout(self)
        self.status = QLabel(f"当前版本：v{project_version()}\n正在检查 GitHub 最新版本...")
        self.status.setMinimumHeight(220)
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.run_button = QPushButton("安装并退出")
        self.run_button.hide()
        self.run_button.clicked.connect(self._run_downloaded_package)
        layout.addWidget(self.run_button)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self.close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        self.close_button.setEnabled(False)
        layout.addWidget(buttons)
        self._worker = UpdateWorker(self)
        self._download_path: Path | None = None
        self._worker.progress_changed.connect(self._on_progress)
        self._worker.finished_success.connect(self._on_success)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, downloaded: int, total: int) -> None:
        self.progress.show()
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(downloaded)
            self.status.setText(f"正在下载更新：{downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB")

    def _on_success(self, path: str, message: str) -> None:
        self.progress.hide()
        self.close_button.setEnabled(True)
        self.close_button.setText("关闭")
        self.status.setText(message)
        if path:
            self._download_path = Path(path)
            self.run_button.show()
            QMessageBox.information(self, "下载完成", "更新包已下载到临时目录。请关闭 AIMux 后运行安装包完成升级。")

    def _on_failed(self, message: str) -> None:
        self.progress.hide()
        self.close_button.setEnabled(True)
        self.status.setText(f"检查更新失败：{message}")

    def _run_downloaded_package(self) -> None:
        """启动已下载的 Windows 安装包或在 macOS 打开 ZIP。"""
        if self._download_path is None or not self._download_path.is_file():
            self.status.setText("更新包不存在，请重新检查更新")
            return
        if platform.system() == "Windows":
            result = QMessageBox.question(
                self,
                "安装更新",
                "将关闭 AIMux 并启动安装程序，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return
            if not QProcess.startDetached(str(self._download_path), []):
                self.status.setText("无法启动安装包，请手动打开下载文件")
                return
            application = QApplication.instance()
            if application is not None:
                application.quit()
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._download_path))):
            self.status.setText("无法打开更新包，请手动打开下载文件")
            return
        self.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        """下载期间保留对话框，避免销毁仍在运行的线程。"""
        if self._worker.isRunning():
            event.ignore()
            return
        event.accept()
