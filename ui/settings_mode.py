"""
设置页面 (PySide6) — 分页：外观 / 功能
顶部一行下拉切换，下方滚动内容 + 底部固定应用按钮
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSlider, QFrame, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from config import Colors, FONT_B, FONT_M, THEMES, DEFAULT_THEME, load_settings, save_settings

# 分页定义：页名 -> 该页包含的 section 构建函数名
PAGE_APPEARANCE = "外观设置"
PAGE_FUNCTION = "功能设置"


def _make_section(parent_layout, title):
    """通用 section 卡片骨架，返回内部 layout"""
    frame = QFrame()
    frame.setStyleSheet(f"QFrame {{ background: {Colors.CARD}; border-radius: 11px; }}")
    v = QVBoxLayout(frame)
    v.setContentsMargins(11, 11, 11, 11)

    if title:
        lbl = QLabel(title)
        lbl.setFont(FONT_B)
        lbl.setStyleSheet(f"color: {Colors.TEXT}; background: transparent;")
        v.addWidget(lbl)
    parent_layout.addWidget(frame)
    return v


def build_settings_mode(app):
    """构建设置页面（分页版）"""
    s = load_settings()
    layout = app.settings_layout
    layout.setContentsMargins(10, 10, 10, 10)

    # ── 页面切换下拉 ──
    nav_row = QWidget()
    nav_row.setStyleSheet("background: transparent;")
    nav = QHBoxLayout(nav_row)
    nav.setContentsMargins(0, 0, 0, 2)
    nav.addStretch()

    page_combo = QPushButton(PAGE_APPEARANCE)
    page_combo.setFixedSize(110, 28)
    page_combo.setFont(QFont("MiSans", 11, QFont.Bold))
    page_combo.setCursor(Qt.PointingHandCursor)
    page_combo.setStyleSheet(f"""
        QPushButton {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: none; border-radius: 4px; padding: 2px 20px 2px 8px; text-align: left; }}
        QPushButton::menu-indicator {{ image: none; subcontrol-origin: padding; subcontrol-position: right center; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {Colors.DIM}; width: 0; height: 0; }}
    """)
    from PySide6.QtWidgets import QMenu
    page_menu = QMenu(page_combo)
    page_menu.setStyleSheet(f"""
        QMenu {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: 1px solid {Colors.DIM}; border-radius: 4px; }}
        QMenu::item {{ padding: 4px 14px; min-height: 24px; }}
        QMenu::item:selected {{ background: {Colors.BLUE}; }}
    """)
    for name in (PAGE_APPEARANCE, PAGE_FUNCTION):
        page_menu.addAction(name)
    page_combo.setMenu(page_menu)

    def _on_page(action):
        page_combo.setText(action.text())
        _show_page(app, action.text())
    page_menu.triggered.connect(_on_page)

    nav.addWidget(page_combo)
    layout.addWidget(nav_row)

    # ── 外观页容器 ──
    appearance_page = QWidget()
    appearance_page.setStyleSheet("background: transparent;")
    ap_layout = QVBoxLayout(appearance_page)
    ap_layout.setContentsMargins(0, 0, 0, 0)
    ap_layout.setSpacing(10)
    app._page_appearance = appearance_page

    # ── 功能页容器 ──
    function_page = QWidget()
    function_page.setStyleSheet("background: transparent;")
    fn_layout = QVBoxLayout(function_page)
    fn_layout.setContentsMargins(0, 0, 0, 0)
    fn_layout.setSpacing(10)
    app._page_function = function_page

    # ══════════ 外观设置 ══════════

    # 透明度
    v = _make_section(ap_layout, "👁 窗口透明度")

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

    slider.valueChanged.connect(lambda val: on_opacity_change(app, val))

    op_row_layout.addWidget(slider, 1)
    op_row_layout.addWidget(op_val)
    v.addWidget(op_row)

    # 主题
    v = _make_section(ap_layout, "🎨 色彩主题")

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

    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(2, 1)
    v.addWidget(themes_grid)

    app._preview_frame = QWidget()
    app._preview_frame.setStyleSheet("background: transparent;")
    app._preview_layout = QVBoxLayout(app._preview_frame)
    app._preview_layout.setContentsMargins(0, 0, 0, 0)
    v.addWidget(app._preview_frame)
    update_preview(app, s["theme"])

    ap_layout.addStretch()

    # ══════════ 功能设置 ══════════

    # 全局停止热键
    v = _make_section(fn_layout, "⌨ 全局停止热键")

    hk_row = QWidget()
    hk_row.setStyleSheet("background: transparent;")
    hk_row_layout = QHBoxLayout(hk_row)
    hk_row_layout.setContentsMargins(0, 0, 0, 0)
    hk_row_layout.setSpacing(8)

    from vk_map import VK_NAME
    app._hotkey_lbl = QLabel(f"当前: {VK_NAME.get(app._stop_hotkey, hex(app._stop_hotkey))}")
    app._hotkey_lbl.setFont(FONT_M)
    app._hotkey_lbl.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
    hk_row_layout.addWidget(app._hotkey_lbl)

    hk_row_layout.addStretch()

    hk_btn = QPushButton("修改热键")
    hk_btn.setFont(FONT_M)
    hk_btn.setFixedHeight(28)
    hk_btn.setFixedWidth(80)
    hk_btn.setCursor(Qt.PointingHandCursor)
    hk_btn.setStyleSheet(f"""
        QPushButton {{ background: {Colors.BLUE}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
        QPushButton:hover {{ background: {Colors.ACCENT}; }}
    """)
    def on_capture_hotkey():
        if app._hotkey_capturing:
            return
        app._hotkey_capturing = True
        app._hotkey_lbl.setText("按下任意键... (ESC取消)")
        app._hotkey_lbl.setStyleSheet(f"color: {Colors.YELLOW}; background: transparent;")
    hk_btn.clicked.connect(on_capture_hotkey)
    hk_row_layout.addWidget(hk_btn)

    v.addWidget(hk_row)

    hk_hint = QLabel("任意界面按下该键立即停止所有任务")
    hk_hint.setFont(QFont("MiSans", 12, QFont.Bold))
    hk_hint.setStyleSheet(f"color: {Colors.DIM}; background: transparent;")
    v.addWidget(hk_hint)

    # 窗口标题
    v = _make_section(fn_layout, "🏷 窗口标题")

    ti_row = QWidget()
    ti_row.setStyleSheet("background: transparent;")
    ti_row_layout = QHBoxLayout(ti_row)
    ti_row_layout.setContentsMargins(0, 0, 0, 0)
    ti_row_layout.setSpacing(6)

    app._title_edit = QLineEdit(s.get("window_title", ""))
    app._title_edit.setPlaceholderText("⚡ 工具（默认）")
    app._title_edit.setFixedHeight(28)
    app._title_edit.setFont(QFont("MiSans", 11, QFont.Bold))
    app._title_edit.setStyleSheet(f"""
        QLineEdit {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: none; border-radius: 4px; padding: 2px 8px; }}
    """)
    ti_row_layout.addWidget(app._title_edit, 1)

    def _apply_title():
        text = app._title_edit.text().strip()
        s2 = load_settings()
        s2["window_title"] = text
        save_settings(s2)
        app._title_label.setText(text or "⚡ 工具")
        from .keyboard_mode import show_floating_notification
        show_floating_notification(app, "✓ 标题已更新" if text else "✓ 已恢复默认标题")
    ti_apply_btn = QPushButton("应用")
    ti_apply_btn.setFont(FONT_M)
    ti_apply_btn.setFixedHeight(28)
    ti_apply_btn.setFixedWidth(52)
    ti_apply_btn.setCursor(Qt.PointingHandCursor)
    ti_apply_btn.setStyleSheet(f"""
        QPushButton {{ background: {Colors.BLUE}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
        QPushButton:hover {{ background: {Colors.ACCENT}; }}
    """)
    ti_apply_btn.clicked.connect(_apply_title)
    ti_row_layout.addWidget(ti_apply_btn)

    v.addWidget(ti_row)

    fn_layout.addStretch()

    # 挂到布局（初始显示外观页）
    layout.addWidget(appearance_page)
    layout.addWidget(function_page)
    function_page.hide()
    app._settings_page_combo = page_combo

    # 应用按钮占位：由 app._settings_scroll 把它固定在滚动区下方
    apply_btn = QPushButton("✓ 应用")
    apply_btn.setFont(FONT_B)
    apply_btn.setFixedHeight(48)
    apply_btn.setStyleSheet(f"""
        QPushButton {{ background: {Colors.GREEN}; color: {Colors.TEXT}; border: none; border-radius: 6px; }}
        QPushButton:hover {{ background: {Colors.HOVER_GREEN}; }}
    """)
    apply_btn.clicked.connect(lambda: apply_settings(app))
    app._settings_apply_btn = apply_btn


def _show_page(app, name):
    """切换分页显示"""
    if name == PAGE_APPEARANCE:
        app._page_appearance.show()
        app._page_function.hide()
    else:
        app._page_appearance.hide()
        app._page_function.show()


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


def update_hotkey_label(app):
    """热键捕获完成后更新设置页标签"""
    from vk_map import VK_NAME
    try:
        if app._hotkey_lbl and app._hotkey_lbl.parent():
            app._hotkey_lbl.setText(f"当前: {VK_NAME.get(app._stop_hotkey, hex(app._stop_hotkey))}")
            app._hotkey_lbl.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
    except RuntimeError:
        pass


def update_preview(app, theme_name):
    """更新主题预览"""
    t = THEMES.get(theme_name, {})
    if not t or not hasattr(app, '_preview_layout'):
        return

    while app._preview_layout.count():
        item = app._preview_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    # 文字预览条
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

    # 色条
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
        "window_title": getattr(app._title_edit, "text", lambda: "")().strip(),
        "stop_hotkey": app._stop_hotkey,
    })
    import subprocess
    if getattr(sys, "frozen", False):
        subprocess.Popen([sys.argv[0]])
    else:
        script = os.path.abspath(sys.argv[0])
        subprocess.Popen([sys.executable, script])
    QApplication.quit()
