"""
设置页面 (PySide6) — 对齐原版 CTk 样式
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSlider, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from config import Colors, FONT_B, FONT_M, THEMES, DEFAULT_THEME, load_settings, save_settings


def build_settings_mode(app):
    """构建设置页面"""
    s = load_settings()
    layout = app.settings_layout

    # ── 透明度 ──
    sf2 = QFrame()
    sf2.setStyleSheet(f"QFrame {{ background: {Colors.CARD}; border-radius: 11px; }}")
    sf2_layout = QVBoxLayout(sf2)
    sf2_layout.setContentsMargins(11, 11, 11, 11)

    op_label = QLabel("👁 窗口透明度")
    op_label.setFont(FONT_B)
    op_label.setStyleSheet(f"color: {Colors.TEXT}; background: transparent;")
    sf2_layout.addWidget(op_label)

    op_row = QWidget()
    op_row.setStyleSheet("background: transparent;")
    op_row_layout = QHBoxLayout(op_row)
    op_row_layout.setContentsMargins(0, 0, 0, 0)

    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(30)
    slider.setMaximum(100)
    slider.setValue(int(s["opacity"] * 100))
    slider.setStyleSheet(f"""
        QSlider::groove:horizontal {{ background: {Colors.ACCENT}; height: 6px; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {Colors.BLUE}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}
        QSlider::sub-page:horizontal {{ background: {Colors.BLUE}; border-radius: 3px; }}
    """)
    app._opacity_slider = slider

    op_val = QLabel(f"{s['opacity']:.0%}")
    op_val.setFont(FONT_M)
    op_val.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
    op_val.setFixedWidth(45)
    app._opacity_lbl = op_val

    slider.valueChanged.connect(lambda v: on_opacity_change(app, v))

    op_row_layout.addWidget(slider, 1)
    op_row_layout.addWidget(op_val)
    sf2_layout.addWidget(op_row)
    layout.addWidget(sf2)

    # ── 主题 ──
    sf3 = QFrame()
    sf3.setStyleSheet(f"QFrame {{ background: {Colors.CARD}; border-radius: 11px; }}")
    sf3_layout = QVBoxLayout(sf3)
    sf3_layout.setContentsMargins(11, 11, 11, 11)

    th_label = QLabel("🎨 色彩主题")
    th_label.setFont(FONT_B)
    th_label.setStyleSheet(f"color: {Colors.TEXT}; background: transparent;")
    sf3_layout.addWidget(th_label)

    themes_grid = QWidget()
    themes_grid.setStyleSheet("background: transparent;")
    grid = QGridLayout(themes_grid)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(4)

    app._theme_buttons = {}
    app._current_theme = s["theme"]

    for i, name in enumerate(THEMES.keys()):
        t = THEMES[name]
        btn = QPushButton(name)
        btn.setFont(FONT_M)
        btn.setFixedHeight(30)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {t["CARD"]}; color: {t["TEXT"]}; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background: {t["ACCENT"]}; }}
        """)
        btn.clicked.connect(lambda checked, n=name: on_theme_change(app, n))
        app._theme_buttons[name] = btn
        grid.addWidget(btn, i // 3, i % 3)

    # 让三列等宽
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(2, 1)

    sf3_layout.addWidget(themes_grid)

    # 主题预览
    app._preview_frame = QWidget()
    app._preview_frame.setStyleSheet("background: transparent;")
    app._preview_layout = QVBoxLayout(app._preview_frame)
    app._preview_layout.setContentsMargins(0, 0, 0, 0)
    sf3_layout.addWidget(app._preview_frame)
    update_preview(app, s["theme"])

    layout.addWidget(sf3)

    # ── 应用按钮 ──
    apply_btn = QPushButton("✓ 应用")
    apply_btn.setFont(FONT_B)
    apply_btn.setFixedHeight(48)
    apply_btn.setStyleSheet(f"""
        QPushButton {{ background: {Colors.GREEN}; color: {Colors.TEXT}; border: none; border-radius: 6px; }}
        QPushButton:hover {{ background: {Colors.HOVER_GREEN}; }}
    """)
    apply_btn.clicked.connect(lambda: apply_settings(app))
    layout.addWidget(apply_btn)

    layout.addStretch()


def on_opacity_change(app, v):
    """透明度变化"""
    app._opacity_lbl.setText(f"{v:.0%}")
    app.setWindowOpacity(v / 100.0)
    s = load_settings()
    s["opacity"] = v / 100.0
    save_settings(s)


def on_theme_change(app, name):
    """主题预览"""
    app._current_theme = name
    update_preview(app, name)


def update_preview(app, theme_name):
    """更新主题预览"""
    t = THEMES.get(theme_name, {})
    if not t or not hasattr(app, '_preview_layout'):
        return

    while app._preview_layout.count():
        item = app._preview_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    # 文字预览条（corner_radius=8, height=50, fill="x"）
    bar = QFrame()
    bar.setFixedHeight(50)
    bar.setStyleSheet(f"background: {t['CARD']}; border-radius: 8px;")
    bar_layout = QHBoxLayout(bar)
    bar_layout.setContentsMargins(8, 8, 8, 8)

    for text, color, font in [
        ("主文字", t["TEXT"], FONT_B),
        ("次要文字", t["TEXT2"], FONT_M),
        ("弱化文字", t["DIM"], FONT_M),
    ]:
        lbl = QLabel(text)
        lbl.setFont(font)
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
        bar_layout.addWidget(lbl)

    app._preview_layout.addWidget(bar)

    # 色条（corner_radius=4, height=20）
    colors_row = QWidget()
    colors_row.setStyleSheet("background: transparent;")
    colors_layout = QHBoxLayout(colors_row)
    colors_layout.setContentsMargins(0, 0, 0, 0)
    colors_layout.setSpacing(2)

    for color in [t["BLUE"], t["GREEN"], t["RED"], t["YELLOW"]]:
        c = QFrame()
        c.setFixedHeight(20)
        c.setStyleSheet(f"background: {color}; border-radius: 4px;")
        colors_layout.addWidget(c, 1)

    app._preview_layout.addWidget(colors_row)

    hint = QLabel("选择后点「✓ 应用」重启生效")
    hint.setFont(QFont("MiSans", 12, QFont.Bold))
    hint.setStyleSheet(f"color: {Colors.DIM}; background: transparent;")
    app._preview_layout.addWidget(hint)


def apply_settings(app):
    """应用设置并重启"""
    save_settings({
        "opacity": app._opacity_slider.value() / 100.0,
        "theme": app._current_theme,
    })
    import subprocess
    script = os.path.abspath(sys.argv[0])
    subprocess.Popen([sys.executable, script])
    QApplication.quit()
