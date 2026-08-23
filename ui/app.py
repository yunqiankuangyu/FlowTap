"""
主窗口 (PySide6)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from config import Colors, FONT_B, FONT_M, load_settings, save_settings
from tasks import KeyboardTask, MouseTask

# 伪装标题
DISGUISE_TITLE = "svchost"

DEFAULT_STOP_HOTKEY = 0x77  # F8


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        # 加载设置并应用主题
        self._settings = load_settings()
        Colors.apply(self._settings["theme"])

        self.setWindowTitle(DISGUISE_TITLE)
        self.setFixedSize(360, 200)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        if self._settings["opacity"] < 1.0:
            self.setWindowOpacity(self._settings["opacity"])

        self.keyboard_tasks = []
        self.mouse_task = MouseTask()
        self.next_task_id = 1
        self._current_mode = "keyboard"
        self._mini_window = None
        self._tracked_height = 220
        self._ready = False  # 初始化完成前禁用所有操作

        # 全局停止热键（_build_ui 的设置页要用，必须先初始化）
        self._stop_hotkey = self._settings.get("stop_hotkey", DEFAULT_STOP_HOTKEY)

        self._build_ui()
        self._ready = True

        # 全局停止热键
        self._hotkey_capturing = False
        self._start_hotkey_poller()

    def _start_hotkey_poller(self):
        """QTimer轮询全局热键（Qt主线程事件循环内调GetAsyncKeyState）"""
        import ctypes
        self._hotkey_timer = QTimer(self)
        self._hotkey_timer.timeout.connect(self._poll_hotkey)
        self._hotkey_timer.start(50)

    def _poll_hotkey(self):
        """检测全局热键：捕获模式=抓新键，否则触发全部停止"""
        import ctypes
        u32 = ctypes.windll.user32
        if self._hotkey_capturing:
            for vk in range(0x08, 0x100):
                if u32.GetAsyncKeyState(vk) & 0x0001:
                    self._hotkey_capturing = False
                    if vk not in (0x1B,):  # ESC取消
                        self._stop_hotkey = vk
                        s = load_settings()
                        s["stop_hotkey"] = vk
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

    def _stop_hotkey_name(self):
        from vk_map import VK_NAME
        return VK_NAME.get(self._stop_hotkey, hex(self._stop_hotkey))

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
            self.content_layout.addWidget(self.settings_frame)
            self.setFixedSize(360, 540)

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
