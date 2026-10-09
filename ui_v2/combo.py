"""
下拉组件 —— 从 ui/keyboard_mode.py 原样复制(隔离副本)

隔离说明: 新 UI 不引用 ui/ 下任何代码, 避免为了新界面改动旧界面。
本文件是 ui/keyboard_mode.py 中 _Signal / _make_menu_combo / _mini_combo 三段
的逐字副本, 未作任何改动。新 UI 若要改下拉行为, 改这里, 不动旧文件。

保留引用 config(Colors/FONT_M) 与 .widgets(btn_qss): 那是全局主题数据与本目录
内已复制的样式正源, 不属于被隔离的界面代码。
"""
from PySide6.QtWidgets import (QPushButton, QMenu, QWidget, QHBoxLayout,
                               QWidgetAction, QSizePolicy, QFrame)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QCursor, QFont, QFontMetricsF

from config import Colors, FONT_M
from .widgets import btn_qss, menu_qss, menu_btn_qss, rgba_of


class _Signal:
    """极简信号替身: QPushButton 没有 currentTextChanged, 这里补一个"""
    def __init__(self):
        self._slots = []

    def connect(self, fn):
        self._slots.append(fn)

    def emit(self, *a):
        for fn in list(self._slots):
            fn(*a)


def _make_menu_combo(items, width=80, on_select=None, height=25, row_actions=None):
    """下拉控件(QPushButton+QMenu 实现, 全app下拉唯一种类)
    为何不用 QComboBox: 无边框置顶窗口里 QComboBox 的弹窗拿不到输入焦点,
    展开后必须点两次才选中(第一次只激活弹窗)。QMenu 走原生菜单不受影响。
    本类实现 QComboBox 的完整常用接口(setItemData/setCurrentIndex/count/itemText 等),
    调用方无感切换, 样式正源 widgets.menu_btn_qss

    row_actions = [(文字, 回调[, 按钮样式覆盖])] 时, 每个选项自成一行:
    名字靠左弹性撑满, 这对文字按钮右对齐(等价 HTML 的 margin-left:auto),
    回调收被点那条选项文字, 用于预设这种"逐条操作"的下拉; 不传就是普通选项菜单。
    行宽与弹层宽度都定长(按最长名字算), 保证每行一样长。"""
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
    btn._on_select = on_select   # 选中回调挂控件上(原来是闭包捕获, 换不掉也测不到)

    def _pick_row(ix, text):
        """行内点名字 = 选中那条并收起(与普通选项项同语义)"""
        _pick(ix)
        if btn._on_select:
            btn._on_select(text)
        menu.close()

    def _act(cb, text):
        """行内点按钮 = 对这一条执行; 先收弹层再跑(删除要弹确认框, 别压在菜单上)"""
        menu.close()
        QTimer.singleShot(0, lambda: cb(text))

    def _mk_row(text, ix):
        """预设行: 名字靠左弹性撑满, row_actions 那对文字按钮右对齐(等价 HTML 的 margin-left:auto)"""
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 3, 8, 3)
        # 按钮之间不留间隔(靠竖线区分是两个按钮), 名字与按钮对之间的留白由行定长给
        lay.setSpacing(0)
        nm = QPushButton(text)
        nm.setFlat(True)
        nm.setCursor(QCursor(Qt.PointingHandCursor))
        nm.setStyleSheet(btn_qss("transparent", Colors.TEXT, hover=Colors.BLUE,
                                 font="bold 13px 'MiSans'",
                                 extra="text-align: left; padding: 2px 6px;"))
        nm.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        nm.clicked.connect(lambda _c=False, t=text, i=ix: _pick_row(i, t))
        lay.addWidget(nm, 1)
        for i, act in enumerate(row_actions):
            if i:
                # 竖线分隔两颗按钮(HTML --line2 = DIM 的 45%)
                sep = QFrame()
                sep.setFixedWidth(1)
                sep.setFixedHeight(15)
                sep.setStyleSheet(f"background: {rgba_of(Colors.DIM, 0.45)};")
                lay.addWidget(sep)
            a_txt, a_cb = act[0], act[1]
            a_kw = act[2] if len(act) > 2 else {}
            b = QPushButton(a_txt)
            b.setFlat(True)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setStyleSheet(btn_qss("transparent", a_kw.get("fg", Colors.TEXT2),
                                    hover=a_kw.get("hover", Colors.BLUE),
                                    hover_fg=a_kw.get("hover_fg"),
                                    font="bold 13px 'MiSans'",
                                    extra="padding: 2px 6px;"))
            # t 必须是这一行的选项文字(预设名), 不是按钮自己的文字
            b.clicked.connect(lambda _c=False, cb=a_cb, t=text: _act(cb, t))
            lay.addWidget(b)
        qa = QWidgetAction(menu)
        qa.setDefaultWidget(w)
        w._qa = qa
        return w

    def _rebuild():
        menu.clear()
        if row_actions and btn._items:
            rows = [_mk_row(it, ix) for ix, it in enumerate(btn._items)]
            # 行定长 = 最长行 + 分隔留白: 名字区与右端按钮对之间要看得出是两块
            # 下限 220(弹层别比下拉按钮还窄), 上限 240(不溢出左栏 246, 超长名字由按钮自己省略)
            _w = max(220, min(max(r.sizeHint().width() for r in rows) + 40, 240))
            for r in rows:
                r.setFixedWidth(_w)
                menu.addAction(r._qa)
            menu.setFixedWidth(_w + 4)  # 弹层定长(4 = 边框各 1 + 余量)
            return
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
        if btn._on_select:
            btn._on_select(action.text())

    menu.triggered.connect(_on_action)

    def _open_menu():
        menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))
    btn.clicked.connect(_open_menu)

    # 凡是改动 _items 都要跟着重建菜单, 否则 QMenu 与选项不同步
    # (只改 _items 会让菜单留空, 表现为下拉点开是空白菜单、选不中)
    def _addItems(new_items):
        btn._items.extend(new_items)
        btn._datas.extend([None] * len(new_items))
        _rebuild()
        if btn._cur < 0 and btn._items:
            _pick(0, emit=False)

    def _addItem(text, data=None):
        btn._items.append(text)
        btn._datas.append(data)
        _rebuild()
        if btn._cur < 0:
            _pick(0, emit=False)

    def _clear():
        btn._items.clear()
        btn._datas.clear()
        btn._cur = -1
        _rebuild()

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


def _mini_combo(items, cur, w, h=18):
    """下拉(模块级唯一工厂, 行内与悬浮页共用)——QPushButton+QMenu 实现
    不用 QComboBox: 无边框置顶窗口里它的弹窗拿不到输入焦点, 展开后要点两次才选中。
    样式走 widgets.menu_btn_qss(全app下拉唯一样式正源, ACCENT 底 + 10pt Bold);
    h 只调高度, 不改字号, 全app下拉字号一致"""
    cb = _make_menu_combo(items, width=w, height=h)
    cb.setCurrentText(cur)
    return cb
