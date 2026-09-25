"""
迷你模式窗口 (PySide6) — 对齐原版 CTk 样式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

from config import Colors, FONT_B, FONT_M, load_settings, save_settings
from .widgets import flat_btn, ghost_btn, style_label


def minimize_to_mini(app):
    """最小化到迷你模式"""
    if app._mini_window:
        return
    app._main_pos = (app.x(), app.y())
    app.hide()
    build_mini_mode(app)


def build_mini_mode(app):
    """构建迷你模式窗口"""
    s = load_settings()
    x = s.get("mini_pos_x", app._main_pos[0])
    y = s.get("mini_pos_y", app._main_pos[1])

    mini = QWidget()
    mini.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    mini.setFixedSize(250, 100)
    # 迷你窗口同样加 DWM 圆角，与主窗口一致
    from core.window_gate import apply_round_corners
    apply_round_corners(mini)
    mini.move(x, y)
    mini.setStyleSheet(f"background-color: {Colors.ACCENT};")
    if app._settings["opacity"] < 1.0:
        mini.setWindowOpacity(app._settings["opacity"])
    app._mini_window = mini

    main_layout = QVBoxLayout(mini)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # 标题栏
    bar = QWidget()
    bar.setFixedHeight(32)
    bar.setStyleSheet(f"background-color: {Colors.CARD};")
    bar_layout = QHBoxLayout(bar)
    bar_layout.setContentsMargins(8, 0, 6, 0)

    # 与主窗口同源：读 window_title 设置，缺省 FlowTap
    title = QLabel(s.get("window_title", "") or "FlowTap")
    title.setFont(FONT_B)
    style_label(title, Colors.TEXT)
    bar_layout.addWidget(title)
    bar_layout.addStretch()

    close_btn = QPushButton("✕")
    close_btn.setFixedSize(22, 22)
    close_btn.setCursor(QCursor(Qt.PointingHandCursor))
    ghost_btn(close_btn, hover=Colors.RED)
    close_btn.clicked.connect(app.quit_app)
    bar_layout.addWidget(close_btn)

    # 拖动
    drag_data = {"x": 0, "y": 0, "dragging": False}

    def start_drag(e):
        drag_data["x"] = e.globalPosition().x() - mini.x()
        drag_data["y"] = e.globalPosition().y() - mini.y()
        drag_data["dragging"] = True

    def do_drag(e):
        if drag_data["dragging"]:
            nx = int(e.globalPosition().x() - drag_data["x"])
            ny = int(e.globalPosition().y() - drag_data["y"])
            mini.move(nx, ny)

    def end_drag(e):
        drag_data["dragging"] = False
        s = load_settings()
        s["mini_pos_x"] = mini.x()
        s["mini_pos_y"] = mini.y()
        save_settings(s)

    bar.mousePressEvent = start_drag
    bar.mouseMoveEvent = do_drag
    bar.mouseReleaseEvent = end_drag
    bar.setMouseTracking(True)

    main_layout.addWidget(bar)

    # 按钮区（2列 grid，sticky="ew"）
    btn_frame = QWidget()
    btn_frame.setStyleSheet("background: transparent;")
    btn_layout = QHBoxLayout(btn_frame)
    btn_layout.setContentsMargins(8, 8, 8, 4)
    btn_layout.setSpacing(3)

    restore_btn = QPushButton("取消最小化")
    restore_btn.setFont(FONT_B)
    restore_btn.setFixedHeight(32)
    flat_btn(restore_btn, Colors.BLUE, hover=Colors.ACCENT)
    restore_btn.clicked.connect(lambda: restore_from_mini(app))
    app._mini_restore_btn = restore_btn
    btn_layout.addWidget(restore_btn, 1)

    all_btn = QPushButton("▶ 全部开始")
    all_btn.setFont(FONT_B)
    all_btn.setFixedHeight(32)
    flat_btn(all_btn, Colors.GREEN, hover=Colors.HOVER_GREEN)
    all_btn.clicked.connect(lambda: toggle_all_from_mini(app))
    app._mini_all_btn = all_btn
    btn_layout.addWidget(all_btn, 1)

    main_layout.addWidget(btn_frame)

    # 状态显示（pady=(0, 6)）
    status = QLabel("● 就绪")
    status.setFont(FONT_M)
    status.setAlignment(Qt.AlignCenter)
    status.setStyleSheet(f"color: {Colors.DIM}; background: transparent; padding-bottom: 6px;")
    app._mini_status = status
    main_layout.addWidget(status)

    mini.show()
    update_mini_status(app)


def restore_from_mini(app):
    """从迷你模式恢复"""
    if not app._mini_window:
        return
    s = load_settings()
    s["mini_pos_x"] = app._mini_window.x()
    s["mini_pos_y"] = app._mini_window.y()
    save_settings(s)

    mx = app._mini_window.x()
    my = app._mini_window.y()

    app._mini_window.close()
    app._mini_window = None

    app.show()
    app.move(mx, my)
    app.activateWindow()
    app.raise_()


def toggle_all_from_mini(app):
    """迷你模式下切换全部开始/停止"""
    from .keyboard_mode import toggle_all
    toggle_all(app)


def update_mini_status(app):
    """更新迷你窗口状态显示"""
    try:
        if not app._mini_window:
            return

        running_count = sum(1 for t in app.keyboard_tasks if t._running or getattr(t, '_countdown_active', False))
        total_count = len(app.keyboard_tasks)

        if running_count > 0:
            text = f"● 运行中 {running_count}/{total_count}"
            color = Colors.GREEN
        elif total_count > 0:
            text = f"● 已停止 {total_count} 个任务"
            color = Colors.DIM
        else:
            text = "● 就绪"
            color = Colors.DIM

        if hasattr(app, '_mini_status') and app._mini_status:
            app._mini_status.setText(text)
            app._mini_status.setStyleSheet(f"color: {color}; background: transparent; padding-bottom: 6px;")

        update_mini_btn(app)

        if app._mini_window:
            QTimer.singleShot(1000, lambda: update_mini_status(app))
    except Exception as e:
        from logger import log_error
        log_error("mini_status", e)


def update_mini_btn(app):
    """同步迷你模式的全部按钮状态"""
    #迷你窗口已关闭时按钮控件可能已销毁，直接跳过
    if not getattr(app, '_mini_window', None) or not hasattr(app, '_mini_all_btn'):
        return
    try:
        running_count = sum(1 for t in app.keyboard_tasks if t._running or getattr(t, '_countdown_active', False))
        if running_count > 0:
            app._mini_all_btn.setText("■ 全部停止")
            flat_btn(app._mini_all_btn, Colors.RED, hover=Colors.HOVER_RED)
        else:
            app._mini_all_btn.setText("▶ 全部开始")
            flat_btn(app._mini_all_btn, Colors.GREEN, hover=Colors.HOVER_GREEN)
    except RuntimeError:
        pass  #控件在遍历间隙被销毁，下一次窗口重建后自然恢复
