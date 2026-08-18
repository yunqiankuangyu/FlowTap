"""
标题栏组件 (PySide6) — 对齐原版 CTk 样式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QCursor

from config import Colors, FONT_B


def build_titlebar(app):
    """构建标题栏"""
    bar = QWidget()
    bar.setFixedHeight(40)
    bar.setStyleSheet(f"""
        QWidget {{
            background-color: {Colors.CARD};
        }}
        QPushButton {{
            background-color: transparent;
            color: {Colors.DIM};
            border: none;
            font: bold 17px 'MiSans';
        }}
        QPushButton:hover {{
            background-color: {Colors.RED};
            color: {Colors.TEXT};
        }}
        QLabel {{
            color: {Colors.TEXT};
        }}
    """)

    layout = QHBoxLayout(bar)
    layout.setContentsMargins(11, 0, 4, 0)
    layout.setSpacing(0)

    # 标题
    title = QLabel("⚡ 工具")
    title.setFont(FONT_B)
    layout.addWidget(title)
    layout.addStretch()

    # 按钮容器
    btn_container = QWidget()
    btn_layout = QHBoxLayout(btn_container)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    btn_layout.setSpacing(0)

    def make_title_btn(text, on_click, hover_color=None):
        btn = QPushButton(text)
        btn.setFixedSize(23, 23)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        if hover_color:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.DIM};
                    border: none;
                    font: bold 17px 'MiSans';
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                    color: {Colors.TEXT};
                }}
            """)
        btn.clicked.connect(on_click)
        return btn

    # 最小化按钮
    min_btn = make_title_btn("—", app._minimize_to_mini, Colors.BLUE)
    btn_layout.addWidget(min_btn)

    # 设置按钮
    settings_btn = make_title_btn("⚙", lambda: app._show_mode("settings"), Colors.BLUE)
    btn_layout.addWidget(settings_btn)

    # 关闭按钮
    close_btn = make_title_btn("✕", app.quit_app, Colors.RED)
    btn_layout.addWidget(close_btn)

    layout.addWidget(btn_container)

    # ── 拖动支持 ──
    app._drag_data = {"x": 0, "y": 0, "dragging": False}

    def mousePressEvent(e):
        if e.button() == Qt.LeftButton:
            app._drag_data["x"] = e.globalPosition().x() - app.frameGeometry().x()
            app._drag_data["y"] = e.globalPosition().y() - app.frameGeometry().y()
            app._drag_data["dragging"] = True

    def mouseMoveEvent(e):
        if app._drag_data["dragging"]:
            x = int(e.globalPosition().x() - app._drag_data["x"])
            y = int(e.globalPosition().y() - app._drag_data["y"])
            app.move(x, y)

    def mouseReleaseEvent(e):
        app._drag_data["dragging"] = False

    bar.mousePressEvent = mousePressEvent
    bar.mouseMoveEvent = mouseMoveEvent
    bar.mouseReleaseEvent = mouseReleaseEvent
    bar.setMouseTracking(True)

    return bar
