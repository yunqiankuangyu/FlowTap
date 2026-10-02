"""
键盘模式页面 (PySide6) — 对齐原版 CTk 布局和样式
布局: pf(顶) → mid(中, expand) → bf(底) → handle(最底)
mid 内部: scroll(上 expand) → 留白(下, 给 bf+handle)
"""
import ctypes

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QDoubleSpinBox,
    QInputDialog, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPoint
from PySide6.QtGui import QFont, QCursor, QFontMetricsF

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Colors, FONT_B, FONT_M, load_presets, save_presets
from .widgets import (_make_btn, _tint_btn, _make_label, state_btn, spin_fill, spin_flat,
                        line_flat, line_fill, ghost_btn, style_label,
                        btn_qss, card_qss, scroll_qss, tip_qss, dot_qss, set_bg, label_qss, menu_qss, menu_btn_qss, F12)
from tasks.keyboard.keyboard_task import KeyboardTask, make_key_action, make_combo_action, make_click_action, fmt_action
from vk_map import VK_NAME

# ── 跨线程 UI 更新桥 ──────────────────────────────────
# QTimer.singleShot(0, fn) 从工作线程调用时 timer 挂在工作线程
# 的 event loop 上——工作线程没有 event loop，timer 永远不触发。
# 用 Qt Signal + QueuedConnection 确保回调投递到主线程。
class _UIBridge(QObject):
    _run = Signal(object)

_ui_bridge = _UIBridge()
_ui_bridge._run.connect(lambda fn: fn(), Qt.QueuedConnection)

def _post_to_main(fn):
    """跨线程安全投递回调到主线程执行"""
    _ui_bridge._run.emit(fn)

class _Signal:
    """极简信号模拟，只支持 connect"""
    def __init__(self):
        self._slots = []
    def connect(self, slot):
        self._slots.append(slot)
    def emit(self, *args):
        for slot in self._slots:
            slot(*args)

class _Signal:
    """极简信号替身: QPushButton 没有 currentTextChanged, 这里补一个"""
    def __init__(self):
        self._slots = []

    def connect(self, fn):
        self._slots.append(fn)

    def emit(self, *a):
        for fn in list(self._slots):
            fn(*a)


def _make_menu_combo(items, width=80, on_select=None, height=25):
    """下拉控件(QPushButton+QMenu 实现, 全app下拉唯一种类)
    为何不用 QComboBox: 无边框置顶窗口里 QComboBox 的弹窗拿不到输入焦点,
    展开后必须点两次才选中(第一次只激活弹窗)。QMenu 走原生菜单不受影响。
    本类实现 QComboBox 的完整常用接口(setItemData/setCurrentIndex/count/itemText 等),
    调用方无感切换, 样式正源 widgets.menu_btn_qss"""
    from PySide6.QtWidgets import QComboBox  # noqa: F401  (类型参照, 保持调用方 import 习惯)
    btn = QPushButton(items[0] if items else "")
    _qt_set_text = btn.setText   # Qt 原生 setText(内部刷新用, 避免与兼容层 btn.setText 自递归)
    btn.setFixedWidth(width)
    btn.setFixedHeight(height)
    btn.setCursor(QCursor(Qt.PointingHandCursor))
    btn.setFont(QFont("MiSans", 10, QFont.Bold))
    btn.setStyleSheet(menu_btn_qss())
    # 不用 btn.setMenu(): 一旦挂上 menu, Qt 的 QSS padding 就不生效(padding 被 menu 布局吃掉,
    # 实测左内边距 5px vs 无 menu 的 14px)。改为 clicked 手动 exec, padding 恢复且行为一致。
    menu = QMenu(btn)
    menu.setStyleSheet(menu_qss())

    btn._items = []          # 全部选项文本
    btn._datas = []          # 与 _items 一一对应的 itemData
    btn._cur = -1            # 当前选中下标
    btn._text = ""           # 显示文本(可被 setText 改成与选项不同的常驻标签)
    btn._fixed_text = False  # True=显示用 _text, 不跟随选项
    btn.currentTextChanged = _Signal()

    def _rebuild():
        menu.clear()
        for it in btn._items:
            menu.addAction(it)
        # 宽度 = 最长选项完整展示所需宽度(按与框同档字号10pt度量) + 菜单内边距
        # QMenu 自己的 sizeHint 不可靠: 像素实测它给 299px 而最长项仅需 220px, 最紧行右边只剩 1px(文字被切)
        if btn._items:
            _fmw = QFontMetricsF(QFont("MiSans", 10, QFont.Bold))
            _w = max(_fmw.horizontalAdvance(it) for it in btn._items)
            menu.setFixedWidth(int(_w) + 26)   # 26 = QMenu::item 左右 padding 各12 + 边框各1

    def _sync_display():
        _qt_set_text(btn._text)

    def _pick(idx, emit=True):
        """选中第 idx 项: 只在真正切换时发信号(与 QComboBox 一致)"""
        if idx < 0 or idx >= len(btn._items):
            return
        changed = (idx != btn._cur)
        btn._cur = idx
        if not btn._fixed_text:
            btn._text = btn._items[idx]
        _sync_display()
        if changed and emit:
            btn.currentTextChanged.emit(btn.currentText())
            _on_index_changed(idx)

    def _on_action(action):
        try:
            idx = btn._items.index(action.text())
        except ValueError:
            return
        _pick(idx)
        if on_select:
            on_select(action.text())

    menu.triggered.connect(_on_action)

    def _open_menu():
        menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))
    btn.clicked.connect(_open_menu)

    def _addItems(new_items):
        btn._items.extend(new_items)
        btn._datas.extend([None] * len(new_items))
        if btn._cur < 0 and btn._items:
            _pick(0, emit=False)

    def _addItem(text, data=None):
        btn._items.append(text)
        btn._datas.append(data)
        if btn._cur < 0:
            _pick(0, emit=False)

    def _clear():
        menu.clear()
        btn._items.clear()
        btn._datas.clear()
        btn._cur = -1

    def _setCurrentIndex(idx, emit=True):
        _pick(idx, emit=emit)

    def _setCurrentText(t, emit=True):
        try:
            idx = btn._items.index(t)
        except ValueError:
            return
        _pick(idx, emit=emit)

    def _itemText(idx):
        return btn._items[idx] if 0 <= idx < len(btn._items) else ""

    def _itemData(idx):
        return btn._datas[idx] if 0 <= idx < len(btn._datas) else None

    def _setItemData(idx, d):
        if 0 <= idx < len(btn._datas):
            btn._datas[idx] = d

    def _setText(t):
        btn._text = t
        btn._fixed_text = True
        _sync_display()

    def _currentData():
        return btn._datas[btn._cur] if 0 <= btn._cur < len(btn._datas) else None

    def _on_index_changed(_i, _cb=btn):
        # 与 currentTextChanged 同步发一份, 供按 index 监听的调用方(jump/branch option)使用
        _cb.currentIndexChanged.emit(_cb.currentIndex())

    # ── QComboBox 兼容接口 ──
    btn.currentIndexChanged = _Signal()
    btn.addItems = _addItems
    btn.addItem = _addItem
    btn.clear = _clear
    btn.setCurrentIndex = _setCurrentIndex
    btn.setCurrentText = _setCurrentText
    btn.currentText = lambda: btn._text
    btn.currentIndex = lambda: btn._cur
    btn.count = lambda: len(btn._items)
    btn.itemText = _itemText
    btn.itemData = _itemData
    btn.setItemData = _setItemData
    btn.currentData = _currentData
    btn.setText = _setText
    btn.view = lambda: menu   # 兼容 QComboBox 的 view()
    btn.menu = lambda: menu   # 兼容 QComboBox 的 menu(): 供 aboutToShow 等钩子取真实 QMenu

    def _set_items(new_items):
        """整体替换选项并重建菜单(动态下拉如关系钮用); 宽度随之按最长项重算"""
        btn._items = list(new_items)
        btn._datas = [None] * len(new_items)
        _rebuild()
        if btn._items:
            _pick(0, emit=False)
        else:
            btn._cur = -1
    btn.set_items = _set_items

    btn._items = list(items)
    btn._datas = [None] * len(items)
    if items:
        btn._cur = 0
        btn._text = items[0]
    _rebuild()
    return btn


def _action_summary(action, task=None):
    """动作行摘要文字。条件分支额外补跳转目标(行内不显示跳到下拉, 目标必须在摘要可见);
    目标未设/已失效时给出可读警示, 不让"条件成立也不跳"静默发生"""
    desc = fmt_action(action)
    if action.get("type") == "cond_branch" and task is not None:
        tgt = action.get("target")
        if tgt:
            ti = next((i for i, a in enumerate(task.actions) if a.get("lid") == tgt), None)
            desc += f" → 动作{ti + 1}" if ti is not None else " → ⚠目标已失效"
        else:
            desc += " → ⚠未设目标"
    return desc


def _target_combo(task, container, big=False):
    """跳转目标下拉：顺序继续(None) + 全部动作；itemData=lid，显示 动作N: 描述
    container = 存 target 的字典（jump 动作本身 或 branch 的 option）; big=悬浮页放大档
    控件构造走 _mini_combo(全app下拉唯一样式), 本函数只管填跳转选项与警示逻辑"""
    items, datas = ["顺序继续"], [None]
    cur = container.get("target")
    sel = 0
    for i, a in enumerate(task.actions):
        items.append(f"动作{i+1}: {fmt_action(a)}")
        datas.append(a.get("lid"))
        if a.get("lid") and a.get("lid") == cur:
            sel = i + 1
    combo = _mini_combo(items, items[sel], 150 if big else 110, h=25 if big else 18)
    for i, d in enumerate(datas):
        combo.setItemData(i, d)
    # 初值已在 _mini_combo 里定好, 不触发信号: 目标动作被删时显示回落「顺序继续」，但存储的 target 必须保留
    combo.blockSignals(True)
    combo.setCurrentIndex(sel)
    combo.blockSignals(False)
    # 未设目标 = 条件成立也不会跳(执行时按顺序继续)，这是用户最容易踩的坑，明确警示
    def _set_tip(_tip):
        combo.setToolTip(_tip)
    if cur and sel == 0:
        _set_tip("⚠ 跳转目标已失效（原动作被删），当前按「顺序继续」执行，请重新选择目标")
    elif not cur:
        _set_tip("⚠ 未设跳转目标：条件成立也不会跳转（等同顺序继续）。请选择一个目标动作")
    else:
        _set_tip(combo.currentText())
    # 选目标: 写回 + 同步警示态 + tooltip（未设目标时提示语优先于文本全文）
    def _on_target_changed(_i, c=container, cb=combo):
        data = cb.currentData()
        c["target"] = data
        warn = data is None
        if warn:
            cb.setToolTip("⚠ 未设跳转目标：条件成立也不会跳转（等同顺序继续）。请选择一个目标动作")
        else:
            cb.setToolTip(cb.currentText())
    combo.currentIndexChanged.connect(_on_target_changed)
    # 弹出列表宽度由 _make_menu_combo 统一按最长选项算, 此处不再另设
    return combo

def _fit_spin(spin, font=None, extra=0):
    #宽度=max(三位数基准, 当前值字宽)+10呼吸+extra: 默认有框的存在感, 值更长时textChanged实时拉长(字体显式; font供悬浮页放大档; extra给阈值等单独加宽)
    _fm = QFontMetricsF(font if font is not None else QFont("MiSans", 11, QFont.Bold))
    _min_w = int(_fm.horizontalAdvance("000")) + 10
    spin.setFixedWidth(max(_min_w, int(_fm.horizontalAdvance(spin.text())) + 10) + extra)

BF_H = 52

def build_keyboard_mode(app):
    """构建键盘模式页面"""
    kf = app.keyboard_frame
    kf_layout = app.keyboard_layout

    # ══════════════════════════════════════════
    # 顶层布局: pf → mid → bf → handle
    # ══════════════════════════════════════════

    # ── 预设栏（顶部）──
    pf = QFrame()
    pf.setStyleSheet(card_qss())
    pf_layout = QHBoxLayout(pf)
    pf_layout.setContentsMargins(7, 7, 7, 7)
    pf_layout.setSpacing(4)

    presets = load_presets()
    preset_names = list(presets.keys()) if presets else ["无预设"]
    # 预设下拉走 _make_menu_combo(QPushButton+QMenu): QComboBox 弹窗在无边框置顶窗口里点两次才选中
    app._preset_combo = _make_menu_combo(preset_names, width=120, height=25)
    pf_layout.addWidget(app._preset_combo)
    pf_layout.addStretch()

    load_btn = _make_btn("加载", bg=Colors.BLUE, hover=Colors.ACCENT)
    load_btn.setFixedSize(36, 25)
    load_btn.clicked.connect(app._load_preset)
    pf_layout.addWidget(load_btn)

    save_btn = _make_btn("保存", bg=Colors.GREEN, hover=Colors.ACCENT)
    save_btn.setFixedSize(36, 25)
    save_btn.clicked.connect(app._save_preset_dialog)
    pf_layout.addWidget(save_btn)

    del_btn = _make_btn("删除", bg=Colors.RED, hover=Colors.ACCENT)
    del_btn.setFixedSize(36, 25)
    del_btn.clicked.connect(app._delete_preset)
    pf_layout.addWidget(del_btn)

    kf_layout.addWidget(pf)

    # ── 滚动区（expand 填充中间剩余空间）──
    from PySide6.QtGui import QPainterPath, QRegion

    class _RoundedScrollArea(QScrollArea):
        """QScrollArea with rounded-corner clipping"""
        _radius = 11
        def resizeEvent(self, e):
            super().resizeEvent(e)
            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), self._radius, self._radius)
            region = QRegion(path.toFillPolygon().toPolygon())
            self.setMask(region)

    app._task_scroll = _RoundedScrollArea()
    app._task_scroll.setWidgetResizable(True)
    app._task_scroll.setFrameShape(QFrame.NoFrame)
    app._task_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    app._task_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    app._task_scroll.setStyleSheet(scroll_qss(Colors.ACCENT))

    app._task_container = QWidget()
    set_bg(app._task_container, "transparent")
    app._task_layout = QVBoxLayout(app._task_container)
    app._task_layout.setContentsMargins(0, 0, 0, 0)
    app._task_layout.setSpacing(5)
    app._task_layout.addStretch()

    app._task_scroll.setWidget(app._task_container)
    kf_layout.addWidget(app._task_scroll, 1)

    # 底部栏和拖动条是窗口级常驻控件，按钮组由 app._show_mode 按当前页管理；
    # "全部开始/停止"按钮引用在 _show_mode('keyboard') 时绑定到 app._bottom_btns[1]
    # 初始化
    app._floating_panel = None
    app._floating_timer = None
    app._cards = []

# 窗口宽度（用户可拖动调整高度，宽度固定）
WIN_W = 400

HANDLE_H = 8  # 拖动条高度

def build_bottom_bar(app, buttons):
    """构建统一底部按钮栏（任务页/设置页共用）。

    buttons: [(text, bg, hover, callback), ...] 水平均分
    返回 (bar, btn_list)
    """
    from PySide6.QtWidgets import QWidget, QHBoxLayout
    bar = QWidget()
    bar.setFixedHeight(BF_H)
    bar.setMinimumHeight(BF_H)
    bar_layout = QHBoxLayout(bar)
    bar_layout.setContentsMargins(10, 2, 10, 0)   # 左右与内容区(10)对齐
    bar_layout.setSpacing(3)

    btns = []
    for text, bg, hover, cb in buttons:
        btn = _make_btn(text, bg=bg, hover=hover, font=FONT_B, height=43)
        btn.clicked.connect(cb)
        bar_layout.addWidget(btn)
        btns.append(btn)
    return bar, btns

def _build_drag_handle(app):
    """构建窗口底部拖动条（任务页/设置页共用），返回 handle 控件"""
    from PySide6.QtWidgets import QWidget, QFrame
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QCursor
    import ctypes
    import ctypes.wintypes
    handle = QWidget()
    handle.setFixedHeight(HANDLE_H)
    handle.setMinimumHeight(HANDLE_H)
    handle.setCursor(QCursor(Qt.SizeVerCursor))
    set_bg(handle, "transparent")

    indicator = QFrame(handle)
    indicator.setFixedSize(200, 4)
    indicator.setStyleSheet(dot_qss("#555"))
    app._drag_indicator = indicator

    def position_indicator():
        try:
            w = handle.width()
            indicator.move((w - indicator.width()) // 2, (HANDLE_H - indicator.height()) // 2)
        except RuntimeError:
            pass  # UI重建后旧handle已销毁，忽略
    handle.resizeEvent = lambda e: position_indicator()
    QTimer.singleShot(0, position_indicator)

    _user32 = ctypes.windll.user32
    _dpi_scale = _user32.GetDpiForSystem() / 96.0 if hasattr(_user32, 'GetDpiForSystem') else 1.0

    app._drag = {"active": False, "start_y": 0, "start_h": 0}

    def on_handle_enter(e):
        indicator.setStyleSheet(dot_qss("#888"))

    def on_handle_leave(e):
        if not app._drag["active"]:
            indicator.setStyleSheet(dot_qss("#555"))

    def on_handle_press(e):
        if e.button() == Qt.LeftButton:
            app._drag["active"] = True
            pt = ctypes.wintypes.POINT()
            _user32.GetCursorPos(ctypes.byref(pt))
            app._drag["start_y"] = pt.y
            app._drag["start_h"] = app.height()  # 读实际窗口高度，不用缓存
            indicator.setStyleSheet(dot_qss("#4fc3f7"))

    def on_handle_release(e):
        app._drag["active"] = False
        indicator.setStyleSheet(dot_qss("#555"))

    def on_handle_drag(e):
        if not app._drag["active"]:
            return
        pt = ctypes.wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        dy = (pt.y - app._drag["start_y"]) / _dpi_scale
        new_h = int(app._drag["start_h"] + dy)
        new_h = max(220, min(600, new_h))
        app.setFixedSize(WIN_W, new_h)
        from config import load_settings, save_settings
        if load_settings().get("remember_height", True):
            s = load_settings()
            s["window_height"] = new_h
            save_settings(s)

    handle.mousePressEvent = on_handle_press
    handle.mouseReleaseEvent = on_handle_release
    handle.mouseMoveEvent = on_handle_drag
    handle.enterEvent = lambda e: on_handle_enter(e)
    handle.leaveEvent = lambda e: on_handle_leave(e)
    handle.setMouseTracking(True)
    return handle

def _task_active(t):
    """任务是否处于活跃状态（运行中或倒计时中）"""
    return t._running or getattr(t, '_countdown_active', False)

def update_all_btn(app):
    """更新全部按钮状态"""
    try:
        running = any(_task_active(t) for t in app.keyboard_tasks)
        if running:
            app._all_btn.setText("■ 全部停止")
            state_btn(app._all_btn, Colors.RED, hover=Colors.HOVER_RED)
        else:
            app._all_btn.setText("▶ 全部开始")
            state_btn(app._all_btn, Colors.GREEN, hover=Colors.HOVER_GREEN)
        update_pause_btn(app)
        app._update_mini_btn()
    except RuntimeError:
        pass  #切页/迷你窗口关闭瞬间的已销毁控件，回切页面时会重建并重同步

def stop_all(app):
    for t in app.keyboard_tasks:
        if _task_active(t):
            t._countdown_active = False
            t.stop()
            # 同步每张任务卡片的UI
            if hasattr(t, '_go_btn') and t._go_btn:
                t._go_btn.setText("▶ 开始")
                state_btn(t._go_btn, Colors.GREEN, hover=Colors.HOVER_GREEN)
            if hasattr(t, '_st_lbl') and t._st_lbl:
                (t._st_set_text if hasattr(t, "_st_set_text") else t._st_lbl.setText)(f"已完成 {t.done_count} 次")
                style_label(t._st_lbl, Colors.DIM)
    update_all_btn(app)

def toggle_all(app):
    running = any(_task_active(t) for t in app.keyboard_tasks)
    if running:
        stop_all(app)
    elif not app.keyboard_tasks:
        show_floating_notification(app, "没有任务，先新建或加载预设")
    else:
        for t in app.keyboard_tasks:
            if not _task_active(t):
                _start_task(app, t)
        update_all_btn(app)

# ── 全部暂停/继续 ──

def pause_all(app):
    """暂停所有活跃任务：进度与时间计数保持，随时可继续"""
    for t in app.keyboard_tasks:
        if _task_active(t) and not getattr(t, '_paused', False):
            t.pause()
            lbl = getattr(t, '_st_lbl', None)
            try:
                if lbl and lbl.parent():
                    (t._st_set_text if hasattr(t, "_st_set_text") else lbl.setText)("⏸ 已暂停")
                    style_label(lbl, Colors.YELLOW)
            except RuntimeError:
                pass

def resume_all(app):
    """继续所有已暂停任务：从冻结的位置接着跑"""
    for t in app.keyboard_tasks:
        if getattr(t, '_paused', False):
            t.resume()
            # 状态栏立即回显当前倒计时，不等下一次 tick
            if t._running and t._countdown_callback:
                pass  # 下一次 tick 会刷新
            elif getattr(t, '_countdown_active', False) and t._st_lbl:
                t._st_set_text("● 准备中...")
                style_label(t._st_lbl, Colors.YELLOW)

def toggle_pause_all(app):
    """有未暂停的活跃任务 → 全部暂停；全在暂停中 → 全部继续"""
    running = [t for t in app.keyboard_tasks if _task_active(t)]
    if not running:
        return
    if any(not getattr(t, '_paused', False) for t in running):
        pause_all(app)
    else:
        resume_all(app)
    update_all_btn(app)

def update_pause_btn(app):
    """同步底部暂停按钮：无活跃任务置灰 / 全在暂停→继续 / 否则→暂停"""
    btn = getattr(app, '_pause_btn', None)
    if btn is None:
        return
    running = [t for t in app.keyboard_tasks if _task_active(t)]
    paused = [t for t in running if getattr(t, '_paused', False)]
    if not running:
        btn.setText("⏸ 全部暂停")
        btn.setEnabled(False)
        state_btn(btn, Colors.ACCENT, fg=Colors.DIM)
    elif len(paused) == len(running):
        btn.setText("▶ 全部继续")
        btn.setEnabled(True)
        state_btn(btn, Colors.GREEN, hover=Colors.HOVER_GREEN)
    else:
        btn.setText("⏸ 全部暂停")
        btn.setEnabled(True)
        state_btn(btn, Colors.YELLOW)

def add_task(app):
    from config import load_settings as _ls
    task = KeyboardTask(app.next_task_id, f"任务{app.next_task_id}", loop_interval=_ls().get("default_loop", 80))
    app.next_task_id += 1
    app.keyboard_tasks.append(task)
    create_card(app, task)
    from .settings_mode import install_wheel_guard
    install_wheel_guard(app)  # 新卡片的 spinbox 防滚轮误触

def create_card(app, task):
    """创建任务卡片"""
    task._app = app  # 存引用，_task_index 用
    card = QFrame()
    card.setStyleSheet(card_qss())
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(11, 11, 11, 11)
    card_layout.setSpacing(5)

    # ── 第一行：折叠钮 + 名称 + 状态 + 删除 + 开始/停止 ──
    hdr = QHBoxLayout()
    hdr.setSpacing(4)

    fold_btn = QPushButton("▼")
    fold_btn.setFixedSize(22, 22)
    fold_btn.setCursor(QCursor(Qt.PointingHandCursor))
    fold_btn.setStyleSheet(btn_qss("transparent", Colors.DIM, hover_fg=Colors.TEXT, font=F12, radius=None))
    fold_btn.setToolTip("收起/展开任务卡片")
    fold_btn.clicked.connect(lambda: toggle_card(app, task))
    task._fold_btn = fold_btn
    hdr.addWidget(fold_btn)

    name_e = QLineEdit(task.name)
    name_e.setFont(FONT_B)
    name_e.setFixedWidth(79)
    name_e.setFixedHeight(25)
    line_fill(name_e, padding="2px 6px")
    name_e.editingFinished.connect(lambda: setattr(task, 'name', name_e.text()))
    task._name_entry = name_e
    hdr.addWidget(name_e)

    st_lbl = _make_label(task.status.value, color=Colors.DIM)
    st_lbl.setMaximumWidth(120)  # 防止状态文字撑爆任务卡
    st_lbl.setToolTip(task.status.value)  # 截断时悬停看全文
    def _st_setter(text):
        fm = st_lbl.fontMetrics()
        elided = fm.elidedText(text, Qt.ElideRight, 118)
        st_lbl.setText(elided)
        st_lbl.setToolTip(text)
    task._st_set_text = _st_setter
    task._st_lbl = st_lbl
    hdr.addWidget(st_lbl)

    hdr.addStretch()

    del_btn = QPushButton("✕")
    del_btn.setFixedSize(22, 22)
    del_btn.setCursor(QCursor(Qt.PointingHandCursor))
    ghost_btn(del_btn, hover=Colors.RED)
    del_btn.clicked.connect(lambda: del_task(app, task, card))
    hdr.addWidget(del_btn)

    go_btn = _make_btn("▶ 开始", bg=Colors.GREEN, hover=Colors.HOVER_GREEN, height=27)
    go_btn.setFixedWidth(79)
    go_btn.clicked.connect(lambda: _toggle_task(app, task, go_btn, st_lbl))
    task._go_btn = go_btn
    hdr.addWidget(go_btn)

    card_layout.addLayout(hdr)

    # ── 动作列表 ──
    task._action_frame = QWidget()
    set_bg(task._action_frame, "transparent")
    task._action_layout = QVBoxLayout(task._action_frame)
    task._action_layout.setContentsMargins(0, 0, 0, 0)
    task._action_layout.setSpacing(2)

    task._action_rows = []
    task._action_frame.setVisible(False)
    card_layout.addWidget(task._action_frame)

    # ── 第二行：添加按钮 ──
    af = QWidget()
    set_bg(af, "transparent")
    af_layout = QHBoxLayout(af)
    af_layout.setContentsMargins(0, 0, 0, 0)
    af_layout.setSpacing(3)

    from .vision_capture import add_image_wait_action, add_ocr_read_action
    from tasks.keyboard.keyboard_task import (make_branch_action, make_jump_action,
                                              make_var_set_action, make_cond_branch_action,
                                              next_var_name)

    # 添加动作区并成三控件一排：键鼠下拉 / 插入下拉 / 清空（原 6 按钮太密）
    def _pick_kb(what):
        dd_kb.setText("+ 键鼠")  # 菜单触发会把按钮改成选项文案，触发器须复位常驻标签
        if "键盘" in what:
            add_key_action(app, task)
        else:
            add_click_action(app, task)

    dd_kb = _make_menu_combo(["⌨ 键盘", "🖱 点击"], width=90, on_select=_pick_kb)
    dd_kb.setText("+ 键鼠")
    dd_kb._current_text = "+ 键鼠"
    dd_kb.setToolTip("添加动作：键盘 / 鼠标点击")
    af_layout.addWidget(dd_kb, 1)

    def _pick_in(what):
        dd_in.setText("+ 插入")
        if "等图像" in what:
            add_image_wait_action(app, task, lambda: _refresh_actions(app, task))
        elif "分支" in what:
            task.actions.append(make_branch_action([]))
            _refresh_actions(app, task)
        else:
            task.actions.append(make_jump_action())
            _refresh_actions(app, task)

    dd_in = _make_menu_combo(["📷 等图像", "🔀 分支", "↳ 跳转"], width=90, on_select=_pick_in)
    dd_in.setText("+ 插入")
    dd_in._current_text = "+ 插入"
    dd_in.setToolTip("插入：等图像（框选等待）/ 多模板分支 / 跳转")
    af_layout.addWidget(dd_in, 1)

    def _pick_var(what):
        dd_var.setText("+ 变量")  # 同 _pick_in：菜单回写文案须复位常驻标签
        if "读数" in what:
            add_ocr_read_action(app, task, lambda: _refresh_actions(app, task))
        elif "运算" in what:
            task.actions.append(make_var_set_action(next_var_name(task.actions, task.vars), "+", 0))
            _refresh_actions(app, task)
        else:
            task.actions.append(make_cond_branch_action(
                next_var_name(task.actions, task.vars), ">=", 0, None))
            _refresh_actions(app, task)

    dd_var = _make_menu_combo(["🔢 读数", "➕ 变量运算", "⚖ 条件分支"], width=90, on_select=_pick_var)
    dd_var.setText("+ 变量")
    dd_var._current_text = "+ 变量"
    dd_var.setToolTip("插入：读数（OCR写入变量）/ 变量运算 / 数值条件分支")
    af_layout.addWidget(dd_var, 1)

    clear_btn = _make_btn("清空", bg=Colors.DIM, hover=Colors.ACCENT, height=25)
    clear_btn.clicked.connect(lambda: clear_actions(app, task))
    af_layout.addWidget(clear_btn, 1)

    # 三等分 → 四等分：解除 helper 的固定宽 + 横向可伸展，stretch=1 把整行均分成 N 份
    from PySide6.QtWidgets import QSizePolicy
    for _w in (dd_kb, dd_in, dd_var, clear_btn):
        _w.setMinimumWidth(0)
        _w.setMaximumWidth(16777215)
        _w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    card_layout.addWidget(af)
    task._extra_rows = [af]  # 折叠时隐藏的附属行
    sf = QWidget()
    set_bg(sf, "transparent")
    sf_layout = QHBoxLayout(sf)
    sf_layout.setContentsMargins(0, 0, 0, 0)

    # 左：关系（单下拉，动态合并"独立/在任务N后"，避免双下拉撑爆行宽）
    right = QHBoxLayout()
    right.setSpacing(3)
    right.addWidget(_make_label("关系:"))

    rel_combo = _make_menu_combo(["独立"], width=80)

    def _rebuild_rel_menu():
        """菜单弹出前重建选项，用位置索引（第几个）而非运行时 id；宽度由工厂按最长项统一算"""
        opts = ["独立"]
        for i, t in enumerate(app.keyboard_tasks):
            if t.task_id != task.task_id:
                opts.append(f"任务{i+1}后")
        rel_combo.set_items(opts)
    rel_combo.menu().aboutToShow.connect(_rebuild_rel_menu)

    def _on_rel_select(text):
        rel_combo._current_text = text
        rel_combo.setText(text)
        task.relation_type = "独立" if text == "独立" else "在任务x后"
        if text.startswith("任务") and text.endswith("后"):
            try:
                # 存位置索引（第几个），不是运行时 task_id
                task.dependency_task_id = int(text[2:-1]) - 1
            except ValueError:
                task.dependency_task_id = None
                task.relation_type = "独立"
        else:
            task.dependency_task_id = None
        if task.relation_type == "在任务x后":
            task.loop_interval = 10
            spin.setValue(10)
            task._loop_label.setText("延迟:")
        else:
            task._loop_label.setText("循环:")
    rel_combo.currentTextChanged.connect(_on_rel_select)  # 兼容旧接口（_on_action 会 emit）
    task._rel_combo = rel_combo
    task._on_rel_select = _on_rel_select  # 存引用，load_preset 调用同步数据

    # 右：循环间隔
    spin = QDoubleSpinBox()
    spin.setRange(0, 999)
    spin.setDecimals(1)
    spin.setSingleStep(5)
    spin.setValue(task.loop_interval)
    spin.setFixedWidth(48)
    spin.setFixedHeight(25)
    spin.setFont(QFont("MiSans", 10, QFont.Bold))
    spin_fill(spin)
    spin.valueChanged.connect(lambda v: setattr(task, 'loop_interval', v))
    task._loop_spin = spin

    # 次数限制输入框（0=无限）
    runs_spin = QDoubleSpinBox()
    runs_spin.setRange(0, 9999)
    runs_spin.setDecimals(0)
    runs_spin.setSingleStep(1)
    runs_spin.setValue(task.max_runs)
    runs_spin.setFixedWidth(38)
    runs_spin.setFixedHeight(25)
    runs_spin.setFont(QFont("MiSans", 10, QFont.Bold))
    spin_fill(runs_spin)
    def _on_runs_change(v):
        task.max_runs = int(v)
        # 修改限制时重置完成标记，允许重新开始
        if hasattr(task, '_finished_by_limit'):
            task._finished_by_limit = False
    runs_spin.valueChanged.connect(_on_runs_change)
    task._runs_spin = runs_spin

    right.addWidget(rel_combo)
    sf_layout.addLayout(right)

    sf_layout.addStretch()

    left = QHBoxLayout()
    left.setSpacing(3)
    loop_label = _make_label("延迟:" if task.relation_type == "在任务x后" else "循环:")
    task._loop_label = loop_label
    left.addWidget(loop_label)
    left.addWidget(spin)
    left.addWidget(_make_label("s"))
    left.addSpacing(4)
    runs_label = _make_label("次数", color=Colors.DIM)
    left.addWidget(runs_label)
    runs_spin.setToolTip("执行次数上限，0 = 无限")
    left.addWidget(runs_spin)
    sf_layout.addLayout(left)

    card_layout.addWidget(sf)
    # sf 不进 _extra_rows：收起时保留最后一行（关系/循环/次数），只隐藏动作列表和+⌨+🖱清空行

    app._task_layout.insertWidget(app._task_layout.count() - 1, card)
    app._cards.append(card)
    _refresh_actions(app, task)

def toggle_card(app, task):
    """收起/展开任务卡片：收起时只保留标题行（内边距同步收紧）"""
    collapsed = not getattr(task, '_collapsed', False)
    task._collapsed = collapsed
    task._fold_btn.setText("▶" if collapsed else "▼")
    task._action_frame.setVisible(bool(task.actions) and not collapsed)
    for w in getattr(task, '_extra_rows', []):
        w.setVisible(not collapsed)

class DraggableRow(QFrame):
    """可拖动的动作行，用QPainter画高亮线，不影响内部布局"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hl_top = False
        self._hl_bottom = False
        self._dragging = False

    def setHighlight(self, top=False, bottom=False):
        self._hl_top = top
        self._hl_bottom = bottom
        self.update()

    def setDragging(self, dragging):
        """拖动中：自身变半透明"""
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        if dragging:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.25)
            self.setGraphicsEffect(eff)
        else:
            self.setGraphicsEffect(None)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._hl_top or self._hl_bottom:
            from PySide6.QtGui import QPainter, QColor, QPen
            from PySide6.QtCore import Qt
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, False)
            pen = QPen(QColor(Colors.BLUE), 2, Qt.SolidLine)
            p.setPen(pen)
            w = self.width()
            if self._hl_top:
                p.drawLine(8, 1, w - 8, 1)
            if self._hl_bottom:
                p.drawLine(8, self.height() - 2, w - 8, self.height() - 2)
            p.end()

def _mini_combo(items, cur, w, h=18):
    """下拉(模块级唯一工厂, 行内与悬浮页共用)——QPushButton+QMenu 实现
    不用 QComboBox: 无边框置顶窗口里它的弹窗拿不到输入焦点, 展开后要点两次才选中。
    样式走 widgets.menu_btn_qss(全app下拉唯一样式正源, ACCENT 底 + 10pt Bold);
    h 只调高度, 不改字号, 全app下拉字号一致"""
    cb = _make_menu_combo(items, width=w, height=h)
    cb.setCurrentText(cur)
    return cb


def _refresh_actions(app, task):
    """刷新动作列表UI"""
    while task._action_layout.count():
        item = task._action_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    task._action_rows.clear()
    task._action_frame.setVisible(bool(task.actions))

    for idx, action in enumerate(task.actions):
        row = DraggableRow()
        row.setStyleSheet(card_qss(Colors.ACCENT, radius=8, sel="DraggableRow"))
        # 统一两行排版: 头行(☰ 描述 … ✕) + 参数行, 400 宽窗内不裁切
        _vbox = QVBoxLayout(row)
        _vbox.setContentsMargins(6, 4, 6, 4)
        _vbox.setSpacing(3)
        row_layout = QHBoxLayout()
        row_layout.setSpacing(2)
        _vbox.addLayout(row_layout)
        # wait/branch设置搬进悬浮设置页(✎), 行内只留摘要
        _inline_full = action.get("type") not in ("wait_image", "branch", "cond_branch", "ocr_read", "var_set")
        # 三期类型(读数/变量运算/条件分支)已全部搬进悬浮编辑页, 不再走行内参数块
        _ctl = None
        if _inline_full:
            _ctl = QHBoxLayout()
            _ctl.setSpacing(0)  # 配对紧挨: label贴数字, 组界另加2px分组
            _ctl.addStretch(1)  # 第二行内容整体右靠
            _vbox.addLayout(_ctl)

        # ☰ 拖动排序手柄
        drag_btn = QPushButton("☰")
        drag_btn.setFixedSize(22, 18)
        drag_btn.setCursor(QCursor(Qt.SizeVerCursor))
        drag_btn.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=Colors.ACCENT, hover_fg=Colors.TEXT, font=F12, radius=4))
        drag_btn.setToolTip("")
        row_layout.addWidget(drag_btn)

        desc = _action_summary(action, task)
        desc_font = QFont("MiSans", 11, QFont.Bold)
        desc_lbl = _make_label(desc, font=desc_font)
        row_layout.addWidget(desc_lbl, 1)

        if action.get("type") in ("jump", "cond_branch") and _inline_full:
            row_layout.addWidget(_make_label("跳到", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM))
            row_layout.addWidget(_target_combo(task, action))

        # 动作行形态：wait(等图像) / branch(分支) / jump(跳转) / 普通
        is_wait = action.get("type") == "wait_image"
        is_branch = action.get("type") == "branch"
        is_jump = action.get("type") == "jump"

        if _inline_full:
            hold_label = _make_label("超时" if (is_wait or is_branch) else "持续", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM)
            _ctl.addWidget(hold_label)

            hold_spin = QDoubleSpinBox()
            if is_wait or is_branch:
                hold_spin.setRange(0, 600)
                hold_spin.setDecimals(0)
                hold_spin.setSingleStep(10)
                hold_spin.setValue(action.get("timeout", 30))
                hold_spin.setSpecialValueText("∞")
                hold_spin.setToolTip("填 0 (∞) = 保持等待：一直等到图像出现才继续，永不超时")
            else:
                hold_spin.setRange(0, 30)
                hold_spin.setDecimals(1)
                hold_spin.setSingleStep(0.1)
                hold_spin.setValue(action.get("hold", 0))
            hold_spin.setFixedHeight(20)
            hold_spin.setFixedWidth(31 if (is_wait or is_branch) else 46)
            hold_spin.setAlignment(Qt.AlignRight)
            hold_spin.setFont(QFont("MiSans", 11, QFont.Bold))
            spin_flat(hold_spin)
            hold_spin.valueChanged.connect(lambda v, a=action: a.__setitem__(
                "timeout" if a.get("type") in ("wait_image", "branch") else "hold", round(v, 2)))
            _ctl.addWidget(hold_spin)
            _ctl.addWidget(_make_label("s", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM))

            delay_label = _make_label("阈值" if is_wait else "后延", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM)
            _ctl.addSpacing(2)  # 组界: 配对内紧、组间松
            _ctl.addWidget(delay_label)

            delay_spin = QDoubleSpinBox()
            if is_wait:
                delay_spin.setRange(0, 1)
                delay_spin.setDecimals(2)
                delay_spin.setSingleStep(0.05)
                delay_spin.setValue(action.get("threshold", 0.85))
            else:
                delay_spin.setRange(0, 30)
                delay_spin.setDecimals(1)
                delay_spin.setSingleStep(0.1)
                delay_spin.setValue(action.get("delay", 0.5))
            delay_spin.setFixedHeight(20)
            if is_wait:  # wait行这个框标签就是"阈值"
                _fit_spin(delay_spin)
            else:
                delay_spin.setFixedWidth(46)
            delay_spin.setAlignment(Qt.AlignRight)
            delay_spin.setFont(QFont("MiSans", 11, QFont.Bold))
            spin_flat(delay_spin)
            delay_spin.valueChanged.connect(lambda v, a=action: a.__setitem__(
                "threshold" if a.get("type") == "wait_image" else "delay", round(v, 2)))
            if is_wait:
                delay_spin.textChanged.connect(lambda _t, sp=delay_spin: _fit_spin(sp))
            _ctl.addWidget(delay_spin)
            if not is_wait:
                _ctl.addWidget(_make_label("s", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM))

        if _inline_full and is_wait:
            _ctl.addSpacing(2)
            # 帧：防抖连续命中次数
            _ctl.addWidget(_make_label("帧", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM))
            hit_spin = QDoubleSpinBox()
            hit_spin.setRange(1, 5)
            hit_spin.setDecimals(0)
            hit_spin.setSingleStep(1)
            hit_spin.setValue(int(action.get("min_hits", 2)))
            hit_spin.setFixedHeight(20)
            hit_spin.setFixedWidth(16)
            hit_spin.setAlignment(Qt.AlignRight)
            hit_spin.setFont(QFont("MiSans", 11, QFont.Bold))
            spin_flat(hit_spin)
            hit_spin.valueChanged.connect(lambda v, a=action: a.__setitem__("min_hits", int(v)))
            _ctl.addWidget(hit_spin)

            _ctl.addSpacing(2)
            # 尺度：多尺度/精确 动态切换（点击翻转 action.scales）
            scale_btn = _make_btn("", font=QFont("MiSans", 11, QFont.Bold), height=20)
            scale_btn.setFixedWidth(47)
            scale_btn.setToolTip("多尺度：UI缩放125%/150%也识别；精确：只按标定原尺寸")
            def _flip_scale(_checked=False, a=action, b=scale_btn):
                cur = a.get("scales") or [1.0, 1.25, 1.5]
                if len(cur) > 1:
                    a["scales"] = [1.0]
                    b.setText("精确")
                    _tint_btn(b, Colors.DIM)
                else:
                    a["scales"] = [1.0, 1.25, 1.5]
                    b.setText("多尺度")
                    _tint_btn(b, Colors.BLUE)
            scale_btn.clicked.connect(_flip_scale)
            _multi = len(action.get("scales") or [1.0, 1.25, 1.5]) > 1
            scale_btn.setText("多尺度" if _multi else "精确")
            _tint_btn(scale_btn, Colors.BLUE if _multi else Colors.DIM)
            _ctl.addWidget(scale_btn)

        if _inline_full and (is_wait or is_branch):
            _ctl.addSpacing(2)
            # 超时后行为：跳过/中止 动态切换（中止=红）
            _ctl.addWidget(_make_label("超时后", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM))
            ot_btn = _make_btn("", font=QFont("MiSans", 11, QFont.Bold), height=20)
            ot_btn.setFixedWidth(32)
            ot_btn.setToolTip("等待超时后：跳过=继续下一动作；跳卡=整张卡片本轮作废(等循环后再来)；中止=终止任务。超时为0时不生效")
            _OT3 = [("skip", "跳过", Colors.BLUE),
                    ("skip_card", "跳卡", Colors.YELLOW),
                    ("stop", "中止", Colors.RED)]
            def _ot_cur(a):
                v = a.get("on_timeout", "skip")
                return "skip" if v == "next" else v  # branch旧值next归一
            def _ot_apply(a, b, val):
                a["on_timeout"] = val
                for k, t, c in _OT3:
                    if k == val:
                        b.setText(t); _tint_btn(b, c); break
            def _flip_ot(_checked=False, a=action, b=ot_btn):
                cur = _ot_cur(a)
                idx = next((i for i, (k, _, _) in enumerate(_OT3) if k == cur), 0)
                _ot_apply(a, b, _OT3[(idx + 1) % 3][0])
            ot_btn.clicked.connect(_flip_ot)
            _ot_apply(action, ot_btn, _ot_cur(action))
            _ctl.addWidget(ot_btn)
            # 超时=0(∞)=保持等待永不超时→超时后行为无意义, 置灰
            hold_spin.valueChanged.connect(lambda v, b=ot_btn: b.setEnabled(v > 0))
            ot_btn.setEnabled(hold_spin.value() > 0)

        if action.get("type") == "click":
            # 定位: 把鼠标移到记录的点上(不点击), 用来核对坐标录得对不对
            loc_btn = _make_btn("定位", bg=Colors.BLUE, hover=Colors.ACCENT, font=QFont("MiSans", 11, QFont.Bold), height=20)
            loc_btn.setFixedWidth(36)
            loc_btn.setToolTip("把鼠标移到这个坐标上（不点击）——用来确认点位准不准")
            def _locate(_c=False, a=action):
                from core import MouseSimulator
                _m = getattr(app, "_locate_mouse", None)
                if _m is None:
                    _m = MouseSimulator()
                    app._locate_mouse = _m
                # 精确移动: 拟人化的±2px微偏与过冲会让落点漂移, 定位必须准
                _m.move_mouse_exact(int(a.get("x", 0)), int(a.get("y", 0)))
            loc_btn.clicked.connect(_locate)
            row_layout.addWidget(loc_btn)

        if is_wait:
            from .vision_preview import open_preview, open_template_view
            prev_btn = _make_btn("预览", bg=Colors.BLUE, hover=Colors.ACCENT, font=QFont("MiSans", 11, QFont.Bold), height=20)
            prev_btn.setFixedWidth(36)
            prev_btn.setToolTip("实时预览匹配得分")
            prev_btn.clicked.connect(lambda checked, a=action: open_preview(
                a, on_close=lambda: _refresh_actions(app, task)))
            row_layout.addWidget(prev_btn)
            tpl_btn = _make_btn("原图", bg=Colors.DIM, hover=Colors.ACCENT, font=QFont("MiSans", 11, QFont.Bold), height=20)
            tpl_btn.setFixedWidth(36)
            tpl_btn.setToolTip("查看标定时截取的原图（静态截图）")
            tpl_btn.clicked.connect(lambda checked, a=action: open_template_view(a))
            row_layout.addWidget(tpl_btn)

        # ocr_read 的「框选」「试读」在悬浮设置页内(行内只留摘要+编辑, 与 wait/branch/cond_branch 一致)

        if not _inline_full:
            from .action_settings_view import open_settings_view
            edit_btn = _make_btn("编辑", bg=Colors.DIM, hover=Colors.ACCENT, font=QFont("MiSans", 11, QFont.Bold), height=20)
            edit_btn.setFixedWidth(36)
            edit_btn.setToolTip("打开设置页")
            edit_btn.clicked.connect(lambda _c=False, a=action: open_settings_view(app, task, a))
            row_layout.addWidget(edit_btn)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(18, 18)
        del_btn.setCursor(QCursor(Qt.PointingHandCursor))
        ghost_btn(del_btn, hover=Colors.RED, hover_fg=Colors.DIM)
        del_btn.clicked.connect(lambda checked, i=idx: _delete_action(app, task, i))
        row_layout.addWidget(del_btn)

        # 拖动排序（检测区=行高30%，UI不变）
        def _drag_start(e, _idx=idx, _row=row):
            if e.button() == Qt.LeftButton:
                from PySide6.QtGui import QDrag
                from PySide6.QtCore import QMimeData
                _row.setDragging(True)
                drag = QDrag(_row)
                mime = QMimeData()
                mime.setText(str(_idx))
                drag.setMimeData(mime)
                drag.exec_(Qt.MoveAction)
                _row.setDragging(False)

        drag_btn.mousePressEvent = _drag_start
        row.setAcceptDrops(True)

        def _clear_hl():
            for r_info in task._action_rows:
                r_info["frame"].setHighlight()

        def _drag_enter(e, _row=row, _idx=idx):
            if e.mimeData().hasText():
                e.acceptProposedAction()

        def _drag_move(e, _row=row, _idx=idx):
            if e.mimeData().hasText():
                e.acceptProposedAction()
                _clear_hl()
                y = e.position().y()
                h = _row.height()
                zone = h * 0.5  # 行高30%为检测区
                if y < zone:
                    _row.setHighlight(top=True)
                elif y > h - zone:
                    _row.setHighlight(bottom=True)
                else:
                    _row.setHighlight(top=True, bottom=True)

        def _drop(e, _idx=idx, _row=row):
            _clear_hl()
            if e.mimeData().hasText():
                try:
                    from_idx = int(e.mimeData().text())
                    y = e.position().y()
                    h = _row.height()
                    zone = h * 0.5
                    if y < zone:
                        to_idx = _idx
                    elif y > h - zone:
                        to_idx = _idx + 1
                    else:
                        to_idx = _idx
                    if from_idx != to_idx and 0 <= from_idx < len(task.actions):
                        action_item = task.actions.pop(from_idx)
                        if from_idx < to_idx:
                            to_idx -= 1
                        task.actions.insert(to_idx, action_item)
                        _refresh_actions(app, task)
                except:
                    pass
            e.acceptProposedAction()

        def _drag_leave(e, _row=row):
            _clear_hl()

        row.dragEnterEvent = _drag_enter
        row.dragMoveEvent = _drag_move
        row.dragLeaveEvent = _drag_leave
        row.dropEvent = _drop
        task._action_layout.addWidget(row)
        task._action_rows.append({"frame": row, "action": action, "desc_lbl": desc_lbl})

    from .settings_mode import install_wheel_guard
    install_wheel_guard(app)  # 新卡片的 spinbox 防滚轮误触

def _delete_action(app, task, idx):
    if 0 <= idx < len(task.actions):
        task.actions.pop(idx)
        _refresh_actions(app, task)

def add_key_action(app, task):
    """捕获按键：即时提示 + QTimer 轮询"""
    if not getattr(app, '_ready', False):
        return
    if getattr(task, '_capturing', False):
        task._capturing = False
        QTimer.singleShot(50, lambda: _start_capture(app, task))
        return
    _start_capture(app, task)

def _start_capture(app, task):
    """启动按键捕获（支持任意组合键）：按住的键实时入集合，全部松开即确认"""
    task._capturing = True

    # 清除焦点，防止空格/回车触发"添加键位"按钮的点击事件
    from PySide6.QtWidgets import QApplication
    fw = QApplication.focusWidget()
    if fw:
        fw.clearFocus()

    # 显示动作区域
    task._action_frame.setVisible(True)

    # 创建临时等待行
    waiting_row = QFrame()
    waiting_row.setStyleSheet(card_qss(Colors.ACCENT, radius=8))
    wl = QHBoxLayout(waiting_row)
    wl.setContentsMargins(6, 4, 6, 4)
    wl.setSpacing(4)
    num_lbl = _make_label("…", color=Colors.DIM)
    num_lbl.setFixedWidth(22)
    wl.addWidget(num_lbl)
    desc_lbl = _make_label("⏳ 按下并保持按键，全部松开完成绑定", font=FONT_B)
    style_label(desc_lbl, Colors.YELLOW)
    wl.addWidget(desc_lbl, 1)
    task._action_layout.addWidget(waiting_row)
    task._action_rows.append({"frame": waiting_row, "action": None, "desc_lbl": desc_lbl})

    # 清除旧键盘状态
    u32 = ctypes.windll.user32
    for vk in range(0x08, 0x100):
        u32.GetAsyncKeyState(vk)

    pressed = set()   # 当前按住的键集合
    combo = []        # 参与组合的键（按按下顺序）

    def _combo_text():
        from vk_map import VK_NAME
        names = [VK_NAME.get(vk, f"[{vk}]") for vk in combo]
        return "+".join(names) if names else "..."

    poll_timer = QTimer()

    def poll_keys():
        if not task._capturing:
            poll_timer.stop()
            return
        # 实时跟踪按下/松开
        for vk in range(0x08, 0x100):
            down = bool(u32.GetAsyncKeyState(vk) & 0x8000)
            if down and vk not in pressed:
                pressed.add(vk)
                if vk not in combo:
                    combo.append(vk)
                desc_lbl.setText(f"⏳ {_combo_text()} （全部松开完成）")
            elif not down and vk in pressed:
                pressed.discard(vk)
        # 有过按键且现在全部松开 → 确认组合
        if combo and not pressed:
            task._capturing = False
            poll_timer.stop()
            from config import load_settings as _ls
            if len(combo) == 1:
                task.actions.append(make_key_action(combo[0], delay=_ls().get("default_delay", 0.5)))
            else:
                task.actions.append(make_combo_action(list(combo), delay=_ls().get("default_delay", 0.5)))
            QTimer.singleShot(0, lambda: _refresh_actions(app, task))

    poll_timer.timeout.connect(poll_keys)
    poll_timer.start(15)

def add_click_action(app, task):
    """录制鼠标位置：移出屏幕 + 全屏遮罩 + QTimer 轮询"""
    if not getattr(app, '_ready', False):
        return
    if getattr(task, '_recording_click', False):
        return
    task._recording_click = True

    _orig_geo = app.geometry()
    screen = app.screen().geometry()
    app.move(screen.width() + 100, screen.height() + 100)

    # 全屏遮罩
    overlay = QWidget()
    overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    overlay.setAttribute(Qt.WA_TranslucentBackground, True)
    overlay.setAttribute(Qt.WA_ShowWithoutActivating, True)
    set_bg(overlay, "rgba(0, 0, 0, 80)")
    overlay.setGeometry(screen)
    overlay.closeEvent = lambda e: e.ignore()

    tip = QLabel("🎯 点击任意位置绑定  |  ESC 取消  |  15秒超时", overlay)
    tip.setFont(FONT_B)
    tip.setAlignment(Qt.AlignCenter)
    tip.setStyleSheet(tip_qss())
    tip.adjustSize()
    tip.move((screen.width() - tip.width()) // 2, (screen.height() - tip.height()) // 2)
    overlay.showFullScreen()
    overlay.raise_()
    overlay.activateWindow()

    state = {'done': False}

    def cleanup(accepted=False):
        if state['done']:
            return
        state['done'] = True
        task._recording_click = False
        poll_timer.stop()
        safety_timer.stop()

        def _restore():
            overlay.hide()
            overlay.deleteLater()
            app.move(_orig_geo.x(), _orig_geo.y())
            app.raise_()
            app.activateWindow()
        QTimer.singleShot(0, _restore)

        if accepted:
            QTimer.singleShot(0, lambda: _refresh_actions(app, task))

    def poll_input():
        """每 50ms 检测一次键盘和鼠标"""
        import ctypes
        u32 = ctypes.windll.user32

        # ESC 键
        if u32.GetAsyncKeyState(0x1B) & 0x8000:
            cleanup(accepted=False)
            return

        # 鼠标左键
        if u32.GetAsyncKeyState(0x01) & 0x8000:
            import ctypes.wintypes
            p = ctypes.wintypes.POINT()
            u32.GetCursorPos(ctypes.byref(p))
            from config import load_settings as _ls
            act = make_click_action(p.x, p.y, delay=_ls().get("default_delay", 0.5))
            # 绑定进程时：点下位置属于该进程窗口 → 存客户区相对坐标（窗口拖走仍点得准）
            from core.window_gate import get_bound_process, window_at_point
            bound = get_bound_process()
            if bound:
                hwnd = window_at_point(p.x, p.y,
                                       exclude=int(overlay.winId()), process=bound)
                if hwnd:
                    rect = ctypes.wintypes.RECT()
                    org = ctypes.wintypes.POINT(0, 0)
                    if (u32.GetClientRect(hwnd, ctypes.byref(rect))
                            and u32.ClientToScreen(hwnd, ctypes.byref(org))):
                        act["rel"] = True
                        act["x"] = p.x - org.x
                        act["y"] = p.y - org.y
                        act["sx"], act["sy"] = p.x, p.y
            task.actions.append(act)
            cleanup(accepted=True)
            return

    def on_safety_timeout():
        """15 秒强制关闭"""
        cleanup(accepted=False)

    poll_timer = QTimer()
    poll_timer.timeout.connect(poll_input)

    safety_timer = QTimer()
    safety_timer.setSingleShot(True)
    safety_timer.timeout.connect(on_safety_timeout)
    safety_timer.start(15000)

    # 等鼠标松开后开始检测
    wait_timer = QTimer()
    def initial_wait():
        import ctypes
        u32 = ctypes.windll.user32
        if u32.GetAsyncKeyState(0x01) & 0x8000:
            return  # 还没松开，继续等
        wait_timer.stop()
        poll_timer.start(50)
    wait_timer.timeout.connect(initial_wait)
    wait_timer.start(50)

def clear_actions(app, task):
    task.actions.clear()
    _refresh_actions(app, task)

def _toggle_task(app, task, btn, lbl):
    """启动/停止任务"""
    if task._running or getattr(task, '_countdown_active', False):
        task._countdown_active = False
        task.stop()
        btn.setText("▶ 开始")
        state_btn(btn, Colors.GREEN, hover=Colors.HOVER_GREEN)
        (task._st_set_text if hasattr(task, "_st_set_text") else lbl.setText)(f"已完成 {task.done_count} 次")
        style_label(lbl, Colors.DIM)
        update_all_btn(app)
    else:
        _start_task(app, task)

def _start_task(app, task):
    """启动任务（带3秒倒计时）"""
    _ensure_limit_watcher(app)
    if task.relation_type == "在任务x后":
        # 依赖ID已在下拉选择时写入 task.dependency_task_id
        pass

    update_dependencies(app)

    btn = task._go_btn
    lbl = task._st_lbl

    if task.relation_type == "在任务x后":
        task._callback = lambda: _post_to_main(lambda: (
            task._st_set_text("● 等待下次触发..."),
            style_label(task._st_lbl, Colors.YELLOW)
        ))
        def _make_cd_cb():
            def cb(t, c):
                _post_to_main(lambda t=t, c=c: (
                    task._st_set_text(t),
                    style_label(task._st_lbl, c)
                ))
            return cb
        task._countdown_callback = _make_cd_cb()
        task.start()
        btn.setText("■ 停止")
        state_btn(btn, Colors.RED, hover=Colors.HOVER_RED)
        task._st_set_text("● 等待前置任务")
        style_label(lbl, Colors.YELLOW)
        update_all_btn(app)
    else:
        btn.setText("■ 停止")
        state_btn(btn, Colors.RED, hover=Colors.HOVER_RED)
        task._countdown_active = True

        def _tick(count):
            try:
                if not task._countdown_active:
                    return
                if getattr(task, '_paused', False):
                    QTimer.singleShot(100, lambda: _tick(count))
                    return
                if count > 0:
                    task._st_set_text(f"● 准备中 {count}...")
                    style_label(task._st_lbl, Colors.YELLOW)
                    QTimer.singleShot(1000, lambda: _tick(count - 1))
                else:
                    task._countdown_active = False
                    def _make_cd_cb():
                        def cb(t, c):
                            try:
                                _post_to_main(lambda t=t, c=c: (
                                    task._st_set_text(t),
                                    style_label(task._st_lbl, c)
                                ))
                            except Exception as e:
                                from logger import log_error
                                log_error("countdown_cb", e)
                        return cb
                    task._countdown_callback = _make_cd_cb()
                    task.start(
                        countdown_callback=task._countdown_callback
                    )
                    task._st_set_text(task.status.value)
                    style_label(task._st_lbl, Colors.GREEN)
                    update_all_btn(app)
            except Exception as e:
                from logger import log_error
                log_error("tick", e)

        from config import load_settings
        _tick(load_settings().get("start_countdown", 3))

def update_dependencies(app):
    """更新任务依赖关系（dependency_task_id 现在存位置索引）"""
    for t in app.keyboard_tasks:
        t._dependents = []
    for t in app.keyboard_tasks:
        if t.relation_type == "在任务x后" and t.dependency_task_id is not None:
            idx = t.dependency_task_id
            if isinstance(idx, int) and 0 <= idx < len(app.keyboard_tasks):
                parent = app.keyboard_tasks[idx]
                parent._dependents.append(t)

def _ensure_limit_watcher(app):
    """启动全局监视器：检测任务因次数限制自动完成，同步UI（只挂一次）"""
    if getattr(app, '_limit_watcher', None) is not None:
        return
    timer = QTimer(app)
    timer.timeout.connect(lambda: _check_limit_finished(app))
    timer.start(300)
    app._limit_watcher = timer

def _check_limit_finished(app):
    """检查是否有任务因次数限制跑满自动停了，同步按钮和状态"""
    try:
        for t in list(app.keyboard_tasks):
            if getattr(t, '_finished_by_limit', False) and not t._running:
                t._finished_by_limit = False
                btn = getattr(t, '_go_btn', None)
                lbl = getattr(t, '_st_lbl', None)
                try:
                    if btn and btn.parent():
                        btn.setText("▶ 开始")
                        state_btn(btn, Colors.GREEN, hover=Colors.HOVER_GREEN)
                    if lbl and lbl.parent():
                        (t._st_set_text if hasattr(t, "_st_set_text") else lbl.setText)(f"✓ 已达上限 {t.done_count} 次")
                        style_label(lbl, Colors.BLUE)
                except RuntimeError:
                    pass
                update_all_btn(app)
                show_floating_notification(app, f"{t.name} 已完成 {t.done_count} 次，自动停止")
    except Exception as e:
        from logger import log_error
        log_error("limit_watcher", e)

def del_task(app, task, card):
    """删除任务"""
    task.stop()
    app.keyboard_tasks.remove(task)
    app._task_layout.removeWidget(card)
    card.deleteLater()
    if card in app._cards:
        app._cards.remove(card)

def load_preset(app):
    """加载预设"""
    name = app._preset_combo.currentText()
    if name == "无预设":
        return
    presets = load_presets()
    if name not in presets:
        return

    #有任务时先确认，防止误点覆盖当前编辑内容
    if app.keyboard_tasks:
        ret = QMessageBox.question(
            app, "加载预设",
            f"加载「{name}」将替换当前 {len(app.keyboard_tasks)} 个任务，且无法撤销。\n确定继续吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ret != QMessageBox.Yes:
            return

    for t in app.keyboard_tasks:
        t.stop()
    while app._task_layout.count():
        item = app._task_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    app._cards.clear()
    app.keyboard_tasks.clear()
    app._task_layout.addStretch()

    p = presets[name]

    # 创建任务（dependency_task_id 现在直接存索引）
    for td in p.get("tasks", []):
        task = KeyboardTask(app.next_task_id, td.get("name", f"任务{app.next_task_id}"))
        app.next_task_id += 1
        from tasks.keyboard.keyboard_task import _ensure_lids
        task.actions = _ensure_lids(td.get("actions", []))
        task.loop_interval = td.get("loop_interval", 80)
        task.max_runs = td.get("max_runs", 0)
        task.relation_type = td.get("relation_type", "独立")
        task.dependency_task_id = td.get("dependency_task_id")  # 现在是索引
        if task.relation_type == "在任务x后":
            task._preset_loop_interval = task.loop_interval
        app.keyboard_tasks.append(task)
        create_card(app, task)

    # 恢复 UI（直接设，不走信号链）
    for t in app.keyboard_tasks:
        if t.relation_type == "在任务x后" and t.dependency_task_id is not None:
            idx = t.dependency_task_id
            # 索引越界或自身引用→降级为独立
            if not isinstance(idx, int) or idx < 0 or idx >= len(app.keyboard_tasks) or idx == app.keyboard_tasks.index(t):
                t.relation_type = "独立"
                t.dependency_task_id = None
                combo_text = "独立"
            else:
                combo_text = f"任务{idx+1}后"
            t._rel_combo._current_text = combo_text
            t._rel_combo.setText(combo_text)
            t._loop_label.setText("延迟:" if t.relation_type == "在任务x后" else "循环:")
            if t.relation_type == "在任务x后" and hasattr(t, '_preset_loop_interval'):
                t.loop_interval = t._preset_loop_interval
                t._loop_spin.setValue(t.loop_interval)

    show_floating_notification(app, f"已加载: {name}")

def save_preset_dialog(app):
    """保存预设对话框"""
    name, ok = QInputDialog.getText(app, "保存预设", "预设名称:")
    if not ok or not name.strip():
        return
    name = name.strip()

    presets = load_presets()
    presets[name] = {
        "tasks": [
            {
                "task_id": t.task_id,
                "name": t.name,
                "actions": t.actions,
                "loop_interval": t.loop_interval,
                "max_runs": t.max_runs,
                "relation_type": t.relation_type,
                "dependency_task_id": t.dependency_task_id if t.relation_type == "在任务x后" else None,
            }
            for t in app.keyboard_tasks
        ]
    }
    save_presets(presets)

    app._preset_combo.clear()
    app._preset_combo.addItems(list(presets.keys()))
    app._preset_combo.setCurrentText(name)

    show_floating_notification(app, f"已保存: {name}")

def delete_preset_cmd(app):
    """删除预设"""
    name = app._preset_combo.currentText()
    if name == "无预设":
        return
    from config.presets import delete_preset
    delete_preset(name)
    presets = load_presets()
    app._preset_combo.clear()
    app._preset_combo.addItems(list(presets.keys()) if presets else ["无预设"])
    show_floating_notification(app, f"已删除: {name}")

def show_floating_notification(app, text, duration_ms=2000):
    """在窗口内显示一条悬浮通知"""
    hide_floating_notification(app)

    panel = QFrame(app)
    panel.setStyleSheet(card_qss(bg="transparent", radius=None, extra="border: none;"))

    lbl = QLabel(text, panel)
    lbl.setFont(FONT_M)
    lbl.setStyleSheet(label_qss(Colors.TEXT, bg=Colors.CARD, extra=f"border: 1px solid {Colors.BLUE}; border-radius: 8px; padding: 8px 16px;"))
    lbl.adjustSize()

    panel.setFixedSize(lbl.sizeHint().width() + 4, lbl.sizeHint().height() + 4)
    lbl.move(2, 2)

    # 相对于主窗口居中底部
    w = app.width()
    h = app.height()
    x = (w - panel.width()) // 2
    y = h - panel.height() - 40  # 底部按钮上方
    panel.move(x, y)
    panel.show()
    panel.raise_()
    app._floating_panel = panel

    if duration_ms > 0:
        QTimer.singleShot(duration_ms, lambda: hide_floating_notification(app))

def hide_floating_notification(app):
    """隐藏悬浮通知"""
    panel = getattr(app, '_floating_panel', None)
    if panel:
        try:
            panel.hide()
            panel.deleteLater()
        except RuntimeError:
            pass  # 面板已随UI重建销毁
        app._floating_panel = None