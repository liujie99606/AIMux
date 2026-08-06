from __future__ import annotations

from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QStyle, QSystemTrayIcon, QTabWidget

from app.config import Settings
from app.ui.client import ApiClient
from app.ui.views.accounts_view import AccountsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.usage_view import UsageView


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("AIMux")
        self.resize(1180, 720)
        client = ApiClient(f"http://{settings.host}:{settings.port}", settings.local_token)
        tabs = QTabWidget()
        tabs.addTab(AccountsView(client), "账号管理")
        tabs.addTab(UsageView(client), "使用记录")
        tabs.addTab(SettingsView(client), "设置")
        self.setCentralWidget(tabs)
        self._closing = False
        self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self)
        menu = QMenu(self)
        show = QAction("显示 AIMux", self); show.triggered.connect(self.showNormal)
        quit_action = QAction("退出", self); quit_action.triggered.connect(self.quit_application)
        menu.addAction(show); menu.addAction(quit_action); self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda _: self.showNormal())
        self.tray.show()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            event.accept()
        else:
            event.ignore(); self.hide()

    def quit_application(self) -> None:
        self._closing = True
        self.tray.hide()
        QApplication.instance().quit()
