"""
标题栏组件
"""
import customtkinter as ctk
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Colors, FONT_B


def build_titlebar(app):
    """构建标题栏
    
    Args:
        app: App主窗口实例，需要提供以下属性/方法:
            - _drag_data: dict, 拖动数据
            - quit_app: method, 退出应用
            - _show_mode: method, 切换页面
            - _minimize_to_mini: method, 最小化到迷你模式
    """
    bar = ctk.CTkFrame(app, height=40, width=346, fg_color=Colors.CARD, corner_radius=0)
    bar.place(x=0, y=0, relwidth=1)
    bar.configure(width=346)
    bar.pack_propagate(False)

    # 拖动支持
    app._drag_data = {"x": 0, "y": 0}
    bar.bind("<Button-1>", lambda e: app._drag_data.update({"x": e.x, "y": e.y}))
    bar.bind("<B1-Motion>", lambda e: app.geometry(
        f"+{app.winfo_x()+e.x-app._drag_data['x']}+{app.winfo_y()+e.y-app._drag_data['y']}"))

    # 标题
    ctk.CTkLabel(bar, text="⚡ 工具", font=FONT_B, text_color=Colors.TEXT).pack(side="left", padx=11)

    # 关闭按钮
    ctk.CTkButton(bar, text="✕", width=23, height=23, fg_color="transparent",
                  text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B,
                  command=app.quit_app).pack(side="right", padx=2, pady=8)

    # 设置按钮
    ctk.CTkButton(bar, text="⚙", width=23, height=23, fg_color="transparent",
                  text_color=Colors.DIM, hover_color=Colors.BLUE, font=FONT_B,
                  command=lambda: app._show_mode("settings")).pack(side="right", padx=2, pady=8)

    # 最小化按钮
    ctk.CTkButton(bar, text="—", width=23, height=23, fg_color="transparent",
                  text_color=Colors.DIM, hover_color=Colors.BLUE, font=FONT_B,
                  command=app._minimize_to_mini).pack(side="right", padx=2, pady=8)
