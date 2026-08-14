from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer, QSize, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QIcon, QKeySequence
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
    QPushButton,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app.config import Settings
from app.ui.client import ApiClient, local_api_base_url
from app.ui.components.common.current_time_label import CurrentTimeLabel
from app.ui.components.update_dialog import UpdateDialog
from app.ui.views.accounts_view import AccountsView
from app.ui.views.models_view import ModelsView
from app.ui.views.monitor_view import MonitorView
from app.ui.views.settings_view import SettingsView
from app.ui.views.statistics_view import StatisticsView
from app.ui.views.usage_view import UsageView
from app.utils.resources import resource_path
from app.utils.version import project_version

_GITHUB_URL = "https://github.com/quietforge-dev/AIMux.git"


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.setWindowTitle("AIMux")
        # 默认尺寸跟随主屏幕可用区域：宽度取 80%，高度取 90%，窗口居中。
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available is not None:
            width = int(available.width() * 0.8)
            height = int(available.height() * 0.9)
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
        self.client = ApiClient(local_api_base_url(settings.host, settings.port), settings.local_token)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedWidth(180)
        self.navigation.setIconSize(QSize(18, 18))
        self.navigation.setSpacing(2)
        self.navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.content = QStackedWidget()
        self._page_factories: list[Callable[[ApiClient], QWidget]] = []
        self._page_widgets: list[QWidget | None] = []
        self._server_ready = False
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
        self.github_button = QPushButton("GitHub")
        self.github_button.setObjectName("githubLink")
        self.github_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon))
        self.github_button.setToolTip(_GITHUB_URL)
        self.github_button.setAccessibleName("打开 AIMux GitHub 地址")
        self.github_button.clicked.connect(self.open_github)
        sidebar_layout.addWidget(self.github_button)
        self.version_label = QLabel(f"版本 v{project_version()}")
        self.version_label.setObjectName("appVersion")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.version_label)
        self.update_button = QPushButton("检查更新")
        self.update_button.setObjectName("updateLink")
        self.update_button.clicked.connect(self.check_for_updates)
        sidebar_layout.addWidget(self.update_button)
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(self.content, 1)
        self.setCentralWidget(root)
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
        """构建各功能视图、导航项并接入内容栈。"""
        pages: list[tuple[str, QIcon, Callable[[ApiClient], QWidget]]] = [
            (
                "账号管理",
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
                AccountsView,
            ),
            (
                "使用记录",
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
                UsageView,
            ),
            (
                "数据统计",
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView),
                StatisticsView,
            ),
            (
                "模型维护",
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView),
                ModelsView,
            ),
            (
                "监控",
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView),
                MonitorView,
            ),
            (
                "设置",
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
                SettingsView,
            ),
        ]
        self._page_factories = [factory for _, _, factory in pages]
        self._page_widgets = [None] * len(pages)
        for title, icon, _ in pages:
            self.content.addWidget(self._loading_placeholder())
            self._add_navigation_item(title, icon)
        self.navigation.setCurrentRow(0)
        self.navigation.currentRowChanged.connect(self._on_navigation_changed)

    @staticmethod
    def _loading_placeholder() -> QWidget:
        """创建页面首次加载前显示的轻量占位控件。"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        label = QLabel("正在加载...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return placeholder

    def load_current_page(self) -> None:
        """在窗口显示后异步创建并加载当前页面。"""
        self._server_ready = True
        QTimer.singleShot(50, lambda: self._on_navigation_changed(self.navigation.currentRow()))

    def _on_navigation_changed(self, index: int) -> None:
        """切换页面并读取当前视图的最新数据。"""
        if not 0 <= index < len(self._page_factories):
            return
        self.content.setCurrentIndex(index)
        if not self._server_ready:
            return
        view = self._page_widgets[index]
        if view is None:
            placeholder = self.content.widget(index)
            view = self._page_factories[index](self.client)
            self.content.removeWidget(placeholder)
            placeholder.deleteLater()
            self.content.insertWidget(index, view)
            self._page_widgets[index] = view
            self.content.setCurrentIndex(index)
            return
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
        self._page_factories = []
        self._page_widgets = []
        while self.content.count():
            widget = self.content.widget(0)
            self.content.removeWidget(widget)
            widget.deleteLater()
        self._build_content()
        # 重建后恢复到原来所在页签。
        if 0 <= current < self.content.count():
            self.navigation.setCurrentRow(current)
            if self._server_ready and self._page_widgets[current] is None:
                self._on_navigation_changed(current)

    def _add_navigation_item(self, title: str, icon: QIcon) -> None:
        """添加一个固定尺寸的左侧菜单项，并与内容栈索引保持一致。"""
        item = QListWidgetItem(icon, title)
        item.setSizeHint(QSize(152, 42))
        self.navigation.addItem(item)

    def open_github(self) -> None:
        """提示 GitHub 地址后使用系统默认浏览器打开。"""
        QMessageBox.information(self, "打开 GitHub", f"将使用默认浏览器打开：\n{_GITHUB_URL}")
        if not QDesktopServices.openUrl(QUrl(_GITHUB_URL)):
            QMessageBox.warning(self, "打开失败", f"无法打开 GitHub 地址：\n{_GITHUB_URL}")

    def check_for_updates(self) -> None:
        """打开非阻塞更新检查和下载对话框。"""
        UpdateDialog(self).exec()

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
