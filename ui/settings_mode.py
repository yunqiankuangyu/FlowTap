"""
设置页面
"""
import customtkinter as ctk
import subprocess
import sys
import os

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Colors, FONT_B, FONT_M, THEMES, DEFAULT_THEME, load_settings, save_settings


def build_settings_mode(app):
    """构建设置页面"""
    s = load_settings()
    # ── 透明度 ──
    sf2 = ctk.CTkFrame(app.settings_frame, fg_color=Colors.CARD, corner_radius=11)
    sf2.pack(fill="x", padx=11, pady=5)
    ctk.CTkLabel(sf2, text="👁 窗口透明度", font=FONT_B, text_color=Colors.TEXT).pack(padx=11, pady=(11, 4), anchor="w")
    row2 = ctk.CTkFrame(sf2, fg_color="transparent")
    row2.pack(fill="x", padx=11, pady=(0, 11))
    app._opacity_var = ctk.DoubleVar(value=s["opacity"])
    app._opacity_lbl = ctk.CTkLabel(row2, text=f"{s['opacity']:.0%}", font=FONT_M, text_color=Colors.TEXT2, width=45)
    app._opacity_lbl.pack(side="right")
    opacity_slider = ctk.CTkSlider(row2, from_=0.3, to=1.0, number_of_steps=14,
                                   variable=app._opacity_var, width=180,
                                   command=lambda v: on_opacity_change(app, v))
    opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
    # ── 主题 ──
    sf3 = ctk.CTkFrame(app.settings_frame, fg_color=Colors.CARD, corner_radius=11)
    sf3.pack(fill="x", padx=11, pady=5)
    ctk.CTkLabel(sf3, text="🎨 色彩主题", font=FONT_B, text_color=Colors.TEXT).pack(padx=11, pady=(11, 6), anchor="w")
    themes_row = ctk.CTkFrame(sf3, fg_color="transparent")
    themes_row.pack(fill="x", padx=11, pady=(0, 6))
    app._theme_var = ctk.StringVar(value=s["theme"])
    for i, name in enumerate(THEMES.keys()):
        t = THEMES[name]
        btn = ctk.CTkButton(themes_row, text=name, font=FONT_M, height=28,
                            fg_color=t["CARD"], hover_color=t["ACCENT"],
                            text_color=t["TEXT"], width=58,
                            command=lambda n=name: on_theme_change(app, n))
        btn.grid(row=i//3, column=i%3, padx=3, pady=3, sticky="ew")
    themes_row.grid_columnconfigure((0, 1, 2), weight=1)
    # ── 主题预览 ──
    app._preview_frame = ctk.CTkFrame(sf3, fg_color="transparent")
    app._preview_frame.pack(fill="x", padx=11, pady=(0, 11))
    update_preview(app, s["theme"])
    # ── 应用按钮 ──
    bf = ctk.CTkFrame(app.settings_frame, fg_color="transparent")
    bf.pack(fill="x", padx=11, pady=2)
    ctk.CTkButton(bf, text="✓ 应用", font=("MiSans", 16, "bold"), fg_color=Colors.GREEN,
                  text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=48,
                  command=lambda: apply_settings(app)).pack(fill="x")


def on_opacity_change(app, v):
    """透明度变化"""
    app._opacity_lbl.configure(text=f"{v:.0%}")
    app.attributes("-alpha", v)
    s = load_settings(); s["opacity"] = v; save_settings(s)


def on_theme_change(app, name):
    """主题预览"""
    app._theme_var.set(name)
    update_preview(app, name)


def update_preview(app, theme_name):
    """更新主题预览"""
    t = THEMES.get(theme_name, {})
    if not t or not hasattr(app, '_preview_frame'):
        return
    for w in app._preview_frame.winfo_children():
        w.destroy()
    bar = ctk.CTkFrame(app._preview_frame, fg_color=t["CARD"], corner_radius=8, height=50)
    bar.pack(fill="x", pady=(0, 4))
    bar.pack_propagate(False)
    ctk.CTkLabel(bar, text="主文字", font=FONT_B, text_color=t["TEXT"]).pack(side="left", padx=8, pady=8)
    ctk.CTkLabel(bar, text="次要文字", font=FONT_M, text_color=t["TEXT2"]).pack(side="left", padx=4, pady=8)
    ctk.CTkLabel(bar, text="弱化文字", font=FONT_M, text_color=t["DIM"]).pack(side="left", padx=4, pady=8)
    colors_bar = ctk.CTkFrame(app._preview_frame, fg_color="transparent")
    colors_bar.pack(fill="x")
    for label, color in [("主色", t["BLUE"]), ("成功", t["GREEN"]), ("危险", t["RED"]), ("警告", t["YELLOW"])]:
        ctk.CTkFrame(colors_bar, fg_color=color, corner_radius=4, height=20).pack(side="left", fill="x", expand=True, padx=2)
    ctk.CTkLabel(app._preview_frame, text="选择后点「✓ 应用」重启生效",
                  font=("MiSans", 10), text_color=Colors.DIM).pack(pady=(4, 0))


def apply_settings(app):
    """应用设置并重启"""
    save_settings({
        "opacity": app._opacity_var.get(),
        "theme": app._theme_var.get(),
    })
    script = os.path.abspath(sys.argv[0])
    subprocess.Popen([sys.executable, script])
    app.destroy()
