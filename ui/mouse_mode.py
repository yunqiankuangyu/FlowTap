"""
鼠标模式页面
"""
import customtkinter as ctk
import threading
import time
import ctypes

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Colors, FONT_B, FONT_M
from tasks import MouseTask, TaskStatus
from core import MouseSimulator


def build_mouse_mode(app):
    """构建鼠标模式页面"""
    # 左右并排容器
    row = ctk.CTkFrame(app.mouse_frame, fg_color="transparent")
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
                  height=23, width=40, command=lambda: rec_pos(app)).pack(side="right")
    app.pos_lbl = ctk.CTkLabel(pf, text="位置: 未记录", font=FONT_B, text_color=Colors.DIM)
    app.pos_lbl.pack(padx=7, pady=(0, 7), anchor="w")

    # 右：点击间隔
    itf = ctk.CTkFrame(row, fg_color=Colors.CARD, corner_radius=12)
    itf.grid(row=0, column=1, sticky="ew", padx=(2, 0))
    ctk.CTkLabel(itf, text="⏱ 点击间隔", font=FONT_B, text_color=Colors.TEXT).pack(padx=8, pady=(8, 4), anchor="w")
    ii = ctk.CTkFrame(itf, fg_color="transparent")
    ii.pack(fill="x", padx=8, pady=(0, 8))
    ctk.CTkLabel(ii, text="毫秒:", font=FONT_M, text_color=Colors.TEXT2).pack(side="left")
    app.ms_iv = ctk.StringVar(value="1000")
    ctk.CTkEntry(ii, font=FONT_B, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                 border_width=0, width=54, height=25, textvariable=app.ms_iv).pack(side="left", padx=6)

    bf = ctk.CTkFrame(app.mouse_frame, fg_color="transparent", height=43)
    bf.pack(fill="x", pady=(4, 0)); bf.pack_propagate(False)
    app.ms_btn = ctk.CTkButton(bf, text="▶ 开始", font=FONT_B,
                                fg_color=Colors.GREEN, text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=36,
                                command=lambda: toggle_ms(app))
    app.ms_btn.pack(fill="x", padx=11)
    app.ms_st = ctk.CTkLabel(app.mouse_frame, text=TaskStatus.IDLE.value,
                              font=FONT_M, text_color=Colors.DIM)
    app.ms_st.pack(pady=4)


def rec_pos(app):
    """记录鼠标位置"""
    app.withdraw()
    overlay = ctk.CTkToplevel(app)
    overlay.overrideredirect(True)
    overlay.geometry(f"{app.winfo_screenwidth()}x{app.winfo_screenheight()}+0+0")
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
        app.mouse_task.position = MouseSimulator().get_mouse_pos()
        app.after(0, overlay.destroy)
        app.after(0, lambda: app.pos_lbl.configure(
            text=f"位置: {app.mouse_task.position}", text_color=Colors.GREEN))
        app.after(0, lambda: app.ms_st.configure(text="● 已记录", text_color=Colors.GREEN))
        app.after(0, app.deiconify)
    threading.Thread(target=wait_click, daemon=True).start()


def toggle_ms(app):
    """切换鼠标任务状态"""
    if app.ms_btn.cget("text") == "■ 停止":
        app.mouse_task.stop()
        app.ms_btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
        app.ms_st.configure(text=f"● 已停止 | {app.mouse_task.done_count} 次", text_color=Colors.DIM)
    else:
        try: app.mouse_task.interval = int(app.ms_iv.get()) / 1000
        except: app.mouse_task.interval = 1.0
        app.mouse_task.start(callback=lambda msg: app.after(0, lambda: on_ms_stopped(app, msg)))
        app.ms_btn.configure(text="■ 停止", fg_color=Colors.RED)
        app.ms_st.configure(text="● 连点中", text_color=Colors.GREEN)


def on_ms_stopped(app, msg):
    """鼠标任务停止回调"""
    app.ms_btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
    app.ms_st.configure(text=f"● {msg} | {app.mouse_task.done_count} 次",
                         text_color=Colors.YELLOW if msg == "安全停止" else Colors.DIM)
