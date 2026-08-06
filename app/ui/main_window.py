from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app.config import Settings
from app.ui.client import ApiClient
from app.ui.views.accounts_view import AccountsView
from app.ui.views.models_view import ModelsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.usage_view import UsageView
from app.utils.resources import resource_path


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("AIMux")
        self.resize(1180, 720)
        icon = QIcon(str(resource_path("assets", "icons", "aimux.png")))
        self.setWindowIcon(icon)
        client = ApiClient(f"http://{settings.host}:{settings.port}", settings.local_token)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedWidth(176)
        self.navigation.setIconSize(QSize(20, 20))
        self.navigation.setSpacing(4)
        self.navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.content = QStackedWidget()
        self.content.addWidget(AccountsView(client))
        self.content.addWidget(ModelsView(client))
        self.content.addWidget(UsageView(client))
        self.content.addWidget(SettingsView(client))
        self._add_navigation_item("账号管理", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self._add_navigation_item("模型维护", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self._add_navigation_item("使用记录", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self._add_navigation_item("设置", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.navigation.currentRowChanged.connect(self.content.setCurrentIndex)
        self.navigation.setCurrentRow(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(16)
        sidebar_layout.addWidget(self.navigation)
        sidebar_layout.addStretch()
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(self.content, 1)
        self.setCentralWidget(root)
        self.setStyleSheet(
            "QFrame#sidebar { background: #f5f7fa; border-right: 1px solid #d9dde3; }"
            "QListWidget#navigation { border: 0; background: transparent; }"
            "QListWidget#navigation::item { padding: 10px 12px; border-radius: 6px; }"
            "QListWidget#navigation::item:selected { background: #dceeff; color: #075985; }"
            "QListWidget#navigation::item:hover { background: #e9edf2; }"
        )
        self._closing = False
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)
        show = QAction("显示 AIMux", self); show.triggered.connect(self.showNormal)
        quit_action = QAction("退出", self); quit_action.triggered.connect(self.quit_application)
        menu.addAction(show); menu.addAction(quit_action); self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda _: self.showNormal())
        self.tray.show()

    def _add_navigation_item(self, title: str, icon: QIcon) -> None:
        """添加一个固定尺寸的左侧菜单项，并与内容栈索引保持一致。"""
        item = QListWidgetItem(icon, title)
        item.setSizeHint(QSize(152, 42))
        self.navigation.addItem(item)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            event.accept()
        else:
            event.ignore(); self.hide()

    def quit_application(self) -> None:
        self._closing = True
        self.tray.hide()
        QApplication.instance().quit()
