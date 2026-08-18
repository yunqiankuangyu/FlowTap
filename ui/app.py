"""
主窗口
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk

from config import Colors, FONT_B, FONT_M, load_settings, save_settings
from tasks import KeyboardTask, MouseTask

# 伪装标题
DISGUISE_TITLE = "svchost"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        # 加载设置并应用主题
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
        
        self.keyboard_tasks = []
        self.mouse_task = MouseTask()
        self.next_task_id = 1
        self._current_mode = "keyboard"
        self._mini_window = None
        
        self.bind("<Button-1>", self._on_global_click)
        self._build_ui()

    def _on_global_click(self, event):
        w = event.widget
        while w and not isinstance(w, ctk.CTkEntry):
            w = w.master
        if not w: self.focus_set()

    def _build_ui(self):
        from .titlebar import build_titlebar
        from .keyboard_mode import build_keyboard_mode, auto_size
        from .mouse_mode import build_mouse_mode
        from .settings_mode import build_settings_mode
        
        build_titlebar(self)
        
        # 模式切换标签
        tab = ctk.CTkFrame(self, height=43, fg_color=Colors.CARD, corner_radius=0)
        tab.pack(fill="x"); tab.pack_propagate(False)
        self.tab_kb = ctk.CTkButton(tab, text="⌨ 键盘", font=FONT_B, fg_color=Colors.BLUE,
                                    text_color=Colors.TEXT, hover_color=Colors.ACCENT, 
                                    command=lambda: self._show_mode("keyboard"))
        self.tab_kb.pack(side="left", fill="both", expand=True, padx=(2, 1), pady=4)
        self.tab_ms = ctk.CTkButton(tab, text="🖱 鼠标", font=FONT_B, fg_color=Colors.CARD,
                                    text_color=Colors.TEXT, hover_color=Colors.ACCENT, 
                                    command=lambda: self._show_mode("mouse"))
        self.tab_ms.pack(side="right", fill="both", expand=True, padx=(1, 2), pady=4)
        
        # 内容区域
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.keyboard_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.mouse_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        
        build_keyboard_mode(self)
        build_mouse_mode(self)
        build_settings_mode(self)
        
        self._show_mode("keyboard")

    def _show_mode(self, mode):
        self.keyboard_frame.pack_forget()
        self.mouse_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.content_frame.pack_forget()
        
        if mode == "keyboard":
            self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            self.keyboard_frame.pack(fill="both", expand=True)
            self.tab_kb.configure(fg_color=Colors.BLUE)
            self.tab_ms.configure(fg_color=Colors.CARD)
            self.after(150, lambda: self._auto_size())
        elif mode == "mouse":
            self.content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            self.mouse_frame.pack(fill="both", expand=True)
            self.tab_kb.configure(fg_color=Colors.CARD)
            self.tab_ms.configure(fg_color=Colors.BLUE)
            self.after(150, lambda: self._auto_size())
        elif mode == "settings":
            self.content_frame.pack(fill="x", padx=5, pady=(0, 5))
            self.settings_frame.pack(fill="x")
            self.tab_kb.configure(fg_color=Colors.CARD)
            self.tab_ms.configure(fg_color=Colors.CARD)
            self.geometry("346x540")

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

    def quit_app(self):
        try:
            from .keyboard_mode import stop_all
            stop_all(self)
        except: pass
        try:
            if self.mouse_task._running: self.mouse_task.stop()
        except: pass
        self.destroy()

    # ── 键盘模式代理方法 ──
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
