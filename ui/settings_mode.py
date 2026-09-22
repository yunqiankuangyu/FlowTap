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

from config import Colors, THEMES, DEFAULT_THEME, load_settings, save_settings

# 设置页专用字体：比全局小 3px
_FB = QFont("MiSans", 11, QFont.Bold)
_FM = QFont("MiSans", 11, QFont.Bold)

# 分页定义：页名 -> 该页包含的 section 构建函数名
PAGE_APPEARANCE = "外观设置"
PAGE_FUNCTION = "功能设置"


def _page_btn_style(active):
    """分页切换按钮样式：选中蓝底，未选中灰底"""
    from config import Colors as _C
    bg = _C.BLUE if active else _C.ACCENT
    return f"""
        QPushButton {{ background: {bg}; color: {_C.TEXT}; border: none; border-radius: 4px; }}
        QPushButton:hover {{ background: {_C.BLUE}; }}
    """


def install_wheel_guard(app):
    """防滚轮误改数值：给所有 QDoubleSpinBox/QSlider 设 ClickFocus——
    未点击聚焦时滚轮事件直接穿透给滚动区；点击后可用滚轮调值。"""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDoubleSpinBox, QSlider
    for typ in (QDoubleSpinBox, QSlider):
        for obj in app.findChildren(typ):
            # 无条件 ClickFocus：QSlider 默认 StrongFocus 会被滚轮悬停偷焦点改值
            obj.setFocusPolicy(Qt.ClickFocus)


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
    layout.setContentsMargins(10, 0, 10, 4)

    # ── 页面切换按钮（两个等宽按钮，选中高亮）──
    nav_row = QWidget()
    nav_row.setStyleSheet("background: transparent;")
    nav = QHBoxLayout(nav_row)
    nav.setContentsMargins(0, 0, 0, 2)
    nav.setSpacing(4)

    page_btns = {}

    def _switch_page(name):
        _show_page(app, name)  # _show_page 内部已同步高亮

    for name in (PAGE_APPEARANCE, PAGE_FUNCTION):
        btn = QPushButton(name)
        btn.setFixedHeight(28)
        btn.setFont(QFont("MiSans", 10, QFont.Bold))
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked, n=name: _switch_page(n))
        page_btns[name] = btn
        nav.addWidget(btn, 1)  # 等宽均分

    page_btns[PAGE_APPEARANCE].setStyleSheet(_page_btn_style(True))
    page_btns[PAGE_FUNCTION].setStyleSheet(_page_btn_style(False))

    layout.addWidget(nav_row)
    app._settings_page_btns = page_btns

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

    # 窗口标题（外观页：改标题属于外观个性化）
    v2 = _make_section(ap_layout, "🏷 窗口标题")

    ti_row = QWidget()
    ti_row.setStyleSheet("background: transparent;")
    ti_row_layout = QHBoxLayout(ti_row)
    ti_row_layout.setContentsMargins(0, 0, 0, 0)
    ti_row_layout.setSpacing(6)

    app._title_edit = QLineEdit(s.get("window_title", ""))
    app._title_edit.setPlaceholderText("FlowTap（默认）")
    app._title_edit.setFixedHeight(28)
    app._title_edit.setFont(QFont("MiSans", 10, QFont.Bold))
    app._title_edit.setStyleSheet(f"""
        QLineEdit {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: none; border-radius: 4px; padding: 2px 8px; }}
    """)
    ti_row_layout.addWidget(app._title_edit, 1)

    def _apply_title():
        try:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.inputMethod().commit()  # 强制上屏，否则输入法预编辑态读到空
        except Exception:
            pass
        text = app._title_edit.text().strip()
        s2 = load_settings()
        s2["window_title"] = text
        save_settings(s2)
        app._title_label.setText(text or "FlowTap")
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
                # 圆角走 paintEvent 自绘，setWindowFlags 重建句柄不影响，无需补
        btn.clicked.connect(toggle)
        rl.addWidget(btn)
        return row, btn

    top_row, _ = _make_toggle("窗口置顶", s.get("always_on_top", True), "always_on_top")
    v.addWidget(top_row)

    remember_row, _ = _make_toggle("记住窗口高度", s.get("remember_height", True), "remember_height")
    v.addWidget(remember_row)

    # 窗口绑定（前台闸门）
    v = _make_section(fn_layout, "🎯 窗口绑定")
    from core.window_gate import set_bound_process, get_bound_process
    from PySide6.QtCore import QTimer as _QTimer
    import bisect as _bisect

    bind_row = QWidget()
    bind_row.setStyleSheet("background: transparent;")
    brl = QHBoxLayout(bind_row)
    brl.setContentsMargins(0, 0, 0, 0)
    brl.setSpacing(6)

    BIND_LBL_W = 150
    bind_prefix = QLabel()
    bind_prefix.setFont(_FM)
    bind_lbl = QLabel()
    bind_lbl.setFont(_FM)
    bind_lbl.setFixedWidth(BIND_LBL_W)

    # 跑马灯状态：仅进程名部分超宽时循环滚动，前缀固定不动
    _mq = {"full": "", "x": 0.0, "timer": None}

    def _marquee_step():
        fm = bind_lbl.fontMetrics()
        s = _mq["full"] + " ⋯ "
        offs = [0]
        for ch in s:
            offs.append(offs[-1] + fm.horizontalAdvance(ch))
        total = offs[-1]
        w = bind_lbl.width() or BIND_LBL_W
        if total <= w:  # 放得下就静止
            if _mq["timer"]:
                _mq["timer"].stop()
            bind_lbl.setText(_mq["full"])
            return
        _mq["x"] = (_mq["x"] + 2.0) % total  # 每50ms步进2px
        x0 = _mq["x"]
        end = x0 + w
        i = _bisect.bisect_right(offs, x0) - 1
        if end <= total:
            j = _bisect.bisect_left(offs, end)
            seg = s[i:j]
        else:  # 尾部回绕到开头
            j = _bisect.bisect_left(offs, end - total)
            seg = s[i:] + s[:j]
        bind_lbl.setText(seg)

    def _refresh_bind_lbl():
        name = get_bound_process()
        if name:
            bind_prefix.setText("已绑定: ")
            _mq["full"] = name
            color = Colors.GREEN
        else:
            bind_prefix.setText("")
            _mq["full"] = "未绑定（不限制）"
            color = Colors.DIM
        for lbl in (bind_prefix, bind_lbl):
            lbl.setStyleSheet(f"color: {color}; background: transparent;")
        _mq["x"] = 0.0
        fm = bind_lbl.fontMetrics()
        if fm.horizontalAdvance(_mq["full"]) > (bind_lbl.width() or BIND_LBL_W):
            if _mq["timer"] is None:
                tm = _QTimer(bind_lbl)  # 随标签销毁，重建UI不会泄漏
                tm.setInterval(50)
                tm.timeout.connect(_marquee_step)
                _mq["timer"] = tm
            _mq["timer"].start()
            _marquee_step()
        else:
            if _mq["timer"]:
                _mq["timer"].stop()
            bind_lbl.setText(_mq["full"])

    _refresh_bind_lbl()
    app._bind_lbl = bind_lbl
    brl.addWidget(bind_prefix)
    brl.addWidget(bind_lbl)
    brl.addStretch()

    def _btn_style(bg, hover):
        return f"""
            QPushButton {{ background: {bg}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:disabled {{ background: {Colors.ACCENT}; color: {Colors.DIM}; }}
        """

    capture_btn = QPushButton("捕获窗口")
    capture_btn.setFont(_FM)
    capture_btn.setFixedHeight(28)
    capture_btn.setFixedWidth(76)
    capture_btn.setCursor(Qt.PointingHandCursor)
    capture_btn.setStyleSheet(_btn_style(Colors.BLUE, Colors.ACCENT))
    unbind_btn = QPushButton("解除")
    unbind_btn.setFont(_FM)
    unbind_btn.setFixedHeight(28)
    unbind_btn.setFixedWidth(44)
    unbind_btn.setCursor(Qt.PointingHandCursor)
    unbind_btn.setStyleSheet(_btn_style(Colors.ACCENT, Colors.BLUE))

    from PySide6.QtCore import QTimer as _QTimer

    _capture_timer = {"t": 0, "timer": None}

    def _capture_tick():
        t = _capture_timer["t"]
        if t > 0:
            capture_btn.setText(f"捕获 {t}s")
            _capture_timer["t"] = t - 1
            return
        _capture_timer["timer"].stop()
        capture_btn.setEnabled(True)
        capture_btn.setText("捕获窗口")
        #读前台窗口进程（此时用户应已切到目标窗口）
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        from core.window_gate import get_process_name
        name = get_process_name(hwnd)
        if not name or name in ("python.exe", "pythonw.exe") or name == os.path.basename(sys.argv[0]).lower():
            show_notification(app, "✕ 捕获失败：请切到目标窗口后再试")
            return
        s4 = load_settings()
        s4["bind_process"] = name
        save_settings(s4)
        set_bound_process(name)
        _refresh_bind_lbl()
        show_notification(app, f"✓ 已绑定 {name}")

    def _start_capture():
        if _capture_timer["timer"] is not None and _capture_timer["timer"].isActive():
            return
        _capture_timer["t"] = 3
        capture_btn.setEnabled(False)
        timer = _QTimer(app)
        timer.setInterval(1000)
        timer.timeout.connect(_capture_tick)
        _capture_timer["timer"] = timer
        timer.start()
        _capture_tick()
        show_notification(app, "3秒内请切换到目标窗口", duration_ms=2500)

    def _unbind():
        s4 = load_settings()
        s4["bind_process"] = ""
        save_settings(s4)
        set_bound_process("")
        _refresh_bind_lbl()
        show_notification(app, "✓ 已解除绑定")

    capture_btn.clicked.connect(_start_capture)
    unbind_btn.clicked.connect(_unbind)
    brl.addWidget(capture_btn)
    brl.addWidget(unbind_btn)
    v.addWidget(bind_row)

    bind_hint = QLabel("绑定后仅目标窗口在前台时才执行，切走自动等待、切回继续")
    bind_hint.setFont(QFont("MiSans", 10, QFont.Bold))
    bind_hint.setStyleSheet(f"color: {Colors.DIM}; background: transparent;")
    v.addWidget(bind_hint)

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

    # 挂到布局（按当前模式显示对应分页；默认外观页）
    layout.addWidget(appearance_page)
    layout.addWidget(function_page)
    function_page.hide()
    # 主题应用重建后恢复用户之前所在的分页
    if getattr(app, "_current_mode", "") == "settings" and getattr(app, "_settings_current_page", None) == PAGE_FUNCTION:
        _show_page(app, PAGE_FUNCTION)

    # 防滚轮误调数值
    install_wheel_guard(app)

    # "✓ 应用"按钮由 app._settings_scroll 的统一底部栏创建（与任务页同款构建器）


def _show_page(app, name):
    """切换分页显示"""
    app._settings_current_page = name
    if name == PAGE_APPEARANCE:
        app._page_appearance.show()
        app._page_function.hide()
    else:
        app._page_appearance.hide()
        app._page_function.show()
    # 同步切换按钮高亮
    btns = getattr(app, '_settings_page_btns', None)
    if btns:
        for n, b in btns.items():
            b.setStyleSheet(_page_btn_style(n == name))


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


def _read_title(ed):
    """读标题：先强制提交输入法预编辑（QLineEdit 无 inputMethod()，必须走 QGuiApplication）"""
    try:
        from PySide6.QtGui import QGuiApplication
        QGuiApplication.inputMethod().commit()
    except Exception:
        pass
    try:
        return ed.text().strip()
    except Exception:
        return ""


def apply_settings(app):
    """实时应用设置：保存 → 重设颜色 → 重建全部UI（不重启进程）"""
    from config import Colors
    s = {
        "opacity": app._opacity_slider.value() / 100.0,
        "theme": app._current_theme,
        "window_title": _read_title(app._title_edit),
        "stop_hotkey": app._stop_hotkey,
    }
    cur = load_settings()
    cur.update(s)
    save_settings(cur)
    # 窗口标题即时生效
    app._title_label.setText(s["window_title"] or "FlowTap")
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
    from .keyboard_mode import build_keyboard_mode, _build_drag_handle, build_bottom_bar
    from .settings_mode import build_settings_mode
    from PySide6.QtWidgets import QScrollArea, QFrame, QStackedWidget

    frozen_size = (app.width(), app.height())
    frozen_mode = app._current_mode

    # ── 1. 清浮动面板 ──
    fp = getattr(app, '_floating_panel', None)
    if fp is not None:
        try:
            fp.hide()
            fp.deleteLater()
        except RuntimeError:
            pass
    app._floating_panel = None

    # ── 2. 隐藏旧 central 并移到屏幕外 ──
    old_central = app.centralWidget()
    if old_central is not None:
        old_central.hide()
        old_central.move(-9999, -9999)
        old_central.resize(0, 0)
        for child in old_central.findChildren(QWidget):
            child.hide()

    # ── 3. 创建全新 central + 全新布局 ──
    new_central = QWidget()
    new_central.setStyleSheet(f"background: {Colors.CARD};")
    app.setCentralWidget(new_central)

    lay = QVBoxLayout(new_central)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    app._central_layout = lay

    # 标题栏
    app._titlebar = build_titlebar(app)

    # 键盘模式页面
    app.keyboard_frame = QWidget()
    app.keyboard_frame.setStyleSheet(f"background: {Colors.CARD};")
    app.keyboard_layout = QVBoxLayout(app.keyboard_frame)
    app.keyboard_layout.setContentsMargins(10, 0, 10, 0)
    app.keyboard_layout.setSpacing(0)
    build_keyboard_mode(app)

    # 设置模式页面
    app.settings_frame = QWidget()
    app.settings_frame.setStyleSheet(f"background: {Colors.CARD};")
    app.settings_layout = QVBoxLayout(app.settings_frame)
    app.settings_layout.setContentsMargins(10, 0, 10, 4)
    app.settings_layout.setSpacing(8)
    build_settings_mode(app)
    install_wheel_guard(app)

    # 滚动容器
    scroll_qss = f"""
        QScrollArea {{ background: {Colors.CARD}; border: none; }}
        QScrollBar:vertical {{ background: {Colors.ACCENT}; width: 6px; border-radius: 3px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {Colors.DIM}; border-radius: 3px; min-height: 30px; }}
        QScrollBar::handle:vertical:hover {{ background: {Colors.BLUE}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    """

    app._keyboard_scroll = QScrollArea()
    app._keyboard_scroll.setWidgetResizable(True)
    app._keyboard_scroll.setFrameShape(QFrame.NoFrame)
    app._keyboard_scroll.setStyleSheet(scroll_qss)
    app._keyboard_scroll.setWidget(app.keyboard_frame)

    app._settings_scroll = QScrollArea()
    app._settings_scroll.setWidgetResizable(True)
    app._settings_scroll.setFrameShape(QFrame.NoFrame)
    app._settings_scroll.setStyleSheet(scroll_qss)
    app._settings_scroll.setWidget(app.settings_frame)

    # content stack
    app.content_stack = QStackedWidget()
    app.content_stack.setStyleSheet(f"background: {Colors.CARD};")
    app.content_stack.addWidget(app._keyboard_scroll)
    app.content_stack.addWidget(app._settings_scroll)

    if frozen_mode == "settings":
        app.content_stack.setCurrentIndex(1)
        if hasattr(app, '_settings_current_page'):
            from .settings_mode import _show_page
            _show_page(app, app._settings_current_page)
    else:
        app.content_stack.setCurrentIndex(0)

    # 底部栏 + 拖动条
    bar, btns = build_bottom_bar(app, app._buttons_for(frozen_mode))
    app._bottom_bar = bar
    app._bottom_btns = btns
    app._drag_handle = _build_drag_handle(app)

    lay.addWidget(app._titlebar)
    lay.addWidget(app.content_stack, 1)
    lay.addWidget(app._bottom_bar)
    lay.addWidget(app._drag_handle)

    # ── 4. 恢复窗口状态 ──
    app.setWindowOpacity(load_settings().get("opacity", 1.0))
    lay.activate()
    app.setFixedSize(*frozen_size)
    app.repaint()
