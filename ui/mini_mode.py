"""
迷你模式窗口
"""
import customtkinter as ctk

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Colors, FONT_B, FONT_M, load_settings, save_settings


def minimize_to_mini(app):
    """最小化到迷你模式"""
    if app._mini_window:
        return
    app._main_pos = (app.winfo_x(), app.winfo_y())
    app.withdraw()
    build_mini_mode(app)


def build_mini_mode(app):
    """构建迷你模式窗口"""
    s = load_settings()
    x = s.get("mini_pos_x", app._main_pos[0])
    y = s.get("mini_pos_y", app._main_pos[1])
    
    app._mini_window = ctk.CTkToplevel(app)
    app._mini_window.overrideredirect(True)
    app._mini_window.attributes("-topmost", True)
    app._mini_window.configure(fg_color=Colors.ACCENT)
    if app._settings["opacity"] < 1.0:
        app._mini_window.attributes("-alpha", app._settings["opacity"])
    app._mini_window.geometry(f"250x100+{x}+{y}")
    
    # 标题栏
    bar = ctk.CTkFrame(app._mini_window, height=32, fg_color=Colors.CARD, corner_radius=0)
    bar.pack(fill="x"); bar.pack_propagate(False)
    
    # 拖动
    drag_data = {"x": 0, "y": 0}
    def start_drag(e):
        drag_data["x"] = e.x
        drag_data["y"] = e.y
    def do_drag(e):
        new_x = app._mini_window.winfo_x() + e.x - drag_data["x"]
        new_y = app._mini_window.winfo_y() + e.y - drag_data["y"]
        app._mini_window.geometry(f"+{new_x}+{new_y}")
    def end_drag(e):
        s = load_settings()
        s["mini_pos_x"] = app._mini_window.winfo_x()
        s["mini_pos_y"] = app._mini_window.winfo_y()
        save_settings(s)
    
    bar.bind("<Button-1>", start_drag)
    bar.bind("<B1-Motion>", do_drag)
    bar.bind("<ButtonRelease-1>", end_drag)
    
    ctk.CTkLabel(bar, text="⚡ 轻松AI", font=FONT_B, text_color=Colors.TEXT).pack(side="left", padx=8)
    ctk.CTkButton(bar, text="✕", width=22, height=22, fg_color="transparent",
                  text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B,
                  command=app.quit_app).pack(side="right", padx=6)
    
    # 按钮区
    btn_frame = ctk.CTkFrame(app._mini_window, fg_color="transparent")
    btn_frame.pack(fill="x", padx=8, pady=(8, 4))
    btn_frame.grid_columnconfigure((0, 1), weight=1)
    
    app._mini_restore_btn = ctk.CTkButton(
        btn_frame, text="取消最小化", font=FONT_B, fg_color=Colors.BLUE,
        text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=32,
        command=lambda: restore_from_mini(app))
    app._mini_restore_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))
    
    app._mini_all_btn = ctk.CTkButton(
        btn_frame, text="▶ 全部开始", font=FONT_B, fg_color=Colors.GREEN,
        text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=32,
        command=lambda: toggle_all_from_mini(app))
    app._mini_all_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))
    
    # 状态显示
    app._mini_status = ctk.CTkLabel(
        app._mini_window, text="● 就绪", font=FONT_M, text_color=Colors.DIM)
    app._mini_status.pack(pady=(0, 6))
    
    # 启动状态更新
    update_mini_status(app)


def restore_from_mini(app):
    """从迷你模式恢复"""
    if not app._mini_window:
        return
    s = load_settings()
    s["mini_pos_x"] = app._mini_window.winfo_x()
    s["mini_pos_y"] = app._mini_window.winfo_y()
    save_settings(s)
    
    mini_x = app._mini_window.winfo_x()
    mini_y = app._mini_window.winfo_y()
    
    app._mini_window.destroy()
    app._mini_window = None
    
    app.deiconify()
    app.geometry(f"+{mini_x}+{mini_y}")
    app.lift()


def toggle_all_from_mini(app):
    """迷你模式下切换全部开始/停止"""
    from .keyboard_mode import toggle_all
    toggle_all(app)


def update_mini_status(app):
    """更新迷你窗口状态显示"""
    if not app._mini_window:
        return
    
    running_count = sum(1 for t in app.keyboard_tasks if t._running)
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
        app._mini_status.configure(text=text, text_color=color)
    
    # 每秒更新一次
    if app._mini_window:
        app._mini_window.after(1000, lambda: update_mini_status(app))


def update_mini_btn(app):
    """同步迷你模式的全部按钮状态"""
    if not hasattr(app, '_mini_all_btn') or not app._mini_all_btn:
        return
    running_count = sum(1 for t in app.keyboard_tasks if t._running)
    if running_count > 0:
        app._mini_all_btn.configure(text="■ 全部停止", fg_color=Colors.RED,
                                     hover_color=Colors.HOVER_RED)
    else:
        app._mini_all_btn.configure(text="▶ 全部开始", fg_color=Colors.GREEN,
                                     hover_color=Colors.HOVER_GREEN)
