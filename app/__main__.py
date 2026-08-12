from __future__ import annotations

import argparse
import socket
import threading
import time
import traceback

import uvicorn

from app.config import load_settings
from app.main import create_app
from app.utils.paths import data_dir


def serve(settings, server_holder: list[uvicorn.Server], errors: list[BaseException]) -> None:
    try:
        server = uvicorn.Server(uvicorn.Config(create_app(settings), host=settings.host, port=settings.port, log_config=None, access_log=False))
        server_holder.append(server)
        server.run()
    except BaseException as exc:
        errors.append(exc)
        try:
            (data_dir() / "startup-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass


def _port_available(host: str, port: int) -> bool:
    """预检查监听地址，避免第二个 AIMux 实例因端口冲突崩溃。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def _notify_running(address: str) -> None:
    """桌面模式下提示用户已有实例正在使用本地服务端口。"""
    from PySide6.QtWidgets import QApplication, QMessageBox

    application = QApplication.instance() or QApplication([])
    QMessageBox.information(None, "AIMux", f"AIMux 已在运行：{address}")
    application.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="AIMux local gateway")
    parser.add_argument("--server-only", action="store_true", help="只启动本地 API 服务")
    args = parser.parse_args()
    settings = load_settings()
    address = f"http://{settings.host}:{settings.port}"
    if not _port_available(settings.host, settings.port):
        if not args.server_only:
            _notify_running(address)
        return
    servers: list[uvicorn.Server] = []
    errors: list[BaseException] = []
    thread = threading.Thread(target=serve, args=(settings, servers, errors), name="aimux-api", daemon=True)
    thread.start()
    if args.server_only:
        thread.join()
        if errors:
            raise SystemExit(1)
        return
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    import qdarktheme
    from app.ui.main_window import MainWindow
    application = QApplication([])
    # 应用扁平深色主题，统一全局控件视觉风格。
    qdarktheme.setup_theme("dark")
    application.setQuitOnLastWindowClosed(False)
    window = MainWindow(settings); window.show()

    deadline = time.monotonic() + 8

    def load_when_server_ready() -> None:
        """窗口显示后等待后端就绪，再启动当前页面的数据加载。"""
        if errors:
            QMessageBox.critical(
                window,
                "AIMux 启动失败",
                f"本地服务启动失败，详情见：\n{data_dir() / 'startup-error.log'}",
            )
            application.quit()
            return
        if not servers or not servers[0].started:
            if time.monotonic() < deadline:
                QTimer.singleShot(50, load_when_server_ready)
                return
            QMessageBox.critical(window, "AIMux 启动失败", f"本地服务未能启动：{address}")
            application.quit()
            return
        window.load_current_page()

    QTimer.singleShot(0, load_when_server_ready)
    application.exec()
    if servers:
        servers[0].should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
