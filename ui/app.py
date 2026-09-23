"""
主窗口 (PySide6)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QScrollArea, QFrame, QStackedWidget
from PySide6.QtCore import Qt, QTimer

from config import Colors, FONT_B, load_settings, save_settings
from tasks import MouseTask
from ui.keyboard_mode import WIN_W

# 伪装标题
DISGUISE_TITLE = "svchost"
WIN_RADIUS = 16   # 窗口圆角半径（自绘）

DEFAULT_STOP_HOTKEY = 0x77  # F8
DEFAULT_START_HOTKEY = 0x76  # F7


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        # 加载设置并应用主题
        self._settings = load_settings()
        Colors.apply(self._settings["theme"])

        # 窗口绑定：启动时恢复绑定进程（前台闸门）
        from core.window_gate import set_bound_process
        set_bound_process(self._settings.get("bind_process", ""))

        self.setWindowTitle(DISGUISE_TITLE)
        self.setFixedSize(WIN_W, 392)
        flags = Qt.FramelessWindowHint
        if self._settings.get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        # 开启逐像素透明：样式表 border-radius 对无边框窗口无效，圆角靠下方 paintEvent 自绘
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # 圆角由下方 paintEvent 自绘；不再叠加 DWM 圆角（两层会残留一条弧线）

        if self._settings["opacity"] < 1.0:
            self.setWindowOpacity(self._settings["opacity"])

        self.keyboard_tasks = []
        self.mouse_task = MouseTask()
        self.next_task_id = 1
        self._current_mode = "keyboard"
        self._mini_window = None
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

    def paintEvent(self, event):
        """自绘圆角背景（样式表 border-radius 对无边框顶层窗口不生效，必须画）"""
        try:
            from PySide6.QtGui import QPainter, QColor, QBrush
            from PySide6.QtCore import QRectF
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(Colors.CARD)))   # 实时读主题色，换主题自动跟随
            p.drawRoundedRect(QRectF(self.rect()), WIN_RADIUS, WIN_RADIUS)
            p.end()
        except Exception:
            pass
        super().paintEvent(event)

    def resizeEvent(self, e):
        """阻止窗口被缩小到 _tracked_height 以下"""
        new_h = e.size().height()
        cur = getattr(self, '_tracked_height', 0)
        if cur > 0 and new_h < cur:
            e.ignore()
            return
        super().resizeEvent(e)

    def _start_hotkey_poller(self):
        """QTimer轮询全局热键（Qt主线程事件循环内调GetAsyncKeyState）"""
        self._hotkey_timer = QTimer(self)
        self._hotkey_timer.timeout.connect(self._poll_hotkey)
        self._hotkey_timer.start(50)

    def _poll_hotkey(self):
        """检测全局热键：捕获模式=抓新键，否则触发开始/停止"""
        try:
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
                show_floating_notification(self, f"⏹ 已停止 ({self._stop_hotkey_name()})")
            elif u32.GetAsyncKeyState(self._start_hotkey) & 0x0001:
                from .keyboard_mode import toggle_all, show_floating_notification, update_all_btn
                running = any(t._running or getattr(t, '_countdown_active', False) for t in self.keyboard_tasks)
                toggle_all(self)
                show_floating_notification(self, f"▶ 开始 ({self._start_hotkey_name()})" if not running else f"⏹ 已停止 ({self._start_hotkey_name()})")
        except Exception as e:
            from logger import log_error
            log_error("hotkey_poll", e)

    def _stop_hotkey_name(self):
        from vk_map import VK_NAME
        return VK_NAME.get(self._stop_hotkey, hex(self._stop_hotkey))

    def _start_hotkey_name(self):
        from vk_map import VK_NAME
        return VK_NAME.get(self._start_hotkey, hex(self._start_hotkey))

    def _build_ui(self):
        from .titlebar import build_titlebar
        from .keyboard_mode import build_keyboard_mode, show_floating_notification
        from .settings_mode import build_settings_mode

        self._show_floating_notification = show_floating_notification

        # Central widget
        central = QWidget()
        central.setStyleSheet("background: transparent;")   # 圆角由主窗口 paintEvent 统一画
        self.setCentralWidget(central)
        self._central_layout = QVBoxLayout(central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)

        # 标题栏
        self._titlebar = build_titlebar(self)

        # 内容区域：QStackedWidget 切换页面（不重建 widget）
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background: transparent;")

        # 页面 0：键盘/任务模式
        self.keyboard_frame = QWidget()
        self.keyboard_frame.setStyleSheet("background: transparent;")
        self.keyboard_layout = QVBoxLayout(self.keyboard_frame)
        self.keyboard_layout.setContentsMargins(10, 0, 10, 0)
        self.keyboard_layout.setSpacing(0)

        # 页面 1：设置模式
        self.settings_frame = QWidget()
        self.settings_frame.setStyleSheet("background: transparent;")
        self.settings_layout = QVBoxLayout(self.settings_frame)
        self.settings_layout.setContentsMargins(10, 0, 10, 4)
        self.settings_layout.setSpacing(8)

        build_keyboard_mode(self)
        build_settings_mode(self)
        from .settings_mode import install_wheel_guard
        install_wheel_guard(self)  # 防滚轮误调数值（任务页+设置页）

        # 滚动容器包裹键盘模式（与设置页对齐）
        self._keyboard_scroll = QScrollArea()
        self._keyboard_scroll.setWidgetResizable(True)
        self._keyboard_scroll.setFrameShape(QFrame.NoFrame)
        self._keyboard_scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: {Colors.ACCENT}; width: 6px; border-radius: 3px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {Colors.DIM}; border-radius: 3px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {Colors.BLUE}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
        self._keyboard_scroll.setWidget(self.keyboard_frame)

        # 滚动容器包裹设置模式
        self._settings_scroll = QScrollArea()
        self._settings_scroll.setWidgetResizable(True)
        self._settings_scroll.setFrameShape(QFrame.NoFrame)
        self._settings_scroll.setStyleSheet(self._scroll_style())
        self._settings_scroll.setWidget(self.settings_frame)

        self.content_stack.addWidget(self._keyboard_scroll)  # index 0
        self.content_stack.addWidget(self._settings_scroll)  # index 1

        # 底部栏 + 拖动条：常驻，不随切页变化
        self._ensure_bottom_bar(self._buttons_for("keyboard"))
        self._all_btn = self._bottom_btns[1]
        self._pause_btn = self._bottom_btns[2]
        from .keyboard_mode import update_pause_btn
        update_pause_btn(self)

        if getattr(self, '_drag_handle', None) is None:
            from .keyboard_mode import _build_drag_handle
            self._drag_handle = _build_drag_handle(self)

        # 组装 central_layout：titlebar → stack → bar → handle
        self._central_layout.addWidget(self._titlebar)
        self._central_layout.addWidget(self.content_stack, 1)
        self._central_layout.addWidget(self._bottom_bar)
        self._central_layout.addWidget(self._drag_handle)

        self._current_mode = "keyboard"

    def _show_mode(self, mode):
        self._current_mode = mode
        if mode == "keyboard":
            self.content_stack.setCurrentIndex(0)
            self._ensure_bottom_bar(self._buttons_for("keyboard"))
            self._all_btn = self._bottom_btns[1]
            self._pause_btn = self._bottom_btns[2]
            #底部按钮是按配置重建的(默认绿)，必须按真实运行状态重同步
            from .keyboard_mode import update_all_btn
            update_all_btn(self)
        elif mode == "settings":
            self.content_stack.setCurrentIndex(1)
            self._ensure_bottom_bar(self._buttons_for("settings"))
            from .settings_mode import _show_page, PAGE_APPEARANCE
            _show_page(self, getattr(self, "_settings_current_page", PAGE_APPEARANCE))

    def _buttons_for(self, mode):
        """各页的底部栏按钮配置"""
        if mode == "keyboard":
            return [
                ("＋ 新建任务", Colors.GREEN, Colors.HOVER_GREEN, self._add_task),
                ("▶ 全部开始", Colors.GREEN, Colors.HOVER_GREEN, self._toggle_all),
                ("⏸ 全部暂停", Colors.YELLOW, Colors.ACCENT, self._toggle_pause),
            ]
        from .settings_mode import apply_settings
        return [
            ("✓ 应用", Colors.GREEN, Colors.HOVER_GREEN, lambda: apply_settings(self)),
        ]

    def _scroll_style(self):
        """设置页滚动区样式（主题相关，可重复刷新）"""
        return f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: {Colors.ACCENT}; width: 6px; border-radius: 3px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {Colors.DIM}; border-radius: 3px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {Colors.BLUE}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """

    def _ensure_bottom_bar(self, buttons):
        """常驻底部栏：全局只建一次；按钮集变化时原地重建按钮，栏/几何参数不动"""
        from .keyboard_mode import build_bottom_bar
        if getattr(self, '_bottom_bar', None) is None:
            bar, btns = build_bottom_bar(self, buttons)
            self._bottom_bar = bar
            self._bottom_btns = btns
        else:
            # 原地换按钮：清掉旧的，按新配置重建（栏本身不动）
            bar = self._bottom_bar
            lay = bar.layout()
            while lay.count():
                it = lay.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            from .keyboard_mode import _make_btn, FONT_B
            from config import Colors
            self._bottom_btns = []
            for text, bg, hover, cb in buttons:
                btn = _make_btn(text, bg=bg, hover=hover, font=FONT_B, height=43)
                btn.clicked.connect(cb)
                lay.addWidget(btn)
                self._bottom_btns.append(btn)
        return self._bottom_bar



    def _minimize_to_mini(self):
        from .mini_mode import minimize_to_mini
        minimize_to_mini(self)

    def _update_mini_btn(self):
        from .mini_mode import update_mini_btn
        update_mini_btn(self)

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
        #槽内异常必须落日志，否则点按钮会静默无反应查无对证
        try:
            toggle_all(self)
        except Exception as e:
            from logger import log_error
            log_error("toggle_all", e)

    def _toggle_pause(self):
        from .keyboard_mode import toggle_pause_all
        toggle_pause_all(self)

    def _load_preset(self):
        from .keyboard_mode import load_preset
        load_preset(self)

    def _save_preset_dialog(self):
        from .keyboard_mode import save_preset_dialog
        save_preset_dialog(self)

    def _delete_preset(self):
        from .keyboard_mode import delete_preset_cmd
        delete_preset_cmd(self)
