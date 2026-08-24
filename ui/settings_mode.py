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

# 设置页专用字体：比全局小 3px
_FB = QFont("MiSans", 11, QFont.Bold)
_FM = QFont("MiSans", 11, QFont.Bold)

# 分页定义：页名 -> 该页包含的 section 构建函数名
PAGE_APPEARANCE = "外观设置"
PAGE_FUNCTION = "功能设置"


def _make_section(parent_layout, title):
    """通用 section 卡片骨架，返回内部 layout"""
    frame = QFrame()
    frame.setStyleSheet(f"QFrame {{ background: {Colors.CARD}; border-radius: 11px; }}")
    v = QVBoxLayout(frame)
    v.setContentsMargins(11, 6, 11, 6)

    if title:
        lbl = QLabel(title)
        lbl.setFont(_FB)
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

    page_combo = QPushButton(PAGE_APPEARANCE)
    page_combo.setFixedHeight(28)
    page_combo.setFont(QFont("MiSans", 10, QFont.Bold))
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
    ap_layout.setSpacing(2)
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

    op_val = QLabel(f"{int(s['opacity'] * 100)}%")
    op_val.setFont(_FM)
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
        btn.setFont(_FM)
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

    # 窗口标题（外观页：改标题属于外观个性化）
    v2 = _make_section(ap_layout, "🏷 窗口标题")

    ti_row = QWidget()
    ti_row.setStyleSheet("background: transparent;")
    ti_row_layout = QHBoxLayout(ti_row)
    ti_row_layout.setContentsMargins(0, 0, 0, 0)
    ti_row_layout.setSpacing(6)

    app._title_edit = QLineEdit(s.get("window_title", ""))
    app._title_edit.setPlaceholderText("⚡ 工具（默认）")
    app._title_edit.setFixedHeight(28)
    app._title_edit.setFont(QFont("MiSans", 10, QFont.Bold))
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
    ti_apply_btn.setFont(_FM)
    ti_apply_btn.setFixedHeight(28)
    ti_apply_btn.setFixedWidth(52)
    ti_apply_btn.setCursor(Qt.PointingHandCursor)
    ti_apply_btn.setStyleSheet(f"""
        QPushButton {{ background: {Colors.BLUE}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
        QPushButton:hover {{ background: {Colors.ACCENT}; }}
    """)
    ti_apply_btn.clicked.connect(_apply_title)
    ti_row_layout.addWidget(ti_apply_btn)

    v2.addWidget(ti_row)

    ap_layout.addStretch()

    # ══════════ 功能设置 ══════════

    from vk_map import VK_NAME
    from PySide6.QtWidgets import QDoubleSpinBox

    def _make_hotkey_row(label_text, current_vk, capture_key):
        """一行热键显示 + 修改按钮"""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        lbl = QLabel(f"当前: {VK_NAME.get(current_vk, hex(current_vk))}")
        lbl.setFont(_FM)
        lbl.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
        rl.addWidget(lbl)
        rl.addStretch()
        btn = QPushButton("修改热键")
        btn.setFont(_FM)
        btn.setFixedHeight(28)
        btn.setFixedWidth(80)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background: {Colors.BLUE}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background: {Colors.ACCENT}; }}
        """)
        def on_capture():
            if app._hotkey_capturing:
                return
            app._hotkey_capturing = True
            app._hotkey_capture_target = capture_key
            lbl.setText("按下任意键... (ESC取消)")
            lbl.setStyleSheet(f"color: {Colors.YELLOW}; background: transparent;")
        btn.clicked.connect(on_capture)
        rl.addWidget(btn)
        setattr(app, f'_{"stop" if capture_key == "stop" else "start"}hotkey_lbl', lbl)
        return row, lbl

    # 全局热键（开始 + 停止）
    v = _make_section(fn_layout, "⌨ 全局热键")

    stop_row, stop_lbl = _make_hotkey_row("停止", app._stop_hotkey, "stop")
    v.addWidget(stop_row)

    start_row, start_lbl = _make_hotkey_row("开始", app._start_hotkey, "start")
    v.addWidget(start_row)

    hk_hint = QLabel("任意界面按下热键立即开始/停止全部任务")
    hk_hint.setFont(QFont("MiSans", 10, QFont.Bold))
    hk_hint.setStyleSheet(f"color: {Colors.DIM}; background: transparent;")
    v.addWidget(hk_hint)

    # 任务默认参数
    v = _make_section(fn_layout, "📋 新建任务默认值")

    defaults_grid = QWidget()
    defaults_grid.setStyleSheet("background: transparent;")
    dg = QHBoxLayout(defaults_grid)
    dg.setContentsMargins(0, 0, 0, 0)
    dg.setSpacing(6)

    spin_style = f"""
        QDoubleSpinBox {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: none; border-radius: 4px; padding: 0px; }}
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}
    """

    dg.addWidget(QLabel("循环间隔"))
    loop_spin = QDoubleSpinBox()
    loop_spin.setRange(1, 999); loop_spin.setDecimals(1); loop_spin.setSingleStep(5)
    loop_spin.setValue(s.get("default_loop", 80))
    loop_spin.setFixedWidth(55); loop_spin.setFixedHeight(25)
    loop_spin.setFont(_FM); loop_spin.setStyleSheet(spin_style)
    app._default_loop_spin = loop_spin
    dg.addWidget(loop_spin)
    dg.addWidget(QLabel("s"))

    dg.addStretch()

    dg.addWidget(QLabel("动作后延"))
    delay_spin = QDoubleSpinBox()
    delay_spin.setRange(0, 30); delay_spin.setDecimals(1); delay_spin.setSingleStep(0.1)
    delay_spin.setValue(s.get("default_delay", 0.5))
    delay_spin.setFixedWidth(45); delay_spin.setFixedHeight(25)
    delay_spin.setFont(_FM); delay_spin.setStyleSheet(spin_style)
    app._default_delay_spin = delay_spin
    dg.addWidget(delay_spin)
    dg.addWidget(QLabel("s"))

    for w in defaults_grid.findChildren(QLabel):
        w.setFont(_FM)
        w.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
    v.addWidget(defaults_grid)

    hint = QLabel("新建任务时使用的初始循环间隔和动作后延")
    hint.setFont(QFont("MiSans", 10, QFont.Bold))
    hint.setStyleSheet(f"color: {Colors.DIM}; background: transparent;")
    v.addWidget(hint)

    # 启动倒计时
    v = _make_section(fn_layout, "⏱ 启动倒计时")

    cd_row = QWidget()
    cd_row.setStyleSheet("background: transparent;")
    cd_layout = QHBoxLayout(cd_row)
    cd_layout.setContentsMargins(0, 0, 0, 0)
    cd_layout.setSpacing(6)
    cd_layout.addWidget(QLabel("点击开始后等待"))
    cd_spin = QDoubleSpinBox()
    cd_spin.setRange(0, 10); cd_spin.setDecimals(0); cd_spin.setSingleStep(1)
    cd_spin.setValue(s.get("start_countdown", 3))
    cd_spin.setFixedWidth(40); cd_spin.setFixedHeight(25)
    cd_spin.setFont(_FM); cd_spin.setStyleSheet(spin_style)
    app._countdown_spin = cd_spin
    cd_layout.addWidget(cd_spin)
    cd_layout.addWidget(QLabel("秒"))
    cd_layout.addStretch()
    for w in cd_row.findChildren(QLabel):
        w.setFont(_FM)
        w.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
    v.addWidget(cd_row)

    # 窗口行为
    v = _make_section(fn_layout, "🪟 窗口行为")

    def _make_toggle(label_text, checked, key):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text)
        lbl.setFont(_FM)
        lbl.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
        rl.addWidget(lbl)
        rl.addStretch()
        btn = QPushButton("开" if checked else "关")
        btn.setFont(_FM)
        btn.setFixedSize(44, 24)
        btn.setCursor(Qt.PointingHandCursor)

        def _style(on):
            color = Colors.GREEN if on else Colors.DIM
            hover = Colors.HOVER_GREEN if on else Colors.ACCENT
            return f"""
                QPushButton {{ background: {color}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
                QPushButton:hover {{ background: {hover}; }}
            """
        btn.setStyleSheet(_style(checked))

        def toggle():
            now_on = btn.text() == "关"
            btn.setText("开" if now_on else "关")
            btn.setStyleSheet(_style(now_on))
            s3 = load_settings()
            s3[key] = now_on
            save_settings(s3)
            if key == "always_on_top":
                flags = app.windowFlags()
                if now_on:
                    flags |= Qt.WindowStaysOnTopHint
                else:
                    flags &= ~Qt.WindowStaysOnTopHint
                app.setWindowFlags(flags)
                app.show()
        btn.clicked.connect(toggle)
        rl.addWidget(btn)
        return row, btn

    top_row, _ = _make_toggle("窗口置顶", s.get("always_on_top", True), "always_on_top")
    v.addWidget(top_row)

    remember_row, _ = _make_toggle("记住窗口高度", s.get("remember_height", True), "remember_height")
    v.addWidget(remember_row)

    # 预设导入/导出
    v = _make_section(fn_layout, "💾 预设备份")

    pe_row = QWidget()
    pe_row.setStyleSheet("background: transparent;")
    pe_layout = QHBoxLayout(pe_row)
    pe_layout.setContentsMargins(0, 0, 0, 0)
    pe_layout.setSpacing(6)

    def _btn(text, handler):
        b = QPushButton(text)
        b.setFont(_FM)
        b.setFixedHeight(30)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{ background: {Colors.BLUE}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background: {Colors.ACCENT}; }}
        """)
        b.clicked.connect(handler)
        return b

    from PySide6.QtWidgets import QFileDialog
    import json as _json

    def export_presets():
        from config.presets import load_presets
        path, _ = QFileDialog.getSaveFileName(app, "导出预设", "FlowTap预设.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            _json.dump({"flowtap_presets": load_presets()}, f, ensure_ascii=False, indent=2)
        show_notification(app, "✓ 预设已导出")

    def import_presets():
        from config.presets import load_presets, save_presets
        path, _ = QFileDialog.getOpenFileName(app, "导入预设", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            incoming = data.get("flowtap_presets", data if isinstance(data, dict) else {})
            if not isinstance(incoming, dict):
                raise ValueError
            merged = load_presets()
            merged.update(incoming)
            save_presets(merged)
            show_notification(app, f"✓ 已导入 {len(incoming)} 个预设")
        except Exception:
            show_notification(app, "✕ 导入失败：文件格式无效")

    pe_layout.addWidget(_btn("导出全部预设", export_presets))
    pe_layout.addWidget(_btn("导入预设", import_presets))
    pe_layout.addStretch()
    v.addWidget(pe_row)

    fn_layout.addStretch()

    # 挂到布局（初始显示外观页）
    layout.addWidget(appearance_page)
    layout.addWidget(function_page)
    function_page.hide()
    app._settings_page_combo = page_combo

    # 应用按钮占位：由 app._settings_scroll 把它固定在滚动区下方
    apply_btn = QPushButton("✓ 应用")
    apply_btn.setFont(_FB)
    apply_btn.setFixedHeight(36)
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
    app._opacity_lbl.setText(f"{v}%")  # v 是 30-100 的整数，直接拼 %（:.0% 会乘100变8900%）
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
        stop_lbl = getattr(app, '_stophotkey_lbl', None)
        if stop_lbl and stop_lbl.parent():
            stop_lbl.setText(f"当前: {VK_NAME.get(app._stop_hotkey, hex(app._stop_hotkey))}")
            stop_lbl.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
        start_lbl = getattr(app, '_starthotkey_lbl', None)
        if start_lbl and start_lbl.parent():
            start_lbl.setText(f"当前: {VK_NAME.get(app._start_hotkey, hex(app._start_hotkey))}")
            start_lbl.setStyleSheet(f"color: {Colors.TEXT2}; background: transparent;")
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
        ("主文字", t["TEXT"], _FB),
        ("次要文字", t["TEXT2"], _FM),
        ("弱化文字", t["DIM"], _FM),
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
    hint.setFont(QFont("MiSans", 10, QFont.Bold))
    hint.setStyleSheet(f"color: {Colors.DIM}; background: transparent;")
    app._preview_layout.addWidget(hint)


def apply_settings(app):
    """实时应用设置：保存 → 重设颜色 → 重建全部UI（不重启进程）"""
    from config import Colors
    s = {
        "opacity": app._opacity_slider.value() / 100.0,
        "theme": app._current_theme,
        "window_title": getattr(app._title_edit, "text", lambda: "")().strip(),
        "stop_hotkey": app._stop_hotkey,
    }
    cur = load_settings()
    cur.update(s)
    save_settings(cur)
    # 窗口标题即时生效
    app._title_label.setText(s["window_title"] or "⚡ 工具")
    # 主题即时生效：重设 Colors 类属性后重建 UI（样式表都是构建时插值的）
    Colors.apply(s["theme"])
    _rebuild_ui(app)
    # 重建完成后再弹通知，避免通知面板随旧UI销毁而卡死常驻
    show_notification(app, "✓ 设置已应用", duration_ms=1500)


def show_notification(app, text, duration_ms=2000):
    """浮动通知（转发 keyboard_mode 实现）"""
    from .keyboard_mode import show_floating_notification
    show_floating_notification(app, text, duration_ms)


def _rebuild_ui(app):
    """销毁并重建所有页面，让新主题的插值样式表生效"""
    from .titlebar import build_titlebar
    from .keyboard_mode import build_keyboard_mode, auto_size
    from .settings_mode import build_settings_mode

    app.setUpdatesEnabled(False)  # 重建期间冻结绘制，消除中间态闪烁
    frozen_size = (app.width(), app.height())  # 记住当前尺寸，重建后原样锁回
    app._floating_panel = None  # 旧通知面板将随旧UI销毁，清引用防定时器打在死对象上

    # 清空中央布局（content_frame 整个被删了，内部框架一并销毁）
    while app._central_layout.count():
        item = app._central_layout.takeAt(0)
        w = item.widget()
        if w:
            w.setParent(None)
            w.deleteLater()

    # 重建全部容器（旧的已销毁，不能复用）
    central = app.centralWidget()
    central.setStyleSheet(f"background: {Colors.CARD};")

    app.content_frame = QWidget()
    app.content_frame.setStyleSheet(f"background: {Colors.CARD};")
    app.content_layout = QVBoxLayout(app.content_frame)
    app.content_layout.setContentsMargins(0, 0, 0, 0)
    app.content_layout.setSpacing(0)

    app.keyboard_frame = QWidget()
    app.keyboard_frame.setStyleSheet(f"background: {Colors.CARD};")
    app.keyboard_layout = QVBoxLayout(app.keyboard_frame)
    app.keyboard_layout.setContentsMargins(0, 0, 0, 0)
    app.keyboard_layout.setSpacing(0)

    app.settings_frame = QWidget()
    app.settings_frame.setStyleSheet(f"background: {Colors.CARD};")
    app.settings_layout = QVBoxLayout(app.settings_frame)
    app.settings_layout.setContentsMargins(10, 10, 10, 10)
    app.settings_layout.setSpacing(8)

    # 中央布局重挂：QWidget 不允许二次 setLayout，必须先卸载旧布局
    old_central_layout = central.layout()
    if old_central_layout is not None:
        QWidget().setLayout(old_central_layout)  # 转移给临时 widget 丢弃
    app._central_layout = QVBoxLayout(central)
    app._central_layout.setContentsMargins(0, 0, 0, 0)
    app._central_layout.setSpacing(0)

    app._titlebar = build_titlebar(app)
    build_keyboard_mode(app)
    build_settings_mode(app)
    # 留在用户当前所在页面（通常就是设置页），不踢回任务页
    app._show_mode(getattr(app, "_current_mode", "keyboard") or "keyboard")

    # 恢复窗口高度和透明度
    app.setWindowOpacity(load_settings().get("opacity", 1.0))
    # 布局收敛后再恢复绘制：先按冻结前尺寸锁定（宽度绝不漂移），高度交给模式逻辑
    app.centralWidget().layout().activate()
    app.setFixedSize(*frozen_size)
    if app._current_mode == "keyboard":
        from .keyboard_mode import auto_size as _as
        _as(app)   # auto_size 内部会以正确高度重新 setFixedSize(360, h)
    # 设置页不另设尺寸：窗口高度只有一个来源（任务页 auto_size / 拖动）
    app.setUpdatesEnabled(True)
    app.update()
