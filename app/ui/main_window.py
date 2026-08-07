from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app.config import Settings
from app.ui.client import ApiClient
from app.ui.components.common.current_time_label import CurrentTimeLabel
from app.ui.views.accounts_view import AccountsView
from app.ui.views.models_view import ModelsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.usage_view import UsageView
from app.utils.resources import resource_path


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("AIMux")
        # 默认尺寸跟随主屏幕可用区域：宽度取 80%，高度取 88%，窗口居中。
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available is not None:
            width = int(available.width() * 0.8)
            height = int(available.height() * 0.88)
            self.resize(width, height)
            self.move(
                available.x() + (available.width() - width) // 2,
                available.y() + (available.height() - height) // 2,
            )
        else:
            self.resize(1180, 720)
        icon = QIcon(str(resource_path("assets", "icons", "aimux.png")))
        self.setWindowIcon(icon)
        self.settings = settings
        self.client = ApiClient(f"http://{settings.host}:{settings.port}", settings.local_token)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedWidth(180)
        self.navigation.setIconSize(QSize(18, 18))
        self.navigation.setSpacing(2)
        self.navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.content = QStackedWidget()
        self._build_content()

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 14)
        sidebar_layout.setSpacing(14)
        # 顶部应用标识区，展示应用名与版本。
        brand = QLabel("AIMux")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(CurrentTimeLabel(sidebar))
        sidebar_layout.addWidget(self.navigation)
        sidebar_layout.addStretch()
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(self.content, 1)
        self.setCentralWidget(root)
        # 侧栏背景与导航项样式，与深色主题协调。
        self.setStyleSheet(
            "QFrame#sidebar { background: #1e2128; border-right: 1px solid #2d3139; }"
            "QLabel#brand { color: #e8eaed; font-size: 16px; font-weight: 600; padding: 6px 0; }"
            "QLabel#sidebarClock { color: #8b909a; font-size: 13px; padding: 2px 0 4px; }"
            "QListWidget#navigation { border: 0; background: transparent; outline: 0; }"
            "QListWidget#navigation::item { padding: 9px 12px; border-radius: 6px; color: #c5c8ce; }"
            "QListWidget#navigation::item:selected { background: #3b82f6; color: #ffffff; }"
            "QListWidget#navigation::item:hover { background: #2d3139; }"
            # 统计卡片样式。
            "QFrame#statCard { background: #1e2128; border: 1px solid #2d3139; border-radius: 8px; }"
            "QLabel#statTitle { color: #8b909a; font-size: 12px; }"
            "QLabel#statValue { color: #e8eaed; font-size: 20px; font-weight: 600; }"
            # 表格统一深色风格。
            "QTableWidget { border: 1px solid #2d3139; border-radius: 6px; }"
            "QHeaderView::section { background: #1e2128; border: 0; border-bottom: 1px solid #2d3139; padding: 6px 8px; }"
        )
        self._closing = False
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)
        show = QAction("显示 AIMux", self); show.triggered.connect(self.showNormal)
        quit_action = QAction("退出", self); quit_action.triggered.connect(self.quit_application)
        menu.addAction(show); menu.addAction(quit_action); self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda _: self.showNormal())
        self.tray.show()
        # Ctrl+R 热重载：销毁并重建所有视图，便于调试 UI 时免重启。
        reload_action = QAction(self)
        reload_action.setShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_R))
        reload_action.triggered.connect(self._reload_views)
        self.addAction(reload_action)

    def _build_content(self) -> None:
        """构建四个视图、导航项并接入内容栈。"""
        self.content.addWidget(AccountsView(self.client))
        self.content.addWidget(UsageView(self.client))
        self.content.addWidget(ModelsView(self.client))
        self.content.addWidget(SettingsView(self.client))
        self._add_navigation_item("账号管理", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self._add_navigation_item("使用记录", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self._add_navigation_item("模型维护", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self._add_navigation_item("设置", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.navigation.currentRowChanged.connect(self._on_navigation_changed)
        self.navigation.setCurrentRow(0)

    def _on_navigation_changed(self, index: int) -> None:
        """切换页面并读取当前视图的最新数据。"""
        self.content.setCurrentIndex(index)
        view = self.content.widget(index)
        refresh = getattr(view, "refresh", None)
        if callable(refresh):
            refresh()

    def _reload_views(self) -> None:
        """销毁旧视图并按最新源码重建，保留当前页签位置。

        调试 UI 时改完代码保存，按 Ctrl+R 即可立即看到改动，无需重启进程；
        后端 API 服务不受影响，重建后各视图会自行刷新数据。
        """
        current = self.navigation.currentRow()
        # 断开旧导航信号，避免重建过程中触发 setCurrentIndex。
        self.navigation.currentRowChanged.disconnect(self._on_navigation_changed)
        self.navigation.clear()
        for index in range(self.content.count()):
            widget = self.content.widget(index)
            self.content.removeWidget(widget)
            widget.deleteLater()
        self._build_content()
        # 重建后恢复到原来所在页签。
        if 0 <= current < self.content.count():
            self.navigation.setCurrentRow(current)

    def _add_navigation_item(self, title: str, icon: QIcon) -> None:
        """添加一个固定尺寸的左侧菜单项，并与内容栈索引保持一致。"""
        item = QListWidgetItem(icon, title)
        item.setSizeHint(QSize(152, 42))
        self.navigation.addItem(item)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            event.accept()
            return
        # 点右上角 X 时弹窗让用户选择：直接退出或最小化到托盘。
        choice = QMessageBox(
            QMessageBox.Icon.Question,
            "关闭 AIMux",
            "你想要直接退出 AIMux，还是最小化到托盘后台运行？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            self,
        )
        choice.button(QMessageBox.StandardButton.Yes).setText("直接退出")
        choice.button(QMessageBox.StandardButton.No).setText("最小化到托盘")
        choice.button(QMessageBox.StandardButton.Cancel).setText("取消")
        result = choice.exec()
        if result == QMessageBox.StandardButton.Yes:
            self.quit_application()
            event.accept()
        elif result == QMessageBox.StandardButton.No:
            event.ignore()
            self.hide()
        else:
            event.ignore()

    def quit_application(self) -> None:
        self._closing = True
        self.tray.hide()
        QApplication.instance().quit()
