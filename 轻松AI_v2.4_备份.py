"""
轻松AI - 键鼠模拟器 v2.4 (防检测精简版)
依赖: pip install customtkinter
反检测: 底层Win32 API + 随机抖动 + 进程伪装
字体: MiSans (需安装)
"""

import customtkinter as ctk
import ctypes, ctypes.wintypes, threading, time, random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

DISGUISE_TITLE = "svchost"

INPUT_KEYBOARD, INPUT_MOUSE = 1, 0
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
MOUSEEVENTF_ABSOLUTE, MOUSEEVENTF_MOVE = 0x8000, 0x0001

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.wintypes.WORD), ("wScan", ctypes.wintypes.WORD),
                ("dwFlags", ctypes.wintypes.DWORD), ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.wintypes.LONG), ("dy", ctypes.wintypes.LONG),
                ("mouseData", ctypes.wintypes.DWORD), ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("union", INPUT_UNION)]

def random_delay(base, jitter=0.1):
    time.sleep(max(0.01, base * (1 + random.uniform(-jitter, jitter))))

class InputSimulator:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        ctypes.windll.kernel32.SetErrorMode(0x0003)

    def _make_input(self, input_type, **kwargs):
        inp = INPUT()
        inp.type = input_type
        if input_type == INPUT_KEYBOARD:
            inp.union.ki.wVk = kwargs.get('vk', 0)
            inp.union.ki.wScan = kwargs.get('scan', 0)
            inp.union.ki.dwFlags = kwargs.get('flags', 0)
        elif input_type == INPUT_MOUSE:
            inp.union.mi.dx = kwargs.get('dx', 0)
            inp.union.mi.dy = kwargs.get('dy', 0)
            inp.union.mi.dwFlags = kwargs.get('flags', 0)
        inp.union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
        return inp

    def _send(self, *inputs):
        arr = (INPUT * len(inputs))(*inputs)
        self.user32.SendInput(len(inputs), ctypes.byref(arr), ctypes.sizeof(INPUT))

    def tap_key(self, vk):
        scan = self.user32.MapVirtualKeyW(vk, 0)
        self._send(
            self._make_input(INPUT_KEYBOARD, vk=vk, scan=scan),
            self._make_input(INPUT_KEYBOARD, vk=vk, scan=scan, flags=KEYEVENTF_KEYUP)
        )
        random_delay(0.05, 0.3)

    def click_mouse(self, x, y):
        self.move_mouse(x, y)
        random_delay(0.02, 0.5)
        sw, sh = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
        ax, ay = int(x * 65535 / sw), int(y * 65535 / sh)
        flags_d = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        flags_u = MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        self._send(
            self._make_input(INPUT_MOUSE, dx=ax, dy=ay, flags=flags_d),
            self._make_input(INPUT_MOUSE, dx=ax, dy=ay, flags=flags_u)
        )

    def move_mouse(self, x, y):
        sw, sh = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
        ax, ay = int(x * 65535 / sw), int(y * 65535 / sh)
        self._send(self._make_input(INPUT_MOUSE, dx=ax, dy=ay,
                                   flags=MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE))

    def get_mouse_pos(self):
        p = ctypes.wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(p))
        return (p.x, p.y)

# ─── 主题配置 ───
# appearance_mode 在 __init__ 中根据主题动态设置

# 字体
FONT_B = ("MiSans", 13, "bold")
FONT_M = ("MiSans", 13)

# ─── 主题系统 ───
THEMES = {
    # ── 暗色系（高饱和，各有性格）──
    "🔵 默认蓝":   {"CARD": "#1a2a4a", "ACCENT": "#121e38", "BLUE": "#4d9cff", "GREEN": "#4ade80", "RED": "#f87171", "YELLOW": "#facc15", "TEXT": "#e2e8f0", "TEXT2": "#94a3b8", "DIM": "#64748b", "HOVER_GREEN": "#22c55e", "HOVER_RED": "#ef4444"},
    "🟣 猫布丁":   {"CARD": "#382a50", "ACCENT": "#2a1e40", "BLUE": "#b4a0f0", "GREEN": "#a0e8a0", "RED": "#ff8090", "YELLOW": "#ffe080", "TEXT": "#e0d8f0", "TEXT2": "#c0b0e0", "DIM": "#8878b0", "HOVER_GREEN": "#60e0c0", "HOVER_RED": "#ff6080"},
    "🔥 炭火":     {"CARD": "#382818", "ACCENT": "#2a1e10", "BLUE": "#68c8e8", "GREEN": "#b8e060", "RED": "#ff6848", "YELLOW": "#ffb830", "TEXT": "#f0e8d8", "TEXT2": "#d0c0a0", "DIM": "#a08860", "HOVER_GREEN": "#98d040", "HOVER_RED": "#ff5030"},
    "🌲 北欧森林": {"CARD": "#1e3030", "ACCENT": "#162828", "BLUE": "#60c8d8", "GREEN": "#80e090", "RED": "#e07070", "YELLOW": "#e0d070", "TEXT": "#d8f0e0", "TEXT2": "#a0d0b8", "DIM": "#508878", "HOVER_GREEN": "#40d8a0", "HOVER_RED": "#d06060"},
    "🍇 葡萄冻":   {"CARD": "#302048", "ACCENT": "#241838", "BLUE": "#c8a0ff", "GREEN": "#90e0b0", "RED": "#ff80a0", "YELLOW": "#ffe090", "TEXT": "#e8d8f8", "TEXT2": "#c8b0e0", "DIM": "#9070c0", "HOVER_GREEN": "#60d8a0", "HOVER_RED": "#ff6090"},
    # ── 亮色系（柔和亮，不刺眼）──
    "🌿 清新绿":   {"CARD": "#d8edd8", "ACCENT": "#c8e0c8", "BLUE": "#3a9850", "GREEN": "#60c060", "RED": "#d04848", "YELLOW": "#e0a830", "TEXT": "#1a4020", "TEXT2": "#306840", "DIM": "#4a7a5a", "HOVER_GREEN": "#2a8840", "HOVER_RED": "#b83838"},
    "☀️ 暖阳金":   {"CARD": "#f8e8d0", "ACCENT": "#f0dcc0", "BLUE": "#d88830", "GREEN": "#90b848", "RED": "#d06050", "YELLOW": "#d89820", "TEXT": "#503820", "TEXT2": "#785838", "DIM": "#806840", "HOVER_GREEN": "#78a838", "HOVER_RED": "#b84838"},
    "🧊 冰川蓝":   {"CARD": "#d8e8f0", "ACCENT": "#c8dce8", "BLUE": "#3880c0", "GREEN": "#40a878", "RED": "#c85050", "YELLOW": "#c89830", "TEXT": "#182838", "TEXT2": "#385870", "DIM": "#507088", "HOVER_GREEN": "#308860", "HOVER_RED": "#a84040"},
    "🌸 樱花粉":   {"CARD": "#f0d8e0", "ACCENT": "#e8c8d8", "BLUE": "#b060a0", "GREEN": "#60a870", "RED": "#d06068", "YELLOW": "#d0a040", "TEXT": "#402030", "TEXT2": "#704860", "DIM": "#806070", "HOVER_GREEN": "#509060", "HOVER_RED": "#b85058"},
    "⚪ 极简白":   {"CARD": "#f0f0f0", "ACCENT": "#e4e4e4", "BLUE": "#3878c0", "GREEN": "#309848", "RED": "#c84040", "YELLOW": "#b89028", "TEXT": "#181820", "TEXT2": "#505060", "DIM": "#606068", "HOVER_GREEN": "#288038", "HOVER_RED": "#a83030"},
}

DEFAULT_THEME = "🔵 默认蓝"

class Colors:
    """全局颜色，通过 apply() 整体替换"""
    CARD = "#2b3a5c"
    ACCENT = "#222e4a"
    BLUE = "#5b9cf5"
    GREEN = "#5ec28a"
    RED = "#e8787f"
    YELLOW = "#e8c55a"
    TEXT = "#dce4f0"
    TEXT2 = "#a0b4d0"
    DIM = "#6a80a0"
    HOVER_GREEN = "#48b078"
    HOVER_RED = "#d06068"

    @classmethod
    def apply(cls, theme_name):
        t = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
        for k, v in t.items():
            setattr(cls, k, v)

import json, os
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")

def load_settings():
    defaults = {"opacity": 1.0, "theme": DEFAULT_THEME}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            defaults.update(json.load(f))
    except: pass
    # 防止主题名失效
    if defaults["theme"] not in THEMES:
        defaults["theme"] = DEFAULT_THEME
    return defaults

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def load_presets():
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def save_presets(presets):
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)

def delete_preset(name):
    presets = load_presets()
    if name in presets:
        del presets[name]
        save_presets(presets)
    return presets

class TaskStatus(Enum):
    IDLE, RUNNING, WAITING = "● 就绪", "● 运行中", "● 等待触发"

@dataclass
class KeyboardTask:
    task_id: int
    name: str
    key_sequence: List[int] = field(default_factory=list)
    key_interval: float = 0.5
    loop_interval: float = 80.0
    status: TaskStatus = TaskStatus.IDLE
    done_count: int = 0
    relation_type: str = "独立"  # "独立" 或 "在任务x后"
    dependency_task_id: Optional[int] = None  # 前置任务ID
    _running: bool = False
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _dependents: List['KeyboardTask'] = field(default_factory=list, repr=False)  # 依赖此任务的列表
    _callback: object = field(default=None, repr=False)  # 自身的UI回调
    _countdown_callback: object = field(default=None, repr=False)  # 延时倒计时UI回调

    def start(self, callback=None, countdown_callback=None):
        """启动任务。独立任务启动循环线程，依赖任务只设run=True等触发。"""
        if self._running: return
        self._running, self.status, self.done_count = True, TaskStatus.RUNNING, 0
        if self.relation_type == "独立":
            self._thread = threading.Thread(target=self._loop, args=(callback, countdown_callback), daemon=True)
            self._thread.start()
        else:
            # 依赖任务：不启动线程，等前置任务触发
            self.status = TaskStatus.WAITING

    def stop(self):
        self._running, self.status = False, TaskStatus.IDLE
        self._countdown_callback = None

    def _loop(self, callback, countdown_callback=None):
        """独立任务的主循环"""
        if getattr(self, '_loop_active', False): return
        self._loop_active = True
        try:
            sim = InputSimulator()
            while self._running:
                self.done_count += 1
                for vk in self.key_sequence:
                    if not self._running: return
                    try: sim.tap_key(vk)
                    except: pass
                    random_delay(self.key_interval, 0.15)
                if callback: callback()
                # 触发依赖此任务的其他任务
                for dep_task in self._dependents:
                    if dep_task._running:
                        threading.Thread(target=dep_task._run_once, daemon=True).start()
                # 循环倒计时显示（倒计时代替等待，不叠加）
                countdown_secs = int(self.loop_interval) - 1
                if countdown_callback and countdown_secs >= 1:
                    for i in range(countdown_secs, 0, -1):
                        if not self._running: return
                        countdown_callback(f"● 等待 {i}s...", Colors.YELLOW)
                        time.sleep(1)
                    if not self._running: return
                    countdown_callback("● 执行中...", Colors.GREEN)
                    # 剩余小数部分用 random_delay 补齐
                    remainder = self.loop_interval - countdown_secs
                    random_delay(remainder, 0.05)
                else:
                    random_delay(self.loop_interval, 0.05)
        finally:
            self._loop_active = False

    def _run_once(self):
        """被依赖触发时执行一次：等延时→执行按键"""
        if not self._running: return
        if self.loop_interval > 0:
            remaining = int(self.loop_interval)
            for i in range(remaining, 0, -1):
                if not self._running: return
                if self._countdown_callback:
                    self._countdown_callback(f"● 延时 {i}s...", Colors.YELLOW)
                time.sleep(1)
            if self._countdown_callback:
                self._countdown_callback("● 执行中...", Colors.GREEN)
        if not self._running: return
        sim = InputSimulator()
        self.done_count += 1
        for vk in self.key_sequence:
            if not self._running: return
            try: sim.tap_key(vk)
            except: pass
            random_delay(self.key_interval, 0.15)
        if self._callback: self._callback()

@dataclass
class MouseTask:
    position: Optional[tuple] = None
    interval: float = 1.0
    status: TaskStatus = TaskStatus.IDLE
    done_count: int = 0
    _running: bool = False
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _safe_radius: int = 300

    def start(self, callback=None):
        if self._running or not self.position: return
        self._running, self.status, self.done_count = True, TaskStatus.RUNNING, 0
        self._thread = threading.Thread(target=self._loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop(self, callback=None, msg="已停止"):
        self._running, self.status = False, TaskStatus.IDLE
        if callback: callback(msg)

    def _loop(self, callback):
        sim = InputSimulator()
        first = True
        while self._running:
            if self.position:
                if not first:
                    cur = sim.get_mouse_pos()
                    dx, dy = cur[0]-self.position[0], cur[1]-self.position[1]
                    if (dx*dx+dy*dy)**0.5 > self._safe_radius:
                        self.stop(callback, "安全停止"); return
                sim.move_mouse(*self.position)
                random_delay(0.05, 0.3)
            try: sim.click_mouse(*self.position); self.done_count += 1
            except: pass
            first = False
            random_delay(self.interval, 0.2)

VK_MAP = {}
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"): VK_MAP[c] = 0x41 + i
for i, c in enumerate("0123456789"): VK_MAP[c] = 0x30 + i
VK_MAP.update({'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B, 'backspace': 0x08,
               'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12,
               'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27})
for i in range(1, 13): VK_MAP[f"f{i}"] = 0x70 + i - 1
VK_NAME = {v: k.upper() for k, v in VK_MAP.items()}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 先加载设置并应用主题颜色，再创建任何 UI 控件
        self._settings = load_settings()
        Colors.apply(self._settings["theme"])
        # 根据主题文字亮度自动切换 dark/light 模式
        r, g, b = int(Colors.TEXT[1:3], 16), int(Colors.TEXT[3:5], 16), int(Colors.TEXT[5:7], 16)
        brightness = 0.299 * r + 0.587 * g + 0.114 * b
        ctk.set_appearance_mode("light" if brightness < 128 else "dark")
        self.title(DISGUISE_TITLE)
        self.geometry("346x100+100+100")
        self.configure(fg_color=Colors.ACCENT)
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.resizable(False, False)
        if self._settings["opacity"] < 1.0:
            self.attributes("-alpha", self._settings["opacity"])
        self.keyboard_tasks: List[KeyboardTask] = []
        self.mouse_task = MouseTask()
        self.next_task_id = 1
        self._current_mode = "keyboard"
        self._mini_window = None  # 迷你模式窗口
        self.bind("<Button-1>", self._on_global_click)
        self._build_ui()

    def _on_global_click(self, event):
        w = event.widget
        while w and not isinstance(w, ctk.CTkEntry):
            w = w.master
        if not w: self.focus_set()

    def _build_ui(self):
        self._build_titlebar()
        self._build_mode_tabs()
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.keyboard_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.mouse_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self._build_keyboard_mode()
        self._build_mouse_mode()
        self._build_settings_mode()
        self._show_mode("keyboard")

    def _build_titlebar(self):
        bar = ctk.CTkFrame(self, height=40, fg_color=Colors.CARD, corner_radius=0)
        bar.pack(fill="x"); bar.pack_propagate(False)
        self._drag_data = {"x": 0, "y": 0}
        bar.bind("<Button-1>", lambda e: self._drag_data.update({"x": e.x, "y": e.y}))
        bar.bind("<B1-Motion>", lambda e: self.geometry(
            f"+{self.winfo_x()+e.x-self._drag_data['x']}+{self.winfo_y()+e.y-self._drag_data['y']}"))
        ctk.CTkLabel(bar, text="⚡ 工具", font=FONT_B, text_color=Colors.TEXT).pack(side="left", padx=11)
        ctk.CTkButton(bar, text="✕", width=23, height=23, fg_color="transparent",
                      text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B, 
                      command=self.quit_app).pack(side="right", padx=2, pady=8)
        ctk.CTkButton(bar, text="⚙", width=23, height=23, fg_color="transparent",
                      text_color=Colors.DIM, hover_color=Colors.BLUE, font=FONT_B, 
                      command=lambda: self._show_mode("settings")).pack(side="right", padx=2, pady=8)
        ctk.CTkButton(bar, text="—", width=23, height=23, fg_color="transparent",
                      text_color=Colors.DIM, hover_color=Colors.BLUE, font=FONT_B, 
                      command=self._minimize_to_mini).pack(side="right", padx=2, pady=8)

    def _build_mode_tabs(self):
        tab = ctk.CTkFrame(self, height=43, fg_color=Colors.CARD, corner_radius=0)
        tab.pack(fill="x"); tab.pack_propagate(False)
        self.tab_kb = ctk.CTkButton(tab, text="⌨ 键盘", font=FONT_B, fg_color=Colors.BLUE,
                                    text_color=Colors.TEXT, hover_color=Colors.ACCENT, command=lambda: self._show_mode("keyboard"))
        self.tab_kb.pack(side="left", fill="both", expand=True, padx=(2, 1), pady=4)
        self.tab_ms = ctk.CTkButton(tab, text="🖱 鼠标", font=FONT_B, fg_color=Colors.CARD,
                                    text_color=Colors.TEXT, hover_color=Colors.ACCENT, command=lambda: self._show_mode("mouse"))
        self.tab_ms.pack(side="right", fill="both", expand=True, padx=(1, 2), pady=4)

    def _show_mode(self, mode):
        self.keyboard_frame.pack_forget(); self.mouse_frame.pack_forget(); self.settings_frame.pack_forget()
        self.content_frame.pack_forget()
        if mode == "keyboard":
            self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            self.keyboard_frame.pack(fill="both", expand=True)
            self.tab_kb.configure(fg_color=Colors.BLUE)
            self.tab_ms.configure(fg_color=Colors.CARD)
            self.after(150, self._auto_size)
        elif mode == "mouse":
            self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            self.mouse_frame.pack(fill="both", expand=True)
            self.tab_kb.configure(fg_color=Colors.CARD)
            self.tab_ms.configure(fg_color=Colors.BLUE)
            self.after(150, self._auto_size)
        elif mode == "settings":
            self.content_frame.pack(fill="x", padx=5, pady=(0, 5))
            self.settings_frame.pack(fill="x")
            self.tab_kb.configure(fg_color=Colors.CARD)
            self.tab_ms.configure(fg_color=Colors.CARD)
            self.geometry("346x540")

    def _auto_size(self):
        """根据内容自动调整窗口高度"""
        self.update_idletasks()
        for frame in [self.mouse_frame, self.keyboard_frame]:
            if frame.winfo_ismapped():
                h = 0
                for child in frame.winfo_children():
                    h += child.winfo_reqheight()
                    mg = child.pack_info().get("pady", 0)
                    if isinstance(mg, tuple):
                        h += mg[0] + mg[1]
                    else:
                        h += mg * 2
                h = min(h, self.winfo_screenheight() - 100)
                if frame is self.mouse_frame:
                    h = max(0, h - 8)
                elif frame is self.keyboard_frame:
                    h = int(h * 1.10)
                w = 346
                x, y = self.winfo_x(), self.winfo_y()
                self.geometry(f"{w}x{h}+{x}+{y}")
                break

    def _auto_size_settings(self):
        """设置页专用：量内容高度设窗口"""
        self.update_idletasks()
        # 量 settings_frame 的实际内容高度
        content_h = self.settings_frame.winfo_reqheight()
        # 加上标题栏(40) + 标签栏(43) + content_frame 上下 padding(5+5) + 一些余量
        total_h = content_h + 40 + 43 + 10 + 24
        total_h = min(total_h, self.winfo_screenheight() - 100)
        w = 346
        x, y = self.winfo_x(), self.winfo_y()
        self.geometry(f"{w}x{total_h}+{x}+{y}")

    def _build_keyboard_mode(self):
        # ── 预设管理栏 ──
        pf = ctk.CTkFrame(self.keyboard_frame, fg_color=Colors.CARD, corner_radius=11)
        pf.pack(fill="x", padx=5, pady=(5, 3))
        presets = load_presets()
        preset_names = list(presets.keys()) if presets else ["无预设"]
        self._preset_var = ctk.StringVar(value=preset_names[0])
        self._preset_menu = ctk.CTkOptionMenu(pf, variable=self._preset_var, values=preset_names,
                                                       font=FONT_M, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                                                       button_color=Colors.DIM, width=120, height=25)
        self._preset_menu.pack(side="left", padx=(7, 4), pady=7)
        ctk.CTkButton(pf, text="加载", width=36, height=25, font=FONT_M,
                      fg_color=Colors.BLUE, text_color=Colors.TEXT,
                      hover_color=Colors.ACCENT, command=self._load_preset).pack(side="left", padx=2)
        ctk.CTkButton(pf, text="保存", width=36, height=25, font=FONT_M,
                      fg_color=Colors.GREEN, text_color=Colors.TEXT,
                      hover_color=Colors.ACCENT, command=self._save_preset_dialog).pack(side="left", padx=2)
        ctk.CTkButton(pf, text="删除", width=36, height=25, font=FONT_M,
                      fg_color=Colors.RED, text_color=Colors.TEXT,
                      hover_color=Colors.ACCENT, command=self._delete_preset).pack(side="left", padx=2)

        container = ctk.CTkFrame(self.keyboard_frame, fg_color="transparent")
        container.pack(fill="both", expand=True)

        self.task_canvas = ctk.CTkCanvas(container, bg=Colors.ACCENT, highlightthickness=0)
        self.task_scroll = ctk.CTkFrame(self.task_canvas, fg_color="transparent")
        self.task_canvas_window = self.task_canvas.create_window(0, 0, window=self.task_scroll, anchor="nw")
        self.task_canvas.bind("<Configure>", lambda e: self.task_canvas.itemconfig(self.task_canvas_window, width=e.width))
        self.task_canvas.pack(side="left", fill="both", expand=True)

        def _on_mousewheel(event):
            self.task_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.task_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        bf = ctk.CTkFrame(self.keyboard_frame, fg_color="transparent", height=66)
        bf.pack(fill="x", pady=(11, 0)); bf.pack_propagate(False)
        bf.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(bf, text="＋ 新建任务", font=FONT_B, fg_color=Colors.GREEN,
                      text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=43,
                      command=self._add_task).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self._all_btn = ctk.CTkButton(bf, text="▶ 全部开始", font=FONT_B, fg_color=Colors.GREEN,
                      text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=43,
                      command=self._toggle_all)
        self._all_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))

    def _add_task(self):
        keys = [0x52, 0x20] if self.next_task_id == 1 else []
        task = KeyboardTask(self.next_task_id, f"任务{self.next_task_id}", keys)
        self.next_task_id += 1
        self.keyboard_tasks.append(task)
        self._create_card(task)

    def _create_card(self, task):
        card = ctk.CTkFrame(self.task_scroll, fg_color=Colors.CARD, corner_radius=11)
        card.pack(fill="x", pady=5)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=11, pady=(11, 5))
        name_e = ctk.CTkEntry(hdr, font=FONT_B, fg_color=Colors.ACCENT,
                              text_color=Colors.TEXT, border_width=0, width=79, height=25)
        name_e.insert(0, task.name); name_e.pack(side="left")
        name_e.bind("<FocusOut>", lambda e: setattr(task, 'name', name_e.get()))
        keys_lbl = ctk.CTkLabel(hdr, text=f"键位: {self._fmt_keys(task.key_sequence)}",
                                font=FONT_B, text_color=Colors.BLUE, anchor="w")
        keys_lbl.pack(side="left", padx=(9, 0))

        kf = ctk.CTkFrame(card, fg_color="transparent")
        kf.pack(fill="x", padx=11, pady=7)
        kf.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(kf, text="添加键", font=FONT_B, fg_color=Colors.BLUE,
                      text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                      command=lambda: self._capture_key(task, keys_lbl)).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(kf, text="删除末位", font=FONT_B, fg_color=Colors.DIM,
                      text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                      command=lambda: self._rm_key(task, keys_lbl)).grid(row=0, column=1, sticky="ew", padx=(0, 4))
        ctk.CTkButton(kf, text="清空", font=FONT_B, fg_color=Colors.DIM,
                      text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                      command=lambda: self._clr_keys(task, keys_lbl)).grid(row=0, column=2, sticky="ew")

        sf = ctk.CTkFrame(card, fg_color="transparent")
        sf.pack(fill="x", padx=11, pady=5)

        ctk.CTkLabel(sf, text="间隔:", font=FONT_M, text_color=Colors.TEXT2).pack(side="left")
        iv_var = ctk.DoubleVar(value=task.key_interval)
        spin1 = self._make_spinbox(sf, iv_var, 0, 30.0, 0.5, task, 'key_interval',
                                   on_change=lambda v: self._check_interval_btn(task))
        spin1.pack(side="left", padx=(5, 18))

        task._loop_label = ctk.CTkLabel(sf, text="循环:", font=FONT_M, text_color=Colors.TEXT2)
        task._loop_label.pack(side="left")
        lv_var = ctk.DoubleVar(value=task.loop_interval)
        spin2 = self._make_spinbox(sf, lv_var, 0, 999, 5, task, 'loop_interval')
        spin2.pack(side="left", padx=6)
        task._loop_var = lv_var
        task._loop_frame = spin2

        rf = ctk.CTkFrame(card, fg_color="transparent")
        rf.pack(fill="x", padx=11, pady=(0, 5))
        ctk.CTkLabel(rf, text="关系:", font=FONT_M, text_color=Colors.TEXT2).pack(side="left")
        rel_var = ctk.StringVar(value=task.relation_type)
        ctk.CTkOptionMenu(rf, variable=rel_var, values=["独立", "在任务x后"],
                                   font=FONT_M, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                                   button_color=Colors.DIM, width=72, height=25,
                           command=lambda v: self._on_rel_change(v, task, rf, rel_var)).pack(side="left", padx=6)

        dep_frame = ctk.CTkFrame(rf, fg_color="transparent")
        dep_var = ctk.StringVar(value="无")
        dep_menu_widget = [None]

        def update_dep_menu():
            opts = ["无"] + [f"任务{t.task_id}" for t in self.keyboard_tasks if t.task_id != task.task_id]
            if dep_var.get() not in opts:
                dep_var.set("无")
            if dep_menu_widget[0]:
                dep_menu_widget[0].destroy()
            dep_menu_widget[0] = ctk.CTkOptionMenu(dep_frame, variable=dep_var, values=opts,
                                                                font=FONT_M, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                                                                button_color=Colors.DIM, width=58, height=25)
            dep_menu_widget[0].pack(side="left")

        self._rel_frames = getattr(self, '_rel_frames', {})
        self._rel_frames[task.task_id] = (rel_var, dep_frame, dep_var, update_dep_menu)

        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=11, pady=(5, 11))
        st_lbl = ctk.CTkLabel(bf, text=task.status.value, font=FONT_M, text_color=Colors.DIM)
        st_lbl.pack(side="left")
        go_btn = ctk.CTkButton(bf, text="▶ 开始", font=FONT_B, fg_color=Colors.GREEN,
                               text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, width=79, height=27,
                               command=lambda: self._toggle_task(task, go_btn, st_lbl))
        go_btn.pack(side="right")
        task._go_btn = go_btn
        task._st_lbl = st_lbl
        del_btn = ctk.CTkButton(bf, text="✕", width=22, height=22, fg_color="transparent",
                                text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B,
                                command=lambda: self._del_task(task, card))
        del_btn.pack(side="right", padx=(0, 5))
        self._check_interval_btn(task)
        self.after(150, self._auto_size)

    def _on_rel_change(self, value, task, parent_frame, rel_var):
        """任务关系切换时更新UI"""
        task.relation_type = rel_var.get()
        if hasattr(task, '_loop_label'):
            task._loop_label.configure(text="延时:" if value == "在任务x后" else "循环:")
        frame_info = self._rel_frames.get(task.task_id)
        if frame_info:
            dep_frame, dep_var, update_fn = frame_info[1], frame_info[2], frame_info[3]
            if value == "在任务x后":
                update_fn()
                dep_frame.pack(side="left", padx=(6, 0))
                # 延时默认10秒，步进1秒
                task.loop_interval = 10
                self._spin_step(task, 0)
                if hasattr(task, '_loop_frame'):
                    for child in task._loop_frame.winfo_children():
                        if isinstance(child, ctk.CTkButton):
                            txt = child.cget("text")
                            cmd = (lambda: self._spin_step(task, -1)) if txt == "◀" else \
                                  (lambda: self._spin_step(task, 1)) if txt == "▶" else None
                            if cmd: child.configure(command=cmd)
                # 从dep_var读取前置任务ID
                dep_str = dep_var.get()
                if dep_str.startswith("任务"):
                    try: task.dependency_task_id = int(dep_str[2:])
                    except: task.dependency_task_id = None
            else:
                dep_frame.pack_forget()
                task.dependency_task_id = None
                # 恢复循环步进为5
                if hasattr(task, '_loop_frame'):
                    for child in task._loop_frame.winfo_children():
                        if isinstance(child, ctk.CTkButton):
                            txt = child.cget("text")
                            cmd = (lambda: self._spin_step(task, -5)) if txt == "◀" else \
                                  (lambda: self._spin_step(task, 5)) if txt == "▶" else None
                            if cmd: child.configure(command=cmd)

    def _toggle_task(self, task, btn, lbl):
        if task._running or getattr(task, '_countdown_active', False):
            # 停止任务或取消倒计时
            task._countdown_active = False
            task.stop()
            btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
            lbl.configure(text=f"已完成 {task.done_count} 次", text_color=Colors.DIM)
            self._update_all_btn()
        else:
            # 从下拉菜单读取前置任务ID
            if task.relation_type == "在任务x后":
                frame_info = self._rel_frames.get(task.task_id)
                if frame_info:
                    dep_str = frame_info[2].get()
                    if dep_str.startswith("任务"):
                        try: task.dependency_task_id = int(dep_str[2:])
                        except: task.dependency_task_id = None
                    else:
                        task.dependency_task_id = None
            # 更新依赖关系
            self._update_dependencies()
            trigger = task.relation_type == "在任务x后"
            if trigger:
                # 依赖任务：设回调，start只设run=True不启动线程
                task._callback = lambda: self.after(0, lambda: lbl.configure(
                    text=f"已完成 {task.done_count} 次", text_color=Colors.GREEN))
                task._countdown_callback = lambda t, c: self.after(0, lambda t=t, c=c: lbl.configure(text=t, text_color=c))
                task.start()
                btn.configure(text="■ 停止", fg_color=Colors.RED)
                lbl.configure(text="● 等待前置任务", text_color=Colors.YELLOW)
                self._update_all_btn()
            else:
                # 独立任务：3秒倒计时准备期
                btn.configure(text="■ 停止", fg_color=Colors.RED)
                task._countdown_active = True
                def do_countdown():
                    for i in range(3, 0, -1):
                        if not task._countdown_active: return
                        self.after(0, lambda t=i: lbl.configure(
                            text=f"● 准备中 {t}...", text_color=Colors.YELLOW))
                        time.sleep(1)
                    if not task._countdown_active: return
                    task._countdown_active = False
                    task._countdown_callback = lambda t, c: self.after(0, lambda t=t, c=c: lbl.configure(text=t, text_color=c))
                    task.start(callback=lambda: self.after(0, lambda: lbl.configure(
                        text=f"已完成 {task.done_count} 次", text_color=Colors.GREEN)),
                        countdown_callback=task._countdown_callback)
                    self.after(0, lambda: lbl.configure(
                        text=task.status.value, text_color=Colors.GREEN))
                    self.after(0, self._update_all_btn)
                threading.Thread(target=do_countdown, daemon=True).start()

    def _update_dependencies(self):
        for t in self.keyboard_tasks: t._dependents.clear()
        for t in self.keyboard_tasks:
            if t.relation_type == "在任务x后" and t.dependency_task_id is not None:
                frame_info = self._rel_frames.get(t.task_id)
                if frame_info:
                    dep_var = frame_info[2]
                    dep_str = dep_var.get()
                    if dep_str.startswith("任务"):
                        try:
                            dep_id = int(dep_str[2:])
                            t.dependency_task_id = dep_id
                            for parent in self.keyboard_tasks:
                                if parent.task_id == dep_id:
                                    parent._dependents.append(t)
                                    break
                        except:
                            t.dependency_task_id = None

    def _del_task(self, task, card):
        task.stop(); self.keyboard_tasks.remove(task); card.destroy()
        self.after(150, self._auto_size)
        self._update_all_btn()

    def _make_spinbox(self, parent, var, lo, hi, step, task, attr, integer=False, on_change=None):
        def _set(v):
            v = round(v, 0) if integer else round(v, 2)
            v = max(lo, min(hi, v))
            var.set(v); setattr(task, attr, v)
            entry.delete(0, "end"); entry.insert(0, str(v))
            if on_change: on_change(v)
        c = ctk.CTkFrame(parent, fg_color=Colors.ACCENT, corner_radius=8)
        c.pack(side="left")
        ctk.CTkButton(c, text="◀", width=17, height=25, font=FONT_M, fg_color="transparent",
                      text_color=Colors.TEXT, hover_color=Colors.BLUE, command=lambda: _set(var.get() - step)).pack(side="left")
        entry = ctk.CTkEntry(c, font=FONT_B, fg_color="transparent", text_color=Colors.TEXT,
                             border_width=0, width=47, height=25, justify="center")
        entry.insert(0, str(var.get())); entry.pack(side="left")
        ctk.CTkButton(c, text="▶", width=17, height=25, font=FONT_M, fg_color="transparent",
                      text_color=Colors.TEXT, hover_color=Colors.BLUE, command=lambda: _set(var.get() + step)).pack(side="left")
        def on_enter(e):
            try: _set(float(entry.get()))
            except: entry.delete(0, "end"); entry.insert(0, str(var.get()))
        entry.bind("<Return>", on_enter); entry.bind("<FocusOut>", on_enter)
        return c

    def _stop_all(self):
        for t in self.keyboard_tasks:
            t.stop()
            if hasattr(t, '_go_btn'):
                t._go_btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
            if hasattr(t, '_st_lbl'):
                t._st_lbl.configure(text=f"已完成 {t.done_count} 次", text_color=Colors.DIM)
        self._update_all_btn()

    def _start_all(self):
        """启动所有可启动的独立任务"""
        for t in self.keyboard_tasks:
            if not t._running and t.relation_type == "独立" and t.key_interval > 0:
                # 复制 _toggle_task 的启动逻辑
                self._update_dependencies()
                t._callback = lambda: None
                t._countdown_callback = lambda t, c: None
                
                def do_start(task=task):
                    time.sleep(3)  # 3秒倒计时
                    if task._running:  # 如果还没被取消
                        task.start(callback=lambda: None)
                
                t._go_btn.configure(text="■ 停止", fg_color=Colors.RED)
                t._st_lbl.configure(text="● 准备中...", text_color=Colors.YELLOW)
                t._running = True  # 标记为准备中
                threading.Thread(target=do_start, daemon=True).start()
        self._update_all_btn()

    def _toggle_all(self):
        """全部开始/全部停止切换"""
        running_count = sum(1 for t in self.keyboard_tasks if t._running)
        if running_count > 0:
            self._stop_all()
        else:
            self._start_all()

    def _update_all_btn(self):
        """根据任务状态更新全部按钮"""
        if not hasattr(self, '_all_btn') or not self._all_btn:
            return
        running_count = sum(1 for t in self.keyboard_tasks if t._running)
        if running_count > 0:
            self._all_btn.configure(text="■ 全部停止", fg_color=Colors.RED,
                                    hover_color=Colors.HOVER_RED)
        else:
            self._all_btn.configure(text="▶ 全部开始", fg_color=Colors.GREEN,
                                    hover_color=Colors.HOVER_GREEN)
        # 同步迷你模式按钮
        self._update_mini_btn()
    def _check_interval_btn(self, task):
        """间隔为0时禁用开始按钮"""
        if hasattr(task, '_go_btn'):
            if task.key_interval <= 0:
                task._go_btn.configure(state="disabled", fg_color=Colors.DIM)
            else:
                task._go_btn.configure(state="normal", fg_color=Colors.GREEN)
    def _spin_step(self, task, step):
        """步进调整延时/循环值并更新entry显示"""
        v = max(0, min(999, task.loop_interval + step))
        task.loop_interval = v
        if hasattr(task, '_loop_var'):
            task._loop_var.set(v)
        if hasattr(task, '_loop_frame'):
            for child in task._loop_frame.winfo_children():
                if isinstance(child, ctk.CTkEntry):
                    child.delete(0, "end")
                    child.insert(0, str(v))
    def _capture_key(self, task, lbl):
        if getattr(task, '_capturing', False):
            task._capturing = False
            time.sleep(0.05)
        task._capturing = True
        lbl.configure(text="按下任意键...", text_color=Colors.YELLOW)
        self.focus_set()
        def listen():
            u32 = ctypes.windll.user32
            for vk in range(0x08, 0x100):
                u32.GetAsyncKeyState(vk)
            time.sleep(0.15)
            while task._capturing:
                for vk in range(0x08, 0x100):
                    if not task._capturing:
                        return
                    if u32.GetAsyncKeyState(vk) & 0x0001:
                        task.key_sequence.append(vk)
                        self.after(0, lambda: lbl.configure(
                            text=f"键位: {self._fmt_keys(task.key_sequence)}"))
                        task._capturing = False
                        return
                time.sleep(0.01)
        threading.Thread(target=listen, daemon=True).start()

    def _rm_key(self, task, lbl):
        if task.key_sequence:
            task.key_sequence.pop()
            lbl.configure(text=f"键位: {self._fmt_keys(task.key_sequence)}")

    def _clr_keys(self, task, lbl):
        task.key_sequence.clear(); lbl.configure(text="键位: (空)")

    def _save_preset_dialog(self):
        """保存当前任务为预设"""        
        dialog = ctk.CTkToplevel(self)
        dialog.overrideredirect(True)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=Colors.ACCENT)
        dialog.geometry(f"260x140+{self.winfo_x()+40}+{self.winfo_y()+100}")
        dialog.attributes("-alpha", self._settings.get("opacity", 1.0))
        ctk.CTkLabel(dialog, text="💾 保存预设", font=FONT_B, text_color=Colors.TEXT).pack(pady=(11, 5))
        entry = ctk.CTkEntry(dialog, font=FONT_M, fg_color=Colors.CARD, text_color=Colors.TEXT,
                             border_width=0, width=200, height=30, placeholder_text="输入预设名称")
        entry.pack(padx=11, pady=5)
        entry.focus_set()
        presets = load_presets()
        entry.insert(0, f"预设{len(presets)+1}")
        bf = ctk.CTkFrame(dialog, fg_color="transparent")
        bf.pack(fill="x", padx=11, pady=(5, 11))
        def do_save():
            name = entry.get().strip()
            if not name: return
            tasks_data = []
            for t in self.keyboard_tasks:
                tasks_data.append({
                    "name": t.name, "key_sequence": list(t.key_sequence),
                    "key_interval": t.key_interval, "loop_interval": t.loop_interval,
                    "relation_type": t.relation_type,
                })
            presets[name] = tasks_data
            save_presets(presets)
            self._refresh_preset_menu()
            dialog.destroy()
        ctk.CTkButton(bf, text="保存", font=FONT_B, fg_color=Colors.GREEN,
                      text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=30,
                      command=do_save).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ctk.CTkButton(bf, text="取消", font=FONT_B, fg_color=Colors.DIM,
                      text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=30,
                      command=dialog.destroy).pack(side="right", expand=True, fill="x", padx=(3, 0))
        entry.bind("<Return>", lambda e: do_save())

    def _load_preset(self):
        """加载选中的预设，追加到当前任务列表"""        
        name = self._preset_var.get()
        if name == "无预设": return
        presets = load_presets()
        if name not in presets: return
        tasks_data = presets[name]
        # 从预设创建任务，追加到现有列表
        for td in tasks_data:
            task = KeyboardTask(self.next_task_id, td["name"], list(td["key_sequence"]),
                                td["key_interval"], td["loop_interval"],
                                relation_type=td.get("relation_type", "独立"))
            self.next_task_id += 1
            self.keyboard_tasks.append(task)
            self._create_card(task)
        self.after(150, self._auto_size)

    def _delete_preset(self):
        """删除选中的预设"""
        name = self._preset_var.get()
        if name == "无预设": return
        presets = load_presets()
        if name in presets:
            del presets[name]
            save_presets(presets)
            self._refresh_preset_menu()

    def _refresh_preset_menu(self):
        """刷新预设下拉菜单"""
        presets = load_presets()
        preset_names = list(presets.keys()) if presets else ["无预设"]
        self._preset_menu.configure(values=preset_names)
        self._preset_var.set(preset_names[0])

    def _fmt_keys(self, keys):
        if not keys: return "(空)"
        return " → ".join(VK_NAME.get(vk, f"[{vk}]") for vk in keys)

    def _build_mouse_mode(self):
        # 左右并排容器
        row = ctk.CTkFrame(self.mouse_frame, fg_color="transparent")
        row.pack(fill="x", pady=4)
        row.grid_columnconfigure(0, weight=1, uniform="half")
        row.grid_columnconfigure(1, weight=1, uniform="half")

        # 左：记录位置
        pf = ctk.CTkFrame(row, fg_color=Colors.CARD, corner_radius=12)
        pf.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ph = ctk.CTkFrame(pf, fg_color="transparent")
        ph.pack(fill="x", padx=7, pady=(7, 2))
        ctk.CTkLabel(ph, text="📍 记录位置", font=FONT_B, text_color=Colors.TEXT).pack(side="left")
        ctk.CTkButton(ph, text="记录", font=FONT_B, fg_color=Colors.BLUE, text_color=Colors.TEXT, hover_color=Colors.ACCENT,
                      height=23, width=40, command=self._rec_pos).pack(side="right")
        self.pos_lbl = ctk.CTkLabel(pf, text="位置: 未记录", font=FONT_B, text_color=Colors.DIM)
        self.pos_lbl.pack(padx=7, pady=(0, 7), anchor="w")

        # 右：点击间隔
        itf = ctk.CTkFrame(row, fg_color=Colors.CARD, corner_radius=12)
        itf.grid(row=0, column=1, sticky="ew", padx=(2, 0))
        ctk.CTkLabel(itf, text="⏱ 点击间隔", font=FONT_B, text_color=Colors.TEXT).pack(padx=8, pady=(8, 4), anchor="w")
        ii = ctk.CTkFrame(itf, fg_color="transparent")
        ii.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(ii, text="毫秒:", font=FONT_M, text_color=Colors.TEXT2).pack(side="left")
        self.ms_iv = ctk.StringVar(value="1000")
        ctk.CTkEntry(ii, font=FONT_B, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                     border_width=0, width=54, height=25, textvariable=self.ms_iv).pack(side="left", padx=6)

        bf = ctk.CTkFrame(self.mouse_frame, fg_color="transparent", height=43)
        bf.pack(fill="x", pady=(4, 0)); bf.pack_propagate(False)
        self.ms_btn = ctk.CTkButton(bf, text="▶ 开始", font=FONT_B,
                                    fg_color=Colors.GREEN, text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=36,
                                    command=self._toggle_ms)
        self.ms_btn.pack(fill="x", padx=11)
        self.ms_st = ctk.CTkLabel(self.mouse_frame, text=TaskStatus.IDLE.value,
                                  font=FONT_M, text_color=Colors.DIM)
        self.ms_st.pack(pady=4)

    def _build_settings_mode(self):
        s = load_settings()
        # ── 透明度 ──
        sf2 = ctk.CTkFrame(self.settings_frame, fg_color=Colors.CARD, corner_radius=11)
        sf2.pack(fill="x", padx=11, pady=5)
        ctk.CTkLabel(sf2, text="👁 窗口透明度", font=FONT_B, text_color=Colors.TEXT).pack(padx=11, pady=(11, 4), anchor="w")
        row2 = ctk.CTkFrame(sf2, fg_color="transparent")
        row2.pack(fill="x", padx=11, pady=(0, 11))
        self._opacity_var = ctk.DoubleVar(value=s["opacity"])
        self._opacity_lbl = ctk.CTkLabel(row2, text=f"{s['opacity']:.0%}", font=FONT_M, text_color=Colors.TEXT2, width=45)
        self._opacity_lbl.pack(side="right")
        opacity_slider = ctk.CTkSlider(row2, from_=0.3, to=1.0, number_of_steps=14,
                                       variable=self._opacity_var, width=180,
                                       command=lambda v: self._on_opacity_change(v))
        opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        # ── 主题 ──
        sf3 = ctk.CTkFrame(self.settings_frame, fg_color=Colors.CARD, corner_radius=11)
        sf3.pack(fill="x", padx=11, pady=5)
        ctk.CTkLabel(sf3, text="🎨 色彩主题", font=FONT_B, text_color=Colors.TEXT).pack(padx=11, pady=(11, 6), anchor="w")
        themes_row = ctk.CTkFrame(sf3, fg_color="transparent")
        themes_row.pack(fill="x", padx=11, pady=(0, 6))
        self._theme_var = ctk.StringVar(value=s["theme"])
        for i, name in enumerate(THEMES.keys()):
            t = THEMES[name]
            btn = ctk.CTkButton(themes_row, text=name, font=FONT_M, height=28,
                                fg_color=t["CARD"], hover_color=t["ACCENT"],
                                text_color=t["TEXT"], width=58,
                                command=lambda n=name: self._on_theme_change(n))
            btn.grid(row=i//3, column=i%3, padx=3, pady=3, sticky="ew")
        themes_row.grid_columnconfigure((0, 1, 2), weight=1)
        # ── 主题预览 ──
        self._preview_frame = ctk.CTkFrame(sf3, fg_color="transparent")
        self._preview_frame.pack(fill="x", padx=11, pady=(0, 11))
        self._update_preview(s["theme"])
        # ── 应用按钮 ──
        bf = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        bf.pack(fill="x", padx=11, pady=2)
        ctk.CTkButton(bf, text="✓ 应用", font=("MiSans", 16, "bold"), fg_color=Colors.GREEN,
                      text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=48,
                      command=self._apply_settings).pack(fill="x")

    def _on_opacity_change(self, v):
        self._opacity_lbl.configure(text=f"{v:.0%}")
        self.attributes("-alpha", v)
        # 实时保存透明度
        s = load_settings(); s["opacity"] = v; save_settings(s)

    def _on_theme_change(self, name):
        """点击主题按钮 → 只更新预览"""
        self._theme_var.set(name)
        self._update_preview(name)

    def _apply_settings(self):
        """保存设置 + 重启"""
        save_settings({
            "opacity": self._opacity_var.get(),
            "theme": self._theme_var.get(),
        })
        import subprocess, sys, os
        script = os.path.abspath(sys.argv[0])
        subprocess.Popen([sys.executable, script])
        self.destroy()

    def _update_preview(self, theme_name):
        """更新主题预览区"""
        t = THEMES.get(theme_name, {})
        if not t or not hasattr(self, '_preview_frame'):
            return
        for w in self._preview_frame.winfo_children():
            w.destroy()
        # 预览条：背景色 + 文字色
        bar = ctk.CTkFrame(self._preview_frame, fg_color=t["CARD"], corner_radius=8, height=50)
        bar.pack(fill="x", pady=(0, 4))
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="主文字", font=FONT_B, text_color=t["TEXT"]).pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(bar, text="次要文字", font=FONT_M, text_color=t["TEXT2"]).pack(side="left", padx=4, pady=8)
        ctk.CTkLabel(bar, text="弱化文字", font=FONT_M, text_color=t["DIM"]).pack(side="left", padx=4, pady=8)
        # 功能色条
        colors_bar = ctk.CTkFrame(self._preview_frame, fg_color="transparent")
        colors_bar.pack(fill="x")
        for label, color in [("主色", t["BLUE"]), ("成功", t["GREEN"]), ("危险", t["RED"]), ("警告", t["YELLOW"])]:
            ctk.CTkFrame(colors_bar, fg_color=color, corner_radius=4, height=20).pack(side="left", fill="x", expand=True, padx=2)
        # 提示
        ctk.CTkLabel(self._preview_frame, text="选择后点「✓ 应用」重启生效",
                      font=("MiSans", 10), text_color=Colors.DIM).pack(pady=(4, 0))

    def _rebuild_ui(self):
        """销毁并重建整个 UI（主题/透明度变更后调用）"""
        # 1. 保存任务数据
        tasks_data = []
        for t in self.keyboard_tasks:
            tasks_data.append({
                "name": t.name, "key_sequence": list(t.key_sequence),
                "key_interval": t.key_interval, "loop_interval": t.loop_interval,
                "relation_type": t.relation_type, "dependency_task_id": t.dependency_task_id,
            })
        # 2. 同步销毁所有子控件
        for w in self.winfo_children():
            w.destroy()
        # 3. 重置状态（Colors 已经在调用者中 apply 了）
        self.keyboard_tasks = []
        self.next_task_id = 1
        self._rel_frames = {}
        self.configure(fg_color=Colors.ACCENT)
        # 4. 同步重建（此时 Colors 已经是新主题的值）
        self._build_ui()
        # 5. 恢复任务
        for td in tasks_data:
            task = KeyboardTask(self.next_task_id, td["name"], td["key_sequence"],
                                td["key_interval"], td["loop_interval"],
                                relation_type=td["relation_type"],
                                dependency_task_id=td["dependency_task_id"])
            self.next_task_id += 1
            self.keyboard_tasks.append(task)
            self._create_card(task)
        # 6. 回到设置页并自适应大小
        self._show_mode("settings")
        self.update_idletasks()
        self._auto_size()

    def _rec_pos(self):
        self.withdraw()
        overlay = ctk.CTkToplevel(self)
        overlay.overrideredirect(True)
        overlay.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        overlay.configure(fg_color="#808080")
        overlay.attributes("-alpha", 0.4)
        overlay.attributes("-topmost", True)
        tip = ctk.CTkLabel(overlay, text="🎯 点击鼠标左键确认位置", font=("MiSans", 16, "bold"),
                           text_color="#ffffff", fg_color="#333333", corner_radius=8)
        tip.place(relx=0.5, rely=0.5, anchor="center")
        def wait_click():
            u32 = ctypes.windll.user32
            time.sleep(0.3)
            while u32.GetAsyncKeyState(0x01) & 0x8000:
                time.sleep(0.01)
            while not (u32.GetAsyncKeyState(0x01) & 0x8000):
                time.sleep(0.01)
            self.mouse_task.position = InputSimulator().get_mouse_pos()
            self.after(0, overlay.destroy)
            self.after(0, lambda: self.pos_lbl.configure(
                text=f"位置: {self.mouse_task.position}", text_color=Colors.GREEN))
            self.after(0, lambda: self.ms_st.configure(text="● 已记录", text_color=Colors.GREEN))
            self.after(0, self.deiconify)
        threading.Thread(target=wait_click, daemon=True).start()

    def _toggle_ms(self):
        if self.ms_btn.cget("text") == "■ 停止":
            # 无论是正在运行还是已被安全停止，都重置UI
            self.mouse_task.stop()
            self.ms_btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
            self.ms_st.configure(text=f"● 已停止 | {self.mouse_task.done_count} 次", text_color=Colors.DIM)
        else:
            try: self.mouse_task.interval = int(self.ms_iv.get()) / 1000
            except: self.mouse_task.interval = 1.0
            self.mouse_task.start(callback=lambda msg: self.after(0, lambda: self._on_ms_stopped(msg)))
            self.ms_btn.configure(text="■ 停止", fg_color=Colors.RED)
            self.ms_st.configure(text="● 连点中", text_color=Colors.GREEN)

    def _on_ms_stopped(self, msg):
        """鼠标任务停止回调（安全停止或手动停止）"""
        self.ms_btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
        self.ms_st.configure(text=f"● {msg} | {self.mouse_task.done_count} 次",
                             text_color=Colors.YELLOW if msg == "安全停止" else Colors.DIM)

    # ─── 迷你模式 ───
    def _minimize_to_mini(self):
        """最小化到迷你模式"""
        if self._mini_window:
            return
        # 保存当前位置
        self._main_pos = (self.winfo_x(), self.winfo_y())
        self.withdraw()  # 隐藏主窗口
        self._build_mini_mode()

    def _build_mini_mode(self):
        """构建迷你模式窗口"""
        s = load_settings()
        # 读取保存的位置，没有则用默认
        x = s.get("mini_pos_x", self._main_pos[0])
        y = s.get("mini_pos_y", self._main_pos[1])
        
        self._mini_window = ctk.CTkToplevel(self)
        self._mini_window.overrideredirect(True)
        self._mini_window.attributes("-topmost", True)
        self._mini_window.configure(fg_color=Colors.ACCENT)
        if self._settings["opacity"] < 1.0:
            self._mini_window.attributes("-alpha", self._settings["opacity"])
        self._mini_window.geometry(f"250x100+{x}+{y}")
        
        # 标题栏
        bar = ctk.CTkFrame(self._mini_window, height=32, fg_color=Colors.CARD, corner_radius=0)
        bar.pack(fill="x"); bar.pack_propagate(False)
        
        # 拖动
        drag_data = {"x": 0, "y": 0}
        def start_drag(e):
            drag_data["x"] = e.x
            drag_data["y"] = e.y
        def do_drag(e):
            new_x = self._mini_window.winfo_x() + e.x - drag_data["x"]
            new_y = self._mini_window.winfo_y() + e.y - drag_data["y"]
            self._mini_window.geometry(f"+{new_x}+{new_y}")
        def end_drag(e):
            # 保存位置
            s = load_settings()
            s["mini_pos_x"] = self._mini_window.winfo_x()
            s["mini_pos_y"] = self._mini_window.winfo_y()
            save_settings(s)
        
        bar.bind("<Button-1>", start_drag)
        bar.bind("<B1-Motion>", do_drag)
        bar.bind("<ButtonRelease-1>", end_drag)
        
        ctk.CTkLabel(bar, text="⚡ 轻松AI", font=FONT_B, text_color=Colors.TEXT).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="✕", width=22, height=22, fg_color="transparent",
                      text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B,
                      command=self.quit_app).pack(side="right", padx=6)
        
        # 按钮区
        btn_frame = ctk.CTkFrame(self._mini_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=(8, 4))
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self._mini_restore_btn = ctk.CTkButton(
            btn_frame, text="取消最小化", font=FONT_B, fg_color=Colors.BLUE,
            text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=32,
            command=self._restore_from_mini)
        self._mini_restore_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        
        self._mini_all_btn = ctk.CTkButton(
            btn_frame, text="▶ 全部开始", font=FONT_B, fg_color=Colors.GREEN,
            text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=32,
            command=self._toggle_all)
        self._mini_all_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        
        # 状态显示
        self._mini_status = ctk.CTkLabel(
            self._mini_window, text="● 就绪", font=FONT_M, text_color=Colors.DIM)
        self._mini_status.pack(pady=(0, 6))
        
        # 启动状态更新
        self._update_mini_status()

    def _restore_from_mini(self):
        """从迷你模式恢复"""
        if not self._mini_window:
            return
        # 保存迷你窗口位置
        s = load_settings()
        s["mini_pos_x"] = self._mini_window.winfo_x()
        s["mini_pos_y"] = self._mini_window.winfo_y()
        save_settings(s)
        
        # 获取迷你窗口位置
        mini_x = self._mini_window.winfo_x()
        mini_y = self._mini_window.winfo_y()
        
        # 销毁迷你窗口
        self._mini_window.destroy()
        self._mini_window = None
        
        # 恢复主窗口
        self.deiconify()
        self.geometry(f"+{mini_x}+{mini_y}")
        self.lift()

    def _mini_stop_all(self):
        """迷你模式下停止所有任务"""
        self._stop_all()
        if self.mouse_task._running:
            self.mouse_task.stop()
        self._update_mini_status()

    def _update_mini_btn(self):
        """同步迷你模式的全部按钮状态"""
        if not hasattr(self, '_mini_all_btn') or not self._mini_all_btn:
            return
        running_count = sum(1 for t in self.keyboard_tasks if t._running)
        if running_count > 0:
            self._mini_all_btn.configure(text="■ 全部停止", fg_color=Colors.RED,
                                         hover_color=Colors.HOVER_RED)
        else:
            self._mini_all_btn.configure(text="▶ 全部开始", fg_color=Colors.GREEN,
                                         hover_color=Colors.HOVER_GREEN)

    def _update_mini_status(self):
        """更新迷你窗口状态显示"""
        if not self._mini_window:
            return
        
        running_count = sum(1 for t in self.keyboard_tasks if t._running)
        total_count = len(self.keyboard_tasks)
        
        if running_count > 0:
            text = f"● 运行中 {running_count}/{total_count}"
            color = Colors.GREEN
        elif total_count > 0:
            text = f"● 已停止 {total_count} 个任务"
            color = Colors.DIM
        else:
            text = "● 就绪"
            color = Colors.DIM
        
        if hasattr(self, '_mini_status') and self._mini_status:
            self._mini_status.configure(text=text, text_color=color)
        
        # 每秒更新一次
        if self._mini_window:
            self._mini_window.after(1000, self._update_mini_status)

    def quit_app(self):
        try: self._stop_all()
        except: pass
        try:
            if self.mouse_task._running: self.mouse_task.stop()
        except: pass
        self.destroy()

def ensure_admin():
    """如果不是管理员权限，自动以管理员身份重启"""
    import sys, os
    if sys.platform != "win32": return
    if ctypes.windll.shell32.IsUserAnAdmin(): return
    # 以管理员权限重新启动（用 pythonw 避免弹控制台）
    script = os.path.abspath(sys.argv[0])
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable  # 回退到 python.exe
    ctypes.windll.shell32.ShellExecuteW(None, "runas", pythonw, f'"{script}"', None, 0)
    sys.exit(0)

if __name__ == "__main__":
    import sys
    if sys.platform != "win32": sys.exit("仅支持 Windows")
    ensure_admin()
    App().mainloop()
