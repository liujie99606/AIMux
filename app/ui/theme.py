from __future__ import annotations

from PySide6.QtWidgets import QApplication, QStyleFactory

import qdarktheme


APP_QSS = """
QWidget {
    color: #d9dde5;
    font-size: 13px;
}
QDialog {
    background: #202329;
}
QLabel {
    color: #d9dde5;
}
QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox,
QPlainTextEdit,
QTextEdit,
QListWidget,
QTableWidget {
    background-color: #262a31;
    color: #e8eaed;
    border: 1px solid #414854;
    border-radius: 5px;
    padding: 2px 8px;
    selection-background-color: #315d9e;
    selection-color: #ffffff;
}
QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    min-height: 24px;
}
QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QPlainTextEdit:focus,
QTextEdit:focus,
QListWidget:focus,
QTableWidget:focus {
    border: 1px solid #6d9eeb;
}
QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled,
QPlainTextEdit:disabled,
QTextEdit:disabled,
QListWidget:disabled,
QTableWidget:disabled {
    color: #858b96;
    background-color: #202329;
}
QComboBox {
    padding-right: 28px;
}
QComboBox::drop-down {
    width: 24px;
    border: 0;
    border-left: 1px solid #414854;
}
QComboBox QAbstractItemView {
    background-color: #262a31;
    color: #e8eaed;
    border: 1px solid #414854;
    selection-background-color: #315d9e;
    selection-color: #ffffff;
}
QAbstractSpinBox {
    padding-right: 28px;
}
QCheckBox {
    spacing: 8px;
    color: #d9dde5;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QPushButton {
    min-height: 26px;
    padding: 3px 12px;
    color: #e8eaed;
    background-color: #303640;
    border: 1px solid #4a5360;
    border-radius: 5px;
}
QPushButton:hover {
    background-color: #3a4553;
    border-color: #6d9eeb;
}
QPushButton:pressed {
    background-color: #273a5a;
}
QPushButton:disabled {
    color: #858b96;
    background-color: #262a31;
    border-color: #343a44;
}
QDialogButtonBox QPushButton {
    min-width: 84px;
    min-height: 26px;
}
QHeaderView::section {
    min-height: 24px;
    padding: 3px 8px;
    color: #d9dde5;
    background-color: #20252d;
    border: 0;
    border-right: 1px solid #343a44;
    border-bottom: 1px solid #414854;
}
QTableCornerButton::section {
    background-color: #20252d;
    border: 0;
    border-right: 1px solid #343a44;
    border-bottom: 1px solid #414854;
}
QTableWidget {
    gridline-color: #343a44;
    alternate-background-color: #22262d;
}
QTableWidget::viewport {
    background-color: #262a31;
}
QTableWidget::item {
    padding: 2px 6px;
}
QTableWidget::item:hover {
    background-color: #2b3442;
}
QTableWidget::item:selected {
    background-color: #2d4f82;
    color: #ffffff;
}
QTableWidget QPushButton {
    min-height: 20px;
    padding: 1px 8px;
}
QListWidget::item {
    min-height: 22px;
    padding: 2px 6px;
}
QListWidget::item:selected {
    background-color: #2d4f82;
    color: #ffffff;
}
QProgressBar {
    min-height: 18px;
    color: #e8eaed;
    background-color: #262a31;
    border: 1px solid #414854;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #4c86d9;
    border-radius: 3px;
}
QToolTip {
    color: #1f2937;
    background-color: #f8fafc;
    border: 1px solid #64748b;
    padding: 6px;
    font-size: 12px;
}
QMessageBox {
    background-color: #202329;
}
QMessageBox QLabel {
    color: #e8eaed;
}
QMenu {
    color: #e8eaed;
    background-color: #262a31;
    border: 1px solid #414854;
}
QMenu::item {
    padding: 7px 28px 7px 12px;
}
QMenu::item:selected {
    background-color: #2d4f82;
}
QScrollBar:vertical {
    width: 12px;
    margin: 2px;
    background: #202329;
}
QScrollBar::handle:vertical {
    min-height: 24px;
    background: #4a5360;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #637083;
}
QScrollBar:horizontal {
    height: 12px;
    margin: 2px;
    background: #202329;
}
QScrollBar::handle:horizontal {
    min-width: 24px;
    background: #4a5360;
    border-radius: 5px;
}
QScrollBar::add-line,
QScrollBar::sub-line,
QScrollBar::add-page,
QScrollBar::sub-page {
    background: none;
    border: 0;
}
QFrame#sidebar {
    background: #1e2128;
    border-right: 1px solid #2d3139;
}
QLabel#brand {
    color: #e8eaed;
    font-size: 16px;
    font-weight: 600;
    padding: 6px 0;
}
QLabel#appVersion,
QLabel#sidebarClock {
    color: #8b909a;
    font-size: 12px;
    padding: 2px 0 4px;
}
QLabel#pageTitle {
    color: #e8eaed;
    font-size: 20px;
    font-weight: 600;
}
QLabel#statisticsGroupTitle {
    color: #c5c8ce;
    font-size: 15px;
    font-weight: 600;
}
QLabel#monitorStatus {
    color: #aeb6c4;
    padding: 2px 0;
}
QListWidget#navigation {
    border: 0;
    background: transparent;
    outline: 0;
}
QListWidget#navigation::item {
    min-height: 26px;
    padding: 9px 12px;
    border-radius: 6px;
    color: #c5c8ce;
}
QListWidget#navigation::item:selected {
    background: #3b82f6;
    color: #ffffff;
}
QListWidget#navigation::item:hover {
    background: #2d3139;
}
QPushButton#githubLink {
    color: #c5c8ce;
    text-align: left;
    padding: 9px 12px;
}
QPushButton#githubLink:hover,
QPushButton#updateLink:hover {
    background: #2d3139;
}
QPushButton#updateLink {
    color: #8b909a;
    text-align: center;
    padding: 5px;
}
QFrame#statCard {
    background: #1e2128;
    border: 1px solid #2d3139;
    border-radius: 8px;
}
QLabel#statTitle {
    color: #8b909a;
    font-size: 12px;
}
QLabel#statValue {
    color: #e8eaed;
    font-size: 20px;
    font-weight: 600;
}
"""


def setup_application_theme(application: QApplication) -> None:
    """初始化跨平台基础风格和 AIMux 深色控件主题。"""
    if "Fusion" in QStyleFactory.keys():
        application.setStyle(QStyleFactory.create("Fusion"))
    qdarktheme.setup_theme("dark", additional_qss=APP_QSS)
