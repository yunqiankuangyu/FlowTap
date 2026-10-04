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
from .widgets import (_make_btn, spin_fill, style_label, btn_qss, card_qss,
                        scroll_qss, set_bg, line_fill, dot_qss, slider_qss)

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
    return btn_qss(bg, _C.TEXT, hover=_C.BLUE)


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
    frame.setStyleSheet(card_qss())
    v = QVBoxLayout(frame)
    v.setContentsMargins(11, 6, 11, 6)

    if title:
        lbl = QLabel(title)
        lbl.setFont(_FB)
        style_label(lbl, Colors.TEXT)
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
    set_bg(nav_row, "transparent")
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

    # 页面容器不设宽度上限: QScrollArea 视口会自动收窄并重排内部内容(见 app.py 处的说明),
    # 给容器额外设上限会凭空扣掉一段宽度, 表现为右侧多出一条空白。

    # ── 外观页容器 ──
    appearance_page = QWidget()
    set_bg(appearance_page, "transparent")
    ap_layout = QVBoxLayout(appearance_page)
    ap_layout.setContentsMargins(0, 0, 0, 0)
    ap_layout.setSpacing(2)
    app._page_appearance = appearance_page

    # ── 功能页容器 ──
    function_page = QWidget()
    set_bg(function_page, "transparent")
    fn_layout = QVBoxLayout(function_page)
    fn_layout.setContentsMargins(0, 0, 0, 0)
    fn_layout.setSpacing(10)
    app._page_function = function_page

    # ══════════ 外观设置 ══════════

    # 窗口标题（外观页：改标题属于外观个性化）
    v2 = _make_section(ap_layout, "🏷 窗口标题")

    ti_row = QWidget()
    set_bg(ti_row, "transparent")
    ti_row_layout = QHBoxLayout(ti_row)
    ti_row_layout.setContentsMargins(0, 0, 0, 0)
    ti_row_layout.setSpacing(6)

    app._title_edit = QLineEdit(s.get("window_title", ""))
    app._title_edit.setPlaceholderText("FlowTap（默认）")
    app._title_edit.setFixedHeight(28)
    app._title_edit.setFont(QFont("MiSans", 10, QFont.Bold))
    line_fill(app._title_edit)
    ti_row_layout.addWidget(app._title_edit, 1)

    def _apply_title():
        text = _read_title(app._title_edit)
        s2 = load_settings()
        s2["window_title"] = text
        save_settings(s2)
        app._title_label.setText(text or "FlowTap")
        from .keyboard_mode import show_floating_notification
        show_floating_notification(app, "✓ 标题已更新" if text else "✓ 已恢复默认标题")
    ti_apply_btn = _make_btn("应用", font=_FM)
    ti_apply_btn.setFixedHeight(28)
    ti_apply_btn.setFixedWidth(52)
    ti_apply_btn.clicked.connect(_apply_title)
    ti_row_layout.addWidget(ti_apply_btn)

    v2.addWidget(ti_row)


    # 透明度
    v = _make_section(ap_layout, "👁 窗口透明度")

    op_row = QWidget()
    set_bg(op_row, "transparent")
    op_row_layout = QHBoxLayout(op_row)
    op_row_layout.setContentsMargins(0, 0, 0, 0)

    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(30)
    slider.setMaximum(100)
    slider.setValue(int(s["opacity"] * 100))
    slider.setStyleSheet(slider_qss())
    app._opacity_slider = slider

    op_val = QLabel(f"{int(s['opacity'] * 100)}%")
    op_val.setFont(_FM)
    style_label(op_val, Colors.TEXT2)
    op_val.setFixedWidth(45)
    app._opacity_lbl = op_val

    slider.valueChanged.connect(lambda val: on_opacity_change(app, val))

    op_row_layout.addWidget(slider, 1)
    op_row_layout.addWidget(op_val)
    v.addWidget(op_row)

    # 主题
    # ── 窗口行为 ──
    def _make_toggle(label_text, checked, key):
        # 设置页开关一律用分段胶囊(关/开两段), 与动作卡组的档位胶囊同一套正源:
        # 两态开关做成翻转按钮时只能看到当前状态, 不知道还有另一个选项存在。
        row = QWidget()
        set_bg(row, "transparent")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label_text)
        lbl.setFont(_FM)
        style_label(lbl, Colors.TEXT2)
        rl.addWidget(lbl)
        rl.addStretch()
        from .segmented import segmented_control
        _ONOFF = [("关", False), ("开", True)]
        def _apply(on):
            s3 = load_settings()
            s3[key] = on
            save_settings(s3)
            if key == "always_on_top":
                flags = app.windowFlags()
                if on:
                    flags |= Qt.WindowStaysOnTopHint
                else:
                    flags &= ~Qt.WindowStaysOnTopHint
                app.setWindowFlags(flags)
                app.show()
                # 圆角走 paintEvent 自绘, setWindowFlags 重建句柄不影响, 无需补
        seg = segmented_control(_ONOFF, bool(checked), _apply, size="settings")
        seg.setToolTip(f"{label_text}：开=启用，关=停用")
        rl.addWidget(seg)
        return row, seg

    v = _make_section(ap_layout, "🪟 窗口行为")
    v.addWidget(_make_toggle("窗口置顶", s.get("always_on_top", True), "always_on_top")[0])
    v.addWidget(_make_toggle("记住窗口高度", s.get("remember_height", True), "remember_height")[0])

    v = _make_section(ap_layout, "🎨 色彩主题")

    themes_grid = QWidget()
    set_bg(themes_grid, "transparent")
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
        btn.setStyleSheet(btn_qss(t["CARD"], t["TEXT"], hover=t["ACCENT"]))
        btn.clicked.connect(lambda checked, n=name: on_theme_change(app, n))
        app._theme_buttons[name] = btn
        grid.addWidget(btn, i // 3, i % 3)

    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 1)
    grid.setColumnStretch(2, 1)
    v.addWidget(themes_grid)

    app._preview_frame = QWidget()
    set_bg(app._preview_frame, "transparent")
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
        set_bg(row, "transparent")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        lbl = QLabel(f"当前: {VK_NAME.get(current_vk, hex(current_vk))}")
        lbl.setFont(_FM)
        style_label(lbl, Colors.TEXT2)
        rl.addWidget(lbl)
        rl.addStretch()
        btn = _make_btn("修改热键", font=_FM)
        btn.setFixedHeight(28)
        btn.setFixedWidth(80)
        def on_capture():
            if app._hotkey_capturing:
                return
            app._hotkey_capturing = True
            app._hotkey_capture_target = capture_key
            lbl.setText("按下任意键... (ESC取消)")
            style_label(lbl, Colors.YELLOW)
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
    style_label(hk_hint, Colors.DIM)
    v.addWidget(hk_hint)

    # 任务默认参数
    v = _make_section(fn_layout, "📋 新建任务默认值")

    defaults_grid = QWidget()
    set_bg(defaults_grid, "transparent")
    dg = QHBoxLayout(defaults_grid)
    dg.setContentsMargins(0, 0, 0, 0)
    dg.setSpacing(6)

    dg.addWidget(QLabel("循环间隔"))
    loop_spin = QDoubleSpinBox()
    loop_spin.setRange(1, 999); loop_spin.setDecimals(1); loop_spin.setSingleStep(5)
    loop_spin.setValue(s.get("default_loop", 80))
    loop_spin.setFixedWidth(55); loop_spin.setFixedHeight(25)
    loop_spin.setFont(_FM); spin_fill(loop_spin)
    app._default_loop_spin = loop_spin
    dg.addWidget(loop_spin)
    dg.addWidget(QLabel("s"))

    dg.addStretch()

    dg.addWidget(QLabel("动作后延"))
    delay_spin = QDoubleSpinBox()
    delay_spin.setRange(0, 30); delay_spin.setDecimals(1); delay_spin.setSingleStep(0.1)
    delay_spin.setValue(s.get("default_delay", 0.5))
    delay_spin.setFixedWidth(45); delay_spin.setFixedHeight(25)
    delay_spin.setFont(_FM); spin_fill(delay_spin)
    app._default_delay_spin = delay_spin
    dg.addWidget(delay_spin)
    dg.addWidget(QLabel("s"))

    for w in defaults_grid.findChildren(QLabel):
        w.setFont(_FM)
        style_label(w, Colors.TEXT2)
    v.addWidget(defaults_grid)

    hint = QLabel("新建任务时使用的初始循环间隔和动作后延")
    hint.setFont(QFont("MiSans", 10, QFont.Bold))
    style_label(hint, Colors.DIM)
    v.addWidget(hint)

    # 启动倒计时
    v = _make_section(fn_layout, "⏱ 启动倒计时")

    cd_row = QWidget()
    set_bg(cd_row, "transparent")
    cd_layout = QHBoxLayout(cd_row)
    cd_layout.setContentsMargins(0, 0, 0, 0)
    cd_layout.setSpacing(6)
    cd_layout.addWidget(QLabel("点击开始后等待"))
    cd_spin = QDoubleSpinBox()
    cd_spin.setRange(0, 10); cd_spin.setDecimals(0); cd_spin.setSingleStep(1)
    cd_spin.setValue(s.get("start_countdown", 3))
    cd_spin.setFixedWidth(40); cd_spin.setFixedHeight(25)
    cd_spin.setFont(_FM); spin_fill(cd_spin)
    app._countdown_spin = cd_spin
    cd_layout.addWidget(cd_spin)
    cd_layout.addWidget(QLabel("秒"))
    cd_layout.addStretch()
    for w in cd_row.findChildren(QLabel):
        w.setFont(_FM)
        style_label(w, Colors.TEXT2)
    v.addWidget(cd_row)

    # 识图匹配
    v = _make_section(fn_layout, "🔍 识图匹配")

    fixed_row, _ = _make_toggle("固定位置比对", s.get("fixed_position_match", True), "fixed_position_match")
    v.addWidget(fixed_row)

    fixed_hint = QLabel("关=整屏搜该图，开=只在框选位置比对")
    fixed_hint.setFont(_FM)
    style_label(fixed_hint, Colors.DIM)
    v.addWidget(fixed_hint)

    tol_row = QWidget()
    set_bg(tol_row, "transparent")
    tol_l = QHBoxLayout(tol_row)
    tol_l.setContentsMargins(0, 0, 0, 0)
    tol_lbl = QLabel("位置容错")
    tol_lbl.setFont(_FM)
    style_label(tol_lbl, Colors.TEXT2)
    tol_l.addWidget(tol_lbl)
    tol_l.addStretch()
    tol_spin = QDoubleSpinBox()
    tol_spin.setRange(0, 10); tol_spin.setDecimals(0); tol_spin.setSingleStep(1)
    tol_spin.setValue(int(s.get("match_tolerance", 3)))
    # 高度用24与上方开关按钮一致(24), 宽度比开关宽以容纳数值
    tol_spin.setFixedWidth(56); tol_spin.setFixedHeight(24)
    tol_spin.setFont(_FM); spin_fill(tol_spin)
    tol_l.addWidget(tol_spin)
    px_lbl = QLabel("px")
    px_lbl.setFont(_FM)          # 不设会走Qt默认字体, 与同排标签不一致
    style_label(px_lbl, Colors.TEXT2)
    tol_l.addWidget(px_lbl)
    v.addWidget(tol_row)

    def _save_tolerance(val):
        s4 = load_settings()
        s4["match_tolerance"] = int(val)
        save_settings(s4)
    tol_spin.valueChanged.connect(_save_tolerance)



    # 窗口绑定（前台闸门）
    v = _make_section(fn_layout, "🎯 窗口绑定")
    from core.window_gate import set_bound_process, get_bound_process
    from PySide6.QtCore import QTimer as _QTimer
    import bisect as _bisect

    bind_row = QWidget()
    set_bg(bind_row, "transparent")
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
            style_label(lbl, color)
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
        return btn_qss(bg, hover=hover, disabled=(Colors.ACCENT, Colors.DIM))

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
    style_label(bind_hint, Colors.DIM)
    v.addWidget(bind_hint)

    # 预设导入/导出
    v = _make_section(fn_layout, "💾 预设备份")

    pe_row = QWidget()
    set_bg(pe_row, "transparent")
    pe_layout = QHBoxLayout(pe_row)
    pe_layout.setContentsMargins(0, 0, 0, 0)
    pe_layout.setSpacing(6)

    def _btn(text, handler):
        b = _make_btn(text, font=_FM)
        b.setFixedHeight(30)
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
            # 导入即刷新顶部预设下拉, 不必再点底部"应用"(应用按钮只管主题)
            try:
                from .keyboard_mode import refresh_preset_combo
                refresh_preset_combo(app)
            except Exception:
                from logger import log_error
                import traceback
                log_error("settings_import", traceback.format_exc())
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
    # 底部栏按钮随分页变化(只有外观页有"应用主题"), 切页时同步重建
    try:
        if getattr(app, "_current_mode", "") == "settings" and getattr(app, "_ensure_bottom_bar", None):
            app._ensure_bottom_bar(app._buttons_for("settings"))
    except Exception:
        pass
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
    """透明度变化。写完设置再同步各独立窗口, 否则拖滑块时只有主窗变。"""
    app._opacity_lbl.setText(f"{v}%")  # v 是 30-100 的整数，直接拼 %（:.0% 会乘100变8900%）
    s = load_settings()
    s["opacity"] = v / 100.0
    save_settings(s)
    # 顺序: 先落盘再同步, 让独立窗口从 apply_all -> current_opacity 读到新值
    from .window_opacity import apply_all
    apply_all(app)


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
            style_label(stop_lbl, Colors.TEXT2)
        start_lbl = getattr(app, '_starthotkey_lbl', None)
        if start_lbl and start_lbl.parent():
            start_lbl.setText(f"当前: {VK_NAME.get(app._start_hotkey, hex(app._start_hotkey))}")
            style_label(start_lbl, Colors.TEXT2)
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
    bar.setStyleSheet(card_qss(t["CARD"], radius=8, sel=""))
    bar_layout = QHBoxLayout(bar)
    bar_layout.setContentsMargins(8, 8, 8, 8)

    for text, color, font in [
        ("主文字", t["TEXT"], _FB),
        ("次要文字", t["TEXT2"], _FM),
        ("弱化文字", t["DIM"], _FM),
    ]:
        lbl = QLabel(text)
        lbl.setFont(font)
        style_label(lbl, color)
        bar_layout.addWidget(lbl)

    app._preview_layout.addWidget(bar)

    # 色条
    colors_row = QWidget()
    set_bg(colors_row, "transparent")
    colors_layout = QHBoxLayout(colors_row)
    colors_layout.setContentsMargins(0, 0, 0, 0)
    colors_layout.setSpacing(2)

    for color in [t["BLUE"], t["GREEN"], t["RED"], t["YELLOW"]]:
        c = QFrame()
        c.setFixedHeight(20)
        c.setStyleSheet(dot_qss(color, radius=4))
        colors_layout.addWidget(c, 1)

    app._preview_layout.addWidget(colors_row)

    hint = QLabel("选择后点「✓ 应用」重启生效")
    hint.setFont(QFont("MiSans", 10, QFont.Bold))
    style_label(hint, Colors.DIM)
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
    """应用主题：只有主题需要显式应用。

    其余设置全部改完即生效，不经过这里——
    透明度/置顶/热键/绑定/识图参数等在各自控件的回调里直接改运行态并落盘，
    标题走标题行的应用按钮，预设增删改与导入在操作当下就刷新下拉。

    主题是唯一的例外：样式表在构建时把颜色插值进了字符串，必须重设 Colors
    并重建全部 UI 才能生效，因此保留这个按钮。
    """
    from config import Colors
    cur = load_settings()
    cur["theme"] = app._current_theme
    save_settings(cur)
    Colors.apply(app._current_theme)
    _rebuild_ui(app)
    # 重建完成后再弹通知，避免通知面板随旧UI销毁而卡死常驻
    show_notification(app, "✓ 主题已应用", duration_ms=1500)


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
    set_bg(new_central, "transparent")  # 圆角由主窗口 paintEvent 统一画(同首次构建)
    app.setCentralWidget(new_central)

    lay = QVBoxLayout(new_central)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    app._central_layout = lay

    # 标题栏
    app._titlebar = build_titlebar(app)

    # 键盘模式页面
    app.keyboard_frame = QWidget()
    set_bg(app.keyboard_frame, "transparent")  # 圆角由主窗口 paintEvent 统一画(同首次构建)
    app.keyboard_layout = QVBoxLayout(app.keyboard_frame)
    app.keyboard_layout.setContentsMargins(10, 0, 10, 0)
    app.keyboard_layout.setSpacing(0)
    build_keyboard_mode(app)

    # 设置模式页面
    app.settings_frame = QWidget()
    set_bg(app.settings_frame, "transparent")  # 圆角由主窗口 paintEvent 统一画(同首次构建)
    app.settings_layout = QVBoxLayout(app.settings_frame)
    app.settings_layout.setContentsMargins(10, 0, 10, 4)
    app.settings_layout.setSpacing(8)
    build_settings_mode(app)
    install_wheel_guard(app)

    # 滚动容器
    sq = scroll_qss(Colors.CARD)

    app._keyboard_scroll = QScrollArea()
    app._keyboard_scroll.setWidgetResizable(True)
    app._keyboard_scroll.setFrameShape(QFrame.NoFrame)
    from core.coords import clamp_scroll_area
    from ui.keyboard_mode import WIN_W

    app._keyboard_scroll.setStyleSheet(sq)
    app._keyboard_scroll.setWidget(app.keyboard_frame)
    clamp_scroll_area(app._keyboard_scroll, WIN_W)

    app._settings_scroll = QScrollArea()
    app._settings_scroll.setWidgetResizable(True)
    app._settings_scroll.setFrameShape(QFrame.NoFrame)
    app._settings_scroll.setStyleSheet(sq)
    app._settings_scroll.setWidget(app.settings_frame)
    clamp_scroll_area(app._settings_scroll, WIN_W)

    # content stack
    app.content_stack = QStackedWidget()
    set_bg(app.content_stack, "transparent")  # 圆角由主窗口 paintEvent 统一画(同首次构建)
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
    # 走统一关口: 与拖动滑块(on_opacity_change)同一套逻辑, 不会再各写一份
    from .window_opacity import apply_all
    apply_all(app)
    lay.activate()
    app.setFixedSize(*frozen_size)
    app.repaint()