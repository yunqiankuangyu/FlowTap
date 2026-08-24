"""
主窗口 (PySide6)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QScrollArea, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from config import Colors, FONT_B, FONT_M, load_settings, save_settings
from tasks import KeyboardTask, MouseTask

# 伪装标题
DISGUISE_TITLE = "svchost"

DEFAULT_STOP_HOTKEY = 0x77  # F8
DEFAULT_START_HOTKEY = 0x76  # F7


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        # 加载设置并应用主题
        self._settings = load_settings()
        Colors.apply(self._settings["theme"])

        self.setWindowTitle(DISGUISE_TITLE)
        self.setFixedSize(360, 200)
        flags = Qt.FramelessWindowHint
        if self._settings.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        if self._settings["opacity"] < 1.0:
            self.setWindowOpacity(self._settings["opacity"])

        self.keyboard_tasks = []
        self.mouse_task = MouseTask()
        self.next_task_id = 1
        self._current_mode = "keyboard"
        self._mini_window = None
        self._tracked_height = 220  # 基准高度，与 keyboard_mode.BASE_WINDOW_H 一致
        self._ready = False  # 初始化完成前禁用所有操作

        # 全局停止热键（_build_ui 的设置页要用，必须先初始化）
        self._stop_hotkey = self._settings.get("stop_hotkey", DEFAULT_STOP_HOTKEY)
        self._start_hotkey = self._settings.get("start_hotkey", DEFAULT_START_HOTKEY)
        self._hotkey_capture_target = None  # 'stop' / 'start' / None

        self._build_ui()
        self._ready = True

        # 全局热键
        self._hotkey_capturing = False
        self._start_hotkey_poller()

    def _start_hotkey_poller(self):
        """QTimer轮询全局热键（Qt主线程事件循环内调GetAsyncKeyState）"""
        self._hotkey_timer = QTimer(self)
        self._hotkey_timer.timeout.connect(self._poll_hotkey)
        self._hotkey_timer.start(50)

    def _poll_hotkey(self):
        """检测全局热键：捕获模式=抓新键，否则触发开始/停止"""
        import ctypes
        u32 = ctypes.windll.user32
        if self._hotkey_capturing:
            for vk in range(0x08, 0x100):
                if u32.GetAsyncKeyState(vk) & 0x0001:
                    self._hotkey_capturing = False
                    if vk != 0x1B:  # ESC取消
                        target = self._hotkey_capture_target
                        if target == "stop":
                            self._stop_hotkey = vk
                            key = "stop_hotkey"
                        else:
                            self._start_hotkey = vk
                            key = "start_hotkey"
                        s = load_settings()
                        s[key] = vk
                        save_settings(s)
                    from .settings_mode import update_hotkey_label
                    try: update_hotkey_label(self)
                    except: pass
                    return
            return
        if u32.GetAsyncKeyState(self._stop_hotkey) & 0x0001:
            from .keyboard_mode import stop_all, show_floating_notification
            stop_all(self)
            if self.mouse_task._running:
                self.mouse_task.stop()
            show_floating_notification(self, f"⏹ 已全部停止 ({self._stop_hotkey_name()})")
        elif u32.GetAsyncKeyState(self._start_hotkey) & 0x0001:
            from .keyboard_mode import toggle_all, show_floating_notification, update_all_btn
            running = any(t._running or getattr(t, '_countdown_active', False) for t in self.keyboard_tasks)
            toggle_all(self)
            show_floating_notification(self, f"▶ 全部开始 ({self._start_hotkey_name()})" if not running else f"⏹ 已全部停止 ({self._start_hotkey_name()})")

    def _stop_hotkey_name(self):
        from vk_map import VK_NAME
        return VK_NAME.get(self._stop_hotkey, hex(self._stop_hotkey))

    def _start_hotkey_name(self):
        from vk_map import VK_NAME
        return VK_NAME.get(self._start_hotkey, hex(self._start_hotkey))

    def _build_ui(self):
        from .titlebar import build_titlebar
        from .keyboard_mode import build_keyboard_mode, auto_size, show_floating_notification
        from .settings_mode import build_settings_mode

        self._show_floating_notification = show_floating_notification

        # Central widget
        central = QWidget()
        central.setStyleSheet(f"background: {Colors.CARD};")
        self.setCentralWidget(central)
        self._central_layout = QVBoxLayout(central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)

        # 标题栏
        self._titlebar = build_titlebar(self)

        # 内容区域
        self.content_frame = QWidget()
        self.content_frame.setStyleSheet(f"background: {Colors.CARD};")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.keyboard_frame = QWidget()
        self.keyboard_frame.setStyleSheet(f"background: {Colors.CARD};")
        self.keyboard_layout = QVBoxLayout(self.keyboard_frame)
        self.keyboard_layout.setContentsMargins(0, 0, 0, 0)
        self.keyboard_layout.setSpacing(0)

        self.settings_frame = QWidget()
        self.settings_frame.setStyleSheet(f"background: {Colors.CARD};")
        self.settings_layout = QVBoxLayout(self.settings_frame)
        self.settings_layout.setContentsMargins(10, 10, 10, 10)
        self.settings_layout.setSpacing(8)

        build_keyboard_mode(self)
        build_settings_mode(self)

        self._show_mode("keyboard")

    def _show_mode(self, mode):
        # Remove all from content_layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Remove content_frame from central
        while self._central_layout.count():
            item = self._central_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Always add titlebar first
        self._central_layout.addWidget(self._titlebar)

        self._current_mode = mode

        if mode == "keyboard":
            self._central_layout.addWidget(self.content_frame)
            self.content_layout.addWidget(self.keyboard_frame)
            QTimer.singleShot(150, self._auto_size)
        elif mode == "settings":
            self._central_layout.addWidget(self.content_frame)
            # 设置页套一层滚动区，内容多时不挤压
            self.content_layout.addWidget(self._settings_scroll())
            # 窗口只有一个：高度保持当前值（由任务页 auto_size/拖动决定），不因切页变化

    def _scroll_style(self):
        """设置页滚动区样式（主题相关，可重复刷新）"""
        return f"""
            QScrollArea {{ background: {Colors.CARD}; border: none; }}
            QScrollBar:vertical {{ background: {Colors.ACCENT}; width: 6px; border-radius: 3px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {Colors.DIM}; border-radius: 3px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {Colors.BLUE}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """

    def refresh_settings_scroll_style(self):
        """主题切换时只刷新滚动区样式，不销毁重建（避免滚动条闪烁）"""
        sc = self._settings_scroller
        if sc is None:
            return
        for child in sc.findChildren(QScrollArea):
            child.setStyleSheet(self._scroll_style())

    def _settings_scroll(self):
        """设置页滚动容器（懒建，复用）：滚动内容 + 底部固定应用按钮"""
        if getattr(self, '_settings_scroller', None) is not None:
            # 容器还在：settings_frame 可能刚被重建，重新挂进去并刷新样式
            from .settings_mode import build_settings_mode  # noqa: F401
            sc = self._settings_scroller
            layout_item = sc.layout().itemAt(0)
            old_scroll = layout_item.widget() if layout_item else None
            if old_scroll is not None and old_scroll.widget() is not self.settings_frame:
                old_scroll.setWidget(self.settings_frame)
                old_scroll.setStyleSheet(self._scroll_style())
            # 拖动条可能随旧UI销毁，确保存在（幂等补挂）
            from .keyboard_mode import _build_drag_handle
            layout = sc.layout()
            it_last = layout.itemAt(layout.count() - 1)
            if it_last is None or it_last.widget() is None:
                layout.addWidget(_build_drag_handle(self))
            elif it_last.widget().height() != 12:  # 不是拖动条（被重建吞了）
                layout.addWidget(_build_drag_handle(self))
            return sc

        from .settings_mode import build_settings_mode  # noqa: F401 (按钮已建在 self 上)

        wrapper = QWidget()
        w_layout = QVBoxLayout(wrapper)
        w_layout.setContentsMargins(0, 0, 0, 10)
        w_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(self._scroll_style())
        scroll.setWidget(self.settings_frame)

        w_layout.addWidget(scroll, 1)
        if hasattr(self, '_settings_apply_btn'):
            w_layout.addWidget(self._settings_apply_btn)

        # 底部拖动条（与任务页同款，共享高度调整逻辑）
        from .keyboard_mode import _build_drag_handle
        handle = _build_drag_handle(self)
        w_layout.addWidget(handle)

        self._settings_scroller = wrapper
        return wrapper

    def _auto_size(self):
        from .keyboard_mode import auto_size
        auto_size(self)

    def _minimize_to_mini(self):
        from .mini_mode import minimize_to_mini
        minimize_to_mini(self)

    def _update_mini_btn(self):
        from .mini_mode import update_mini_btn
        update_mini_btn(self)

    def _update_all_btn(self):
        from .keyboard_mode import update_all_btn
        update_all_btn(self)

    def closeEvent(self, event):
        """关闭按钮 → 正常退出"""
        event.accept()
        self.quit_app()

    def quit_app(self):
        try:
            from .keyboard_mode import stop_all
            stop_all(self)
        except: pass
        try:
            if self.mouse_task._running: self.mouse_task.stop()
        except: pass
        QApplication.quit()

    # ── 混合模式代理方法 ──
    def _add_task(self):
        from .keyboard_mode import add_task
        add_task(self)

    def _toggle_all(self):
        from .keyboard_mode import toggle_all
        toggle_all(self)

    def _load_preset(self):
        from .keyboard_mode import load_preset
        load_preset(self)

    def _save_preset_dialog(self):
        from .keyboard_mode import save_preset_dialog
        save_preset_dialog(self)

    def _delete_preset(self):
        from .keyboard_mode import delete_preset_cmd
        delete_preset_cmd(self)
