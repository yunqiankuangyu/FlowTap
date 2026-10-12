"""
三栏面板 —— 左(任务) / 中(动作) / 右(配置), 全部绑定 Model

交互原则: 增删类操作重建对应区域(行号会变, 重建才不错位); 改参数类操作只写模型,
不重建 —— 重建会把用户正在输入的数字框清掉。

复用清单(凡是原有组件能实现的都直接引用, 不新建近似变体):
  下拉      ui.keyboard_mode._make_menu_combo   全app下拉唯一种类
  分段胶囊  ui.segmented.segmented_control       normal/settings 两档
  按钮      ui.widgets._make_btn / flat_btn / ghost_btn
  卡片      ui.widgets.card_qss
  数字框    ui.widgets.spin_flat
  标签      ui.widgets._make_label / style_label
  滚动      ui.widgets.scroll_qss

栏宽按 20/40/40 分配(百分比, 主人口述比例), 栏间用 1px 分隔线。
数字框统一 1 位小数: decimals 设 2 会把 0.1 渲染成 0.10、10 渲染成 10.00,
比预览稿宽出一截把行动行撑破。
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
                               QDoubleSpinBox, QLabel, QScrollArea,
                               QPushButton, QStackedWidget, QLayout, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFontMetricsF, QColor

from config import Colors, FONT_B, FONT_M
from .widgets import (card_qss, btn_qss, dot_qss, scroll_qss, spin_flat, spin_fill,
                        flat_btn, ghost_btn, _make_btn, _make_label, style_label, tag_label,
                        set_bg, rgba_of, F12)
from .combo import _make_menu_combo, _mini_combo
from .segmented import segmented_control
from .model import _vk_name, combo_name

# 间隔口径(用户要求缩短): 正源 .col 是 padding:12px; gap:12px。
# GAP = 条目之间(任务卡/动作行/设置项), 用户定为 4px;
# PAD = 栏内边距(同时决定中栏与两侧栏的视觉间隔 = 各栏 PAD + 1px 分隔线), 6px。
GAP = 4
PAD = 6
RATIO = (20, 40, 40)   # 百分比口径(正源), 换算见 win_v2: setFixedWidth(WIN_W * p / 100)
PICK3 = [("继续下一步", "next"), ("跳过本分支", "skip"), ("结束任务", "stop")]
# 等待条件 / 超时后 —— 值即显示文本(模型里存的就是中文串), 不另造键名
WAIT3 = [(s, s) for s in ("图像·按钮", "图像·图标", "文字内容")]
AFTER3 = [(s, s) for s in ("跳过", "跳卡", "中止")]
# 变量类动作的徽章: (图标, 徽章色 hex —— 走 rgba_of 换算)
_VAR_STYLE = {"read": ("🔢", "#9678dc"),
              "varset": ("➕", "#d29650"),
              "cond": ("⚖", "#5aaac8")}


class CardBox(QFrame):
    """卡片容器(设置区卡 / 任务卡共用)

    必须用类名做 QSS 选择器: card_qss 的 sel 若留 "QFrame" 或用裸规则 "",
    选中态的 border 都会画进内部 QLabel —— QLabel 就是 QFrame 的子类,
    实测"临时去掉卡片 border, 标签内的长横线立刻归零"证明框来自容器 border。
    动作行用 ActionRow 类名没这问题, 此处照同一做法。
    """


class ActionRow(QFrame):
    """动作行 / 分支行 / 变量行的容器, 带拖拽排序与高亮

    两个职责各有一个独立理由:
      1. 不直接用 QFrame —— card_qss 默认按 QFrame 匹配, 而 QDoubleSpinBox
         也是 QFrame 子类, 行容器的边框规则会串到内部数字框(数字框被描边)。
         用本类名做选择器后规则只命中行本身。
      2. 高亮线画在 paintEvent 里而不是加边框控件 —— 加控件会挤动行内布局,
         拖动时每换一个目标就重排一次, 看起来在抖。
    """
    _hl_top = False
    _hl_bottom = False

    def setDragging(self, dragging):
        """拖动中: 自身变半透明(旧版 DraggableRow.setDragging 同款, opacity 0.25)
        不做的话拖动源行与静止行看不出区别, 拖的是哪一行得靠猜"""
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        if dragging:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.25)
            self.setGraphicsEffect(eff)
        else:
            self.setGraphicsEffect(None)

    def setHighlight(self, top=False, bottom=False):
        self._hl_top, self._hl_bottom = top, bottom
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        if not (self._hl_top or self._hl_bottom):
            return
        from PySide6.QtGui import QPainter, QPen
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, False)
            p.setPen(QPen(QColor(Colors.BLUE), 2, Qt.SolidLine))
            if self._hl_top:
                p.drawLine(8, 1, self.width() - 8, 1)
            if self._hl_bottom:
                p.drawLine(8, self.height() - 2, self.width() - 8, self.height() - 2)
            p.end()
        except Exception:
            pass


def _line():
    f = QFrame()
    f.setFixedWidth(1)
    set_bg(f, rgba_of(Colors.DIM, 0.32))
    return f


# 数字框宽度按内容算: 固定宽会让位数不同的值互相迁就(0.05 占半格、10.0 顶满格),
# 统一写死时大值撑破行动行。按内容度量加内边距, 各行各栏自适应, 文本一变就重算。
# 另外要显式 setFixedWidth: QDoubleSpinBox 默认 minimumSizeHint 宽 117,
# 两个框累加就把行动行顶到 380 > 中栏视口 344, 撑破中栏。
# 单位不进输入框(进框就成了能被光标选中改写的输入文本), 调用处另接 _make_label 单位标签。
def _fit_spin(s):
    #宽度 = 当前文字宽 + 8 呼吸, 下限 40(框的存在感); textChanged 时重算, 大值不截断
    fm = QFontMetricsF(s.font())
    s.setFixedWidth(max(40, int(fm.horizontalAdvance(s.text())) + 8))


def bind(a, key, cast=None):
    """控件值 → 回写动作/任务 dict 字段的回调, 全包唯一来源。

    原先每个控件各写一份 `lambda v, aa=a: aa.__setitem__(key, v)`, 同形不同键;
    cast 给需要换算的字段用(如跳转下拉: 选项文字 -> 序号)。多带的参数吞掉,
    防止某个信号多传一个参数时炸。"""
    def _on(v, *_):
        a[key] = cast(v) if cast else v
    return _on


def _spin(val, lo=0, hi=999, dec=1, step=0.1, on=None, fill=False):
    """fill=True 用 spin_fill(填底+微妙描边, HTML .num 同款);
    fill=False 用 spin_flat(透底无框, 行内已铺底时用)"""
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(dec)
    s.setSingleStep(step)
    s.setValue(val)
    s.setFont(FONT_M)
    _fit_spin(s)
    s.textChanged.connect(lambda _t, sp=s: _fit_spin(sp))
    # 水平方向 Fixed: QDoubleSpinBox 的 minimumSizeHint 默认要 117px(给三位数+箭头),
    # 父布局按它算下限, 两个框累加就把行动行顶到 380 > 视口 344。Fixed 策略把
    # 宽度诉求交给 setFixedWidth, 父布局不再按 minimumSizeHint 预留。
    s.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    s.setFixedHeight(26)
    if fill:
        spin_fill(s)       # 任务卡/设置页: 填底+描边(HTML .num)
    else:
        spin_flat(s)       # 动作行内: 透底(行底已有底色)
    if on:
        s.valueChanged.connect(on)
    return s


def _plain(kind="h"):
    # 透明容器 + 布局唯一工厂, kind = "h" 横排 / "v" 竖排 / "g" 网格
    # 必须是合法声明"background: transparent": 裸 "transparent" 不是 QSS, Qt 解析不到
    # 背景规则, 一旦该控件 autoFillBackground=True(被 QScrollArea 托管的页面就是)就
    # 回落到调色板白底 —— 设置页不管什么主题背景都是白的, 根子在这。
    w = QWidget()
    w.setStyleSheet("background: transparent")
    if kind == "v":
        return w, QVBoxLayout(w)
    if kind == "g":
        return w, QGridLayout(w)
    return w, QHBoxLayout(w)


def _dash():
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"border-top: 1px dashed {rgba_of(Colors.DIM, 0.45)}; background: transparent;")
    return f


def _hint(m, text, sticky=False):
    """把提示发到主窗的常驻提示条(录制回显用, 不走 toast)

    录制回显每 15ms 一次, toast 会堆定时器; 而 Model 不该持有具体窗口,
    所以经 m._main_win 中转, 没挂窗口时静默。
    """
    w = getattr(m, "_main_win", None)
    if w is not None and hasattr(w, "_hint"):
        w._hint(text, sticky)


def _take_recording(m):
    """有录制会话就取消它并提示; 返回 True = 本次入口到此为止。

    键录 / 点录 / 框选三个入口共用同一段"再次点选=取消上一次"逻辑。"""
    if not getattr(m, "_recording", None):
        return False
    m._recording()                  # 再次点选 = 取消上一次
    m._recording = None
    m.on_toast("已取消录制")
    return True


def _record_key(m, _reader=None):
    """录组合键: 按住的键实时回显, 全松开写进当前任务

    _reader 是给测试注入的假按键读取器(测试不可能在运行中的桌面真按键盘);
    正常路径不传, 走 GetAsyncKeyState。
    """
    from .capture import capture_keys
    if _take_recording(m):
        return
    _hint(m, "按下按键，全部松开完成绑定")

    last = {"t": ""}

    def _upd(combo):
        # 回显当前按下的组合。必须走粘性 hint: capture_keys 每 15ms 报一次,
        # 换成 toast 会堆几十个回收定时器并疯狂闪烁。
        txt = combo_name(combo, sep=" ") or "…"
        if txt != last["t"]:
            last["t"] = txt
            _hint(m, f"⏳ {txt}  (全部松开完成)", sticky=True)

    def _done(combo):
        m._recording = None
        _hint(m, "")            # 收掉粘性回显
        if not combo:
            m.on_toast("未捕获到按键")
            return
        if len(combo) == 1:
            # 单键: 存原始 vk + 可读显示名。不能回退成 "K" —— 表外键(F13~F24、
            # 媒体键)按显示名反查会录成完全不相干的另一个键。
            m.add_action(key=_vk_name(combo[0]), vk=combo[0])
        else:
            m.add_combo(combo)
        m.refresh()
        m.on_toast(f"已录入 {combo_name(combo)}")

    m._recording = capture_keys(on_update=_upd, on_done=_done, _reader=_reader)


def _record_click(m):
    """录点击坐标: 遮罩全屏, 点到哪儿就存哪儿"""
    from .capture import capture_click
    from PySide6.QtWidgets import QApplication
    if _take_recording(m):
        return
    win = m._main_win

    def _done(act):
        m._recording = None
        m.add_click(act["x"], act["y"], delay=act.get("delay", 0.5),
                    hold=act.get("hold", 0), rel=act.get("rel", False),
                    sx=act.get("sx"), sy=act.get("sy"))
        m.refresh(panes=("mid",), mini=False)
        m.on_toast(f"已录入坐标 ({act['x']}, {act['y']})")

    m._recording = capture_click(win, on_done=_done)


def _box_start(m, name):
    """框选的公共入口。返回是否可以开始。

    两个占用源都要看:
      m._recording    键位/坐标录制的会话句柄, 有就先取消它
      vision_capture  框选自己的 _BUSY(它在遮罩打开期间自置)
    只看前者会漏 —— 遮罩已经打开时再点, 新遮罩会叠上去, 旧的关不掉。
    """
    from .vision_capture import _busy, _end
    # 录制会话与框选占用是两回事, 彼此不借用对方的字段:
    # 早先让框选复用 m._recording 做"进行中"标记, 结果框选取消时那个占位
    # lambda 永远不被清掉, 之后点键鼠录制会被误判成"正在录制"而直接 return
    # —— 表现就是按了键但动作栏不加行。
    if _take_recording(m):
        return False
    if _busy():
        _end()                 # 上一次框选的遮罩没走完, 释放状态
        m.on_toast("上一次框选未结束, 已中断")
        return False
    m.on_toast(f"拖动框出{name}区域, ESC 取消")
    return True


def _box_go(m, name, add):
    """框选入口唯一实现(模板 / 读数共用): 占用检查 → 取主窗 → 派发给对应 add_*。

    完成与取消都由 vision_capture 收尾, 不占录制字段。"""
    if not _box_start(m, name):
        return
    win = m._main_win
    if win is None:
        m.on_toast("窗口未就绪, 无法框选")
        return
    add(win, m)


def _box_template(m):
    """等图像: 全屏框选 -> 截存模板 -> 插入等图像行"""
    from .vision_capture import add_image_wait_action
    _box_go(m, "模板", add_image_wait_action)


def _box_ocr(m):
    """读数: 全屏框选读数区 -> 插入读数行"""
    from .vision_capture import add_ocr_read_action
    _box_go(m, "读数", add_ocr_read_action)


def _row_box(lab, ctrl):
    """标签在左、控件在右占满一行 —— 用于只读展示(如写入哪个变量)"""
    w, wl = _plain()
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(8)
    wl.addWidget(_make_label(lab, color=Colors.TEXT2))
    wl.addStretch()
    wl.addWidget(ctrl)
    return w


def _dash_row(lab, opts, cur, on):
    # 标签 — 虚线 — 下拉, 三段占满整行
    w, wl = _plain()
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(8)
    wl.addWidget(_make_label(lab, color=Colors.TEXT2))
    wl.addWidget(_dash(), 1)
    # 下拉引用正源 keyboard_mode._mini_combo(内部即 _make_menu_combo +
    # setCurrentText, 后者走 _pick 正常选中路径, 不像 setText 会把显示锁死在初值)
    c = _mini_combo(opts, cur, 120, h=22)
    c.currentTextChanged.connect(on)
    wl.addWidget(c)
    return w


def _seg_block(lab, items, cur, on):
    # 小节标签在上 + 分段胶囊在下(与「分支选择」同形态同 normal 档), 组内紧、组间由卡 spacing 管
    w = QWidget()
    wl = QVBoxLayout(w)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(GAP)
    wl.addWidget(_make_label(lab, color=Colors.TEXT2))
    wl.addWidget(segmented_control(items, cur, on, size="normal"))
    return w


def _grip():
    g = QWidget()
    g.setFixedSize(10, 18)
    set_bg(g, "transparent")
    lay = QVBoxLayout(g)
    lay.setContentsMargins(2, 4, 2, 4)
    lay.setSpacing(2)
    for _ in range(3):
        r, rh = _plain()
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(2)
        for _ in range(2):
            d = QFrame()
            d.setFixedSize(3, 3)
            d.setStyleSheet(dot_qss(Colors.DIM, radius=1))
            rh.addWidget(d)
        lay.addWidget(r)
    return g


def _card(radius=9, margins=(12, 10, 12, 12), spacing=9, title=None,
          bg=None, extra="", kind="v"):
    """卡片唯一工厂 —— 右栏配置卡 / 任务卡 / 设置页卡 / 迷你窗 chip 共用,
    彼此只差圆角、边距、间距、标题与排布方向这几个参数, 不再各写一份构造。
    参数记进 f._card_p, 换态(选中/运行)用 _restyle_card 重刷, 不手拼第二份 QSS。
    kind = "v" 卡内竖排(标题在上) / "h" 横排(chip: 状态点 + 名字)。"""
    f = CardBox()
    if bg is None:
        bg = Colors.ACCENT   # 调用期取当前主题 —— 写进默认参数会在导入期固化成旧色
    f._card_p = dict(radius=radius, bg=bg)
    _restyle_card(f, extra)
    lay = QHBoxLayout(f) if kind == "h" else QVBoxLayout(f)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    if title is not None:
        lay.addWidget(_make_label(title, font=FONT_B))
    return f, lay


def _restyle_card(f, extra=""):
    # 按建卡时记下的参数重刷样式 —— 选中态/运行态换色都走这一处
    p = f._card_p
    f.setStyleSheet(card_qss(p["bg"], radius=p["radius"], sel="CardBox", extra=extra))


def _sel_border(sel):
    """选中描边 —— 透明边框常驻, 选中只换颜色(正源 .task / .act 同一写法)

    正源: .task{border:1.5px solid transparent} + .task.sel{border-color:var(--blue)}
    透明边框一直占着那 1.5px, 于是选中/未选中的盒子尺寸完全一致。
    若只在选中时才加 border, 卡片会凭空长高 3px, 下面所有卡片跟着位移 ——
    排布被选中动作本身搅动。动作行同理(正源 .act 也是 transparent 占位)。"""
    return f"border: 1.5px solid {Colors.BLUE if sel else 'transparent'};"


def _badge(text, width=None, font=FONT_B, height=26, bg=None,
           color="", border="", padding=""):
    """行内徽章唯一工厂 —— 键位块 / 分支名 / 变量名 / 跳转 共用一套圆角底 + 居中字,
    彼此只差字体、底色、描边与内边距, 不再各写一份 QLabel + card_qss。
    width 给了就定宽(键位块 28 / 左键 46), 不给则按文字自适应、只定高。
    不加 padding 的徽章要给 width: 固定宽 28 放不下 padding + 文字,
    padding 会把字挤成半个圆角块(实测)。"""
    if bg is None:
        bg = Colors.ACCENT   # 同 _card: 主题色必须在调用期取, 不能进默认参数
    extra = f"color: {color};" if color else ""
    if border:
        extra += f" border: 1px solid {border};"
    if padding:
        extra += f" padding: {padding};"
    b = QLabel(text)
    b.setFont(font)
    if width is not None:
        b.setFixedSize(width, height)
    else:
        b.setFixedHeight(height)
    b.setAlignment(Qt.AlignCenter)
    b.setStyleSheet(card_qss(bg, radius=6, sel="QLabel", extra=extra))
    return b


# ══════════ 左栏: 预设 + 任务卡 + 添加块 ══════════
def _bind_rebuild(col, fn):
    # 栏把重建函数挂给 Model 调用 —— 三栏唯一写法(fn 签名 fn(col, m))
    col.rebuild = lambda mm: fn(col, mm)


def build_left(m):
    col = QWidget()
    set_bg(col, "transparent")
    outer = QVBoxLayout(col)
    outer.setContentsMargins(PAD, PAD, PAD, PAD)
    outer.setSpacing(GAP)

    row, rl = _plain()
    rl.setContentsMargins(0, 0, 0, 0)
    rl.setSpacing(8)
    # 预设列表直接读 presets.json —— 下拉里列的是文件里真有的名字, 不是硬编码
    from config.presets import load_presets as _lp
    _names = list(_lp().keys()) or ["深渊"]
    # 逐条操作(载入/删除)做成每行一对、右对齐的文字按钮放进弹层: 行内塞不下第 3 颗
    # 按钮(3×64 + 3×8 + 下拉90 = 306 > 左栏内容宽 234), 也不占行宽。
    # 删除那颗走 .btn.danger 配色(HTML 同款): 红字, 悬停红底白字。
    combo = _make_menu_combo(
        _names, width=90,
        row_actions=[("载入", lambda n: _load_preset(m, n)),
                     ("删除", lambda n: _delete_preset(m, n),
                      dict(fg=Colors.RED, hover=Colors.RED, hover_fg="#ffffff"))])
    m.preset_name = _names[0]
    combo.currentTextChanged.connect(lambda v: setattr(m, "preset_name", v))
    m._preset_combo = combo   # 删除后靠它刷新条目 —— combo 建在本层作用域, 回调里取不到
    # 下拉定长撑满到保存钮前(HTML .selbox{flex:1}), 行内不留空
    combo.setMinimumWidth(90)
    combo.setMaximumWidth(1 << 24)
    combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    rl.addWidget(combo, 1)
    b_save = _make_btn("保存", height=28)
    # 下拉吃满剩余后按钮只剩 34px(纯字宽, QSS 里没 padding) —— 给到 HTML .btn 同档的呼吸位
    b_save.setMinimumWidth(60)
    b_save.clicked.connect(lambda: _save_preset(m))
    rl.addWidget(b_save)
    outer.addWidget(row)

    body = QWidget()
    set_bg(body, "transparent")
    outer.addWidget(body, 1)
    col._body = body
    _bind_rebuild(col, _rebuild_left)
    _rebuild_left(col, m)
    return col, combo


def _rebuild_left(col, m):
    bl = col._body
    lay = bl.layout()
    if lay is None:
        lay = QVBoxLayout(bl)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(GAP)
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w:
            w.setParent(None)
    for i, t in enumerate(m.tasks):
        lay.addWidget(_task_card(m, i, t))
    lay.addStretch(1)

    add = QFrame()
    add.setFixedHeight(58)
    add.setStyleSheet(
        f"QFrame {{ border: 1px dashed {Colors.DIM}; border-radius: 11px; }}"
        f"QPushButton {{ background: transparent; border: none; color: {Colors.DIM}; }}")
    al = QHBoxLayout(add)
    al.setContentsMargins(0, 0, 0, 0)
    tip = QPushButton("＋ 点击添加任务")
    tip.setFont(FONT_M)
    tip.setCursor(QCursor(Qt.PointingHandCursor))
    tip.clicked.connect(lambda: (m.add_task(), m.refresh(panes=("left",))))
    al.addWidget(tip)
    al.addStretch()
    lay.addWidget(add)
    col.task_cards = [c for c in bl.findChildren(QFrame) if hasattr(c, "_set_run")]


def _preset_file():
    """读写 presets.json —— 与旧 UI 同一份文件, 所以能直接读旧预设"""
    from config.presets import load_presets, save_presets
    return load_presets, save_presets


def _save_preset(m):
    """按当前预设名落盘(引擎格式, 与旧 UI 的存法一致, 旧版也能读新存的)"""
    from .runner import to_engine
    load_p, save_p = _preset_file()
    name = m.preset_name
    data = load_p()
    data[name] = {"tasks": [{"task_id": i + 1, "name": t["name"],
                             "actions": to_engine(t["actions"]),
                             "loop_interval": t.get("loop", 5),
                             "relation_type": t.get("rel", "独立"),
                             "max_runs": t.get("runs", 0)}
                            for i, t in enumerate(m.tasks)]}
    save_p(data)
    m.on_toast(f"已保存「{name}」({len(m.tasks)} 个任务)")


def _sel_preset(m, name):
    """下拉显示与 m.preset_name 一起切到 name —— 行内载入/删除后统一走这里。

    combo.setCurrentText 会发 currentTextChanged(那里 setattr 同步 m.preset_name);
    文本没变时不发信号, 所以 else 里手动兜底。"""
    combo = getattr(m, "_preset_combo", None)
    if combo is None:
        m.preset_name = name
    elif combo.currentText() != name:
        combo.setCurrentText(name)
    else:
        m.preset_name = name


def _delete_preset(m, name):
    """行内「删除」: 先弹确认, 确认后从 presets.json 删掉那条并同步下拉与 m.preset_name"""
    from PySide6.QtWidgets import QMessageBox
    from config.presets import load_presets, delete_preset
    if name not in load_presets():
        m.on_toast("没有可删除的预设" if name == "无预设" else f"预设「{name}」不存在")
        return
    win = getattr(m, "_main_win", None)
    mb = QMessageBox(win) if win is not None else QMessageBox()
    mb.setIcon(QMessageBox.Question)
    mb.setWindowTitle("删除预设")
    mb.setText(f"确定删除「{name}」？")
    mb.setInformativeText("删除后无法恢复。")
    b_del = mb.addButton("删除", QMessageBox.DestructiveRole)
    mb.addButton("取消", QMessageBox.RejectRole)
    mb.exec()
    if mb.clickedButton() is not b_del:
        return
    names = list(delete_preset(name).keys())
    combo = getattr(m, "_preset_combo", None)
    if combo is not None:
        combo.set_items(names or ["无预设"])   # 会静默选中第一项(不发信号)
    _sel_preset(m, names[0] if names else "无预设")
    m.on_toast(f"已删除「{name}」")
    try:
        from logger import log_info
        log_info("ui_v2.preset_delete", name)
    except Exception:
        pass


def _load_preset(m, name=None):
    """读 presets.json 并换进 Model; 不传名字就用当前选中(行内「载入」传的是那一行的名字)"""
    from .runner import from_engine_all
    load_p, _ = _preset_file()
    data = load_p()
    if not data:
        m.on_toast("presets.json 是空的")
        return
    if name is None:
        name = m.preset_name if m.preset_name in data else next(iter(data))
    if name not in data:
        m.on_toast(f"预设「{name}」不存在")
        return
    raw = data[name]
    try:
        tasks = [from_engine_all(t) for t in raw.get("tasks", [])]
    except Exception as e:
        m.on_toast(f"读取失败: {e}")
        return
    if not tasks:
        m.on_toast(f"预设「{name}」里没有任务")
        return
    m.tasks = tasks
    m.sel_task = 0
    m.sel_row = 0
    m.running = 0
    _sel_preset(m, name)   # 下拉显示跟到刚载入那条
    m.refresh()
    m.on_toast(f"已载入「{name}」({len(tasks)} 个任务)")
    try:
        from logger import log_info
        log_info("ui_v2.preset_load", f"{name} {len(tasks)} 任务")
    except Exception:
        pass


def _task_card(m, i, t):
    # 类名选择器(CardBox)只命中卡片自身。用 sel="" 裸规则实测拦不住 —— 选中态那条
    # border 仍会画进内部 QLabel(二分验证: 去掉卡片 border, 标签内长横线归零),
    # 表现就是"被选中的任务其内部元素也被框定"。构造与 QSS 都走 _card 正源。
    card, cl = _card(radius=11, margins=(13, 12, 13, 12), spacing=10,
                     extra=_sel_border(i == m.sel_task))

    r1, r1l = _plain()
    r1l.setContentsMargins(0, 0, 0, 0)
    r1l.setSpacing(0)
    nm = _make_label(t["name"], font=FONT_B)
    r1l.addWidget(nm)
    r1l.addStretch()
    dele = _make_btn("✕", height=20)
    ghost_btn(dele, hover=Colors.RED)      # ghost_btn 只设样式不返回控件
    dele.setFixedWidth(24)
    dele.clicked.connect(lambda: _del_task(m, i))
    r1l.addWidget(dele)
    cl.addWidget(r1)

    r2, r2l = _plain()
    r2l.setContentsMargins(0, 0, 0, 0)
    r2l.setSpacing(7)
    dot = QFrame()
    dot.setFixedSize(8, 8)
    dot.setStyleSheet(dot_qss(Colors.GREEN if t["run"] else Colors.DIM, radius=4))
    r2l.addWidget(dot)
    st = _make_label("运行中" if t["run"] else "就绪",
                     color=Colors.GREEN if t["run"] else Colors.DIM)
    r2l.addWidget(st)
    r2l.addStretch()
    go = _make_btn("停止" if t["run"] else "开始",
                   Colors.RED if t["run"] else Colors.GREEN,
                   hover=Colors.HOVER_RED if t["run"] else Colors.HOVER_GREEN,
                   font=F12, height=26)
    go.setMinimumWidth(64)
    go.clicked.connect(lambda: (m.toggle_one(i),
                                  m.refresh(panes=("left",), mini=False),
                                 m._mini.sync_btn() if m._mini else None,
                                 m.on_run_change(i) if getattr(m, "on_run_change", None) else None))
    r2l.addWidget(go)
    cl.addWidget(r2)

    card._dot, card._st, card._go = dot, st, go

    def _set_run(on):
        dot.setStyleSheet(dot_qss(Colors.GREEN if on else Colors.DIM, radius=4))
        st.setText("运行中" if on else "就绪")
        style_label(st, Colors.GREEN if on else Colors.DIM)
        flat_btn(go, Colors.RED if on else Colors.GREEN,
                 hover=Colors.HOVER_RED if on else Colors.HOVER_GREEN)
        go.setText("停止" if on else "开始")
    card._set_run = _set_run
    card._run = t["run"]

    # 点名字/标题行/卡片空白 = 选中该任务; 删除与开始钮各自处理, 不会误触发
    pick = lambda e, k=i: _pick_task(m, k)
    for wdg in (card, r1, nm):
        wdg.mousePressEvent = pick
    return card


def _del_task(m, i):
    if not m.del_task(i):
        m.on_toast("至少保留一个任务")
        return
    m.refresh()              # 任务少了一个, 迷你窗 chip 跟着少


def _pick_task(m, i):
    if i == m.sel_task:
        return
    m.sel_task = i
    m.sel_row = 0
    m.refresh(mini=False)


# ══════════ 中栏: 工具条 + 动作行 ══════════
def _pick_dd(m, label, items, width, steps):
    """工具条下拉唯一工厂 —— 控件与分派回调一次成型(原先是三处各写一个闭包)。

    steps = [(关键词, 动作, 自收尾)], 关键词空串是兜底分支;
    自收尾=True 表示动作自己负责收尾(录制会话 / 框选链), 否则执行后统一 m.refresh()。
    文案用 setText 锁成常驻标签(combo 的 _fixed_text 会一直保持, 不必在回调里复位)。"""
    def _pick(what):
        for kw, act, self_done in steps:
            if kw and kw not in what:
                continue
            act()
            if not self_done:
                m.refresh()
            return

    c = _make_menu_combo(items, width=width, on_select=_pick)
    c.setText(label)
    return c


def build_mid(m):
    col = QWidget()
    set_bg(col, Colors.ACCENT)
    lay = QVBoxLayout(col)
    lay.setContentsMargins(PAD, PAD, PAD, PAD)
    lay.setSpacing(GAP)

    tools, tl = _plain()
    tl.setContentsMargins(0, 0, 0, 0)
    tl.setSpacing(8)

    # 添加动作区: 键鼠下拉 / 插入下拉 / 清空按钮。
    # 用下拉而不是平铺按钮 —— 选项不止一个时平铺会把工具条撑满中栏(实测三个
    # 按钮把文字压成竖排), 且新增分类必须再占一个按钮位。下拉的常驻文案只写
    # 动作大类, 具体类型在菜单里选。
    dd_kb = _pick_dd(m, "＋ 键鼠", ["⌨ 键盘", "🖱 点击"], 88,
                     [("点击", lambda: _record_click(m), True),
                      ("", lambda: _record_key(m), True)])
    dd_kb.setToolTip("添加动作: 键盘 / 鼠标点击")
    tl.addWidget(dd_kb, 1)

    dd_in = _pick_dd(m, "＋ 插入", ["📷 等图像", "🔀 分支", "↳ 跳转"], 88,
                     [("等图像", lambda: _box_template(m), True),
                      ("跳转", m.add_jump, False),
                      ("", m.add_branch, False)])
    dd_in.setToolTip("插入: 等图像(框选等待) / 分支 / 跳转")
    tl.addWidget(dd_in, 1)

    dd_var = _pick_dd(m, "＋ 变量", ["🔢 读数", "➕ 变量运算", "⚖ 条件分支"], 88,
                      [("读数", lambda: _box_ocr(m), True),
                       ("运算", m.add_var_set, False),
                       ("", m.add_cond_branch, False)])
    dd_var.setToolTip("插入: 读数(OCR写入变量) / 变量运算 / 数值条件分支")
    tl.addWidget(dd_var, 1)

    b3 = _make_btn("🗑 清空", height=28)
    flat_btn(b3, "transparent", Colors.RED, hover=Colors.RED)
    b3.clicked.connect(lambda: (m.clear_rows(),
                               m.refresh(panes=("mid", "right"), mini=False)))
    tl.addWidget(b3)
    tl.addStretch()
    lay.addWidget(tools)

    rows = QScrollArea()
    rows.setWidgetResizable(True)
    rows.setStyleSheet(scroll_qss("transparent"))
    # 纵向常显, 横向按需: 动作行多时纵向滚, 内容比视口宽时横向滚,
    # 而不是把中栏撑到内容宽(实测内容 380 > 视口 344)
    rows.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    rows.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    host = QWidget()
    set_bg(host, "transparent")
    rows.setWidget(host)
    lay.addWidget(rows, 1)
    col._host = host
    _bind_rebuild(col, _rebuild_mid)
    _rebuild_mid(col, m)
    return col


def _enable_drag(m, row, grip, i):
    """让 grip 拖动本行去排序(机制照旧版 keyboard_mode 的 _drag_start/_drop)

    拖拽源是 grip(六点把手), 不是整行 —— 整行的 mousePressEvent 已经用来"点行
    选中", 两件事抢同一个事件会顾此失彼。
    """
    from PySide6.QtGui import QDrag
    from PySide6.QtCore import QMimeData

    def drag_start(e):
        if e.button() != Qt.LeftButton:
            return
        mime = QMimeData()
        mime.setText(str(i))
        # 拖拽源必须是 row 而不是 grip: QDrag 的第一个参数决定跟鼠标走的那张
        # ghost 截图。传 grip 会截出一个小横条飘在任务框上方(用户反馈过),
        # 旧版 keyboard_mode.py:1075 是 QDrag(_row) —— ghost 是整行, 看起来
        # 是行本身在动。拖拽仍由 grip 发起, 这个参数只管 ghost。
        drag = QDrag(row)
        drag.setMimeData(mime)
        row.setDragging(True)          # 拖动中源行变半透明, 与旧版一致
        try:
            drag.exec_(Qt.MoveAction)
        finally:
            row.setDragging(False)     # 无论正常结束还是被 ESC 取消都要还原

    grip.mousePressEvent = drag_start
    row.setAcceptDrops(True)

    def clear_hl():
        for c in m._mid.findChildren(ActionRow):
            c.setHighlight()

    def _zone(e, r):
        y = e.position().y()
        h = r.height()
        if y < h * 0.5:
            return 1            # 上半
        if y > h * 0.5:
            return 2            # 下半
        return 0

    def drag_enter(e):
        if e.mimeData().hasText():
            e.acceptProposedAction()

    def drag_move(e):
        if not e.mimeData().hasText():
            return
        e.acceptProposedAction()
        clear_hl()
        z = _zone(e, row)
        row.setHighlight(top=(z in (0, 1)), bottom=(z in (0, 2)))

    def drop(e):
        clear_hl()
        if e.mimeData().hasText():
            try:
                from_idx = int(e.mimeData().text())
                z = _zone(e, row)
                to_idx = i + (1 if z == 2 else 0)
                acts = m.task()["actions"]
                if from_idx != to_idx and 0 <= from_idx < len(acts):
                    item = acts.pop(from_idx)
                    if from_idx < to_idx:
                        to_idx -= 1
                    acts.insert(to_idx, item)
                    # 拖完行号全变, 必须重建; 选中项跟着新的 index 走
                    if m.sel_row == from_idx:
                        m.sel_row = to_idx
                    m.refresh(panes=("mid", "right"), mini=False)
            except (ValueError, IndexError):
                pass
        e.acceptProposedAction()

    def drag_leave(e):
        clear_hl()

    row.dragEnterEvent = drag_enter
    row.dragMoveEvent = drag_move
    row.dropEvent = drop
    row.dragLeaveEvent = drag_leave


def _rebuild_mid(col, m):
    hl = col._host.layout()
    if hl is None:
        hl = QVBoxLayout(col._host)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(GAP)          # 走 GAP 常量, 别写死 10
    while hl.count():
        it = hl.takeAt(0)
        w = it.widget()
        if w:
            w.setParent(None)
    for i, a in enumerate(m.task()["actions"]):
        kind = a["kind"]
        if kind == "jump":
            hl.addWidget(_jump_row(m, i, a))
        elif kind in ("branch", "wait"):
            hl.addWidget(_cond_row(m, i, a))
        elif kind in ("read", "varset", "cond"):
            hl.addWidget(_var_row(m, i, a))
        else:
            hl.addWidget(_action_row(m, i, a))
    hl.addStretch(1)


def _del_row_btn(m, i):
    b = _make_btn("✕", height=22)
    ghost_btn(b, hover=Colors.RED)
    b.setFixedWidth(24)
    b.clicked.connect(lambda: (m.del_row(i),
                               m.refresh(panes=("mid", "right"), mini=False)))
    return b


def _row_base(m, i):
    # 动作行骨架 —— 键鼠/分支/变量/跳转 四类行共用同一套容器参数
    row = ActionRow()
    row.setFixedHeight(52)
    row.setStyleSheet(card_qss(Colors.CARD, radius=8, sel="ActionRow",
                               extra=_sel_border(i == m.sel_row)))
    lay = QHBoxLayout(row)
    lay.setContentsMargins(8, 0, 8, 0)
    lay.setSpacing(5)           # 7 太大: 内容 380 > 视口 344, 差 36px
    g = _grip()
    lay.addWidget(g)
    return row, lay, g


def _row_tail(m, row, lay, i, g):
    # 行收尾三件事(删除按钮 / 点行选中 / grip 拖拽) —— 四类行共用, 排在行内容之后
    lay.addWidget(_del_row_btn(m, i))
    row.mousePressEvent = lambda e, k=i: _pick_row(m, k)
    _enable_drag(m, row, g, i)      # grip 拖动排序
    return row


def _action_row(m, i, a):
    row, lay, _g = _row_base(m, i)
    # combo 行没有 key, 徽章显示 name(如 W+D) —— 定宽 28 装不下, 走自适应 + padding
    if "key" in a:
        lay.addWidget(_badge(a["key"], 46 if a["key"] == "左键" else 28))
        hold = "按住" if a["key"] == "左键" else "持续"
    else:
        lay.addWidget(_badge(a.get("name", a["kind"]), font=FONT_B,
                             padding="0 10px"))
        hold = "持续"
    lay.addStretch(1)          # 弹性空隙: 把参数组推到行右端
    for lab, key in ((hold, "a"), ("后延", "b")):
        lay.addWidget(_make_label(lab, color=Colors.TEXT2))
        #单位是独立标签(不可选中, 与标注字同 FONT_M), 不塞进输入框
        lay.addWidget(_spin(a[key], 0, 999, 1, 0.1,
                            on=bind(a, key)))
        lay.addWidget(_make_label("s", color=Colors.DIM))
    return _row_tail(m, row, lay, i, _g)


def _cond_row(m, i, a):
    """条件等待行 —— 「分支」与「等图像」共用。

    两者右栏都是等待条件 / 超时 / 超时后 / 分支选择, 配置形态一致, 所以共用一个
    行渲染(徽章文案取各自的 name)。
    """
    row, lay, _g = _row_base(m, i)
    lay.addWidget(_badge(f"⑂ {a['name']}", font=FONT_M, bg=rgba_of(Colors.BLUE, 0.14),
                         color=Colors.BLUE, border=rgba_of(Colors.BLUE, 0.45),
                         padding="0 10px"))
    lay.addStretch(1)
    lay.addWidget(_make_label("等待条件配置在右侧", color=Colors.DIM))
    return _row_tail(m, row, lay, i, _g)


def _var_row(m, i, a):
    """变量类动作行 —— 读数 / 变量运算 / 条件分支, 参数在右栏配"""
    row, lay, _g = _row_base(m, i)
    icon, tint = _VAR_STYLE[a["kind"]]
    lay.addWidget(_badge(f"{icon} {a['name']}", font=FONT_M, bg=rgba_of(tint, 0.14),
                         color=Colors.TEXT, border=rgba_of(tint, 0.4),
                         padding="0 10px"))
    lay.addStretch(1)
    lay.addWidget(_make_label("配置在右侧", color=Colors.DIM))
    return _row_tail(m, row, lay, i, _g)


def _jump_row(m, i, a):
    """跳转行 —— 目标序号在右栏配置, 行内只给徽章与说明"""
    row, lay, _g = _row_base(m, i)
    lay.addWidget(_badge("⤴ 跳转", font=FONT_M, bg=rgba_of(Colors.DIM, 0.14),
                         color=Colors.TEXT2, border=rgba_of(Colors.DIM, 0.4),
                         padding="0 10px"))
    lay.addStretch(1)
    lay.addWidget(_make_label("跳转目标配置在右侧", color=Colors.DIM))
    return _row_tail(m, row, lay, i, _g)


def _pick_row(m, i):
    m.sel_row = i
    m.refresh(panes=("mid", "right"), mini=False)


# ══════════ 右栏: 随中栏选中在任务设置/分支配置之间切换 ══════════
def build_right(m):
    col = QWidget()
    set_bg(col, "transparent")
    lay = QVBoxLayout(col)
    lay.setContentsMargins(PAD, PAD, PAD, PAD)
    lay.setSpacing(GAP)
    stack = QStackedWidget()
    stack.setStyleSheet("background: transparent")
    lay.addWidget(stack, 1)
    col._stack = stack
    _bind_rebuild(col, _rebuild_right)
    _rebuild_right(col, m)
    return col


def _rebuild_right(col, m):
    st = col._stack
    while st.count():
        w = st.widget(0)
        st.removeWidget(w)
        w.setParent(None)
    acts = m.task()["actions"]
    a = acts[m.sel_row] if acts else None
    # 三个页都要建, 下标固定: 0=任务设置 1=条件配置(分支/等图像) 2=跳转配置。
    # 只 add 其中一个再 setCurrentIndex 会越界/落到空处 —— 索引按加入顺序算。
    st.addWidget(_page_task(m))
    st.addWidget(_page_branch(m, a)
                 if (a and a["kind"] in ("branch", "wait")) else _page_task(m))
    st.addWidget(_page_jump(m, a) if (a and a["kind"] == "jump") else _page_task(m))
    st.addWidget(_page_var(m, a)
                 if (a and a["kind"] in ("read", "varset", "cond")) else _page_task(m))
    kind = a["kind"] if a else ""
    st.setCurrentIndex({"branch": 1, "wait": 1, "jump": 2,
                        "read": 3, "varset": 3, "cond": 3}.get(kind, 0))


def _page():
    # 页容器宽度交给 stack 分配: 不设边距、不设固定宽, 让它跟着 stack 走。
    # 设了最小宽度会把 QStackedWidget 顶到内容宽(实测 639), 右栏只有 385 却放不下。
    w = QWidget()
    set_bg(w, "transparent")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(GAP)
    lay.setSizeConstraint(QLayout.SetNoConstraint)   # 布局不反过来要求父容器变宽
    return w, lay


def _page_task(m):
    t = m.task()
    w, lay = _page()
    lay.addWidget(_make_label("任务设置", color=Colors.DIM))
    c, cl = _card()
    # 关系值用引擎格式 "在任务N后"(不是"任务N后") —— keyboard_task 按字面比较,
    # 格式不对会走独立分支, 依赖关系形同虚设。选项按当前任务数生成。
    rel_opts = ["独立"] + [f"在任务{k}后" for k in range(1, len(m.tasks) + 1)]
    # 对齐 HTML: label + 边框下拉框(flex:1 + ▼), 不是虚线 + 纯文字
    r_rel, rl_rel = _plain()
    rl_rel.setContentsMargins(0, 0, 0, 0)
    rl_rel.setSpacing(8)
    rl_rel.addWidget(_make_label("关系", color=Colors.TEXT2))
    cm_rel = _make_menu_combo(rel_opts, width=120)
    cm_rel.setFixedHeight(26)
    cm_rel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    cm_rel.setCurrentText(t["rel"])
    cm_rel.currentTextChanged.connect(bind(t, "rel"))
    rl_rel.addWidget(cm_rel, 1)
    cl.addWidget(r_rel)

    # 循环 / 次数 —— 对齐 HTML: label + 整数输入框(50px/26px/居中/有边框) + 独立单位标签
    # 不用 setSuffix: HTML 的 .unit 是独立的 12px 灰色标签, 不在输入框内
    r_num, rl_num = _plain()
    rl_num.setContentsMargins(0, 0, 0, 0)
    rl_num.setSpacing(8)
    rl_num.addWidget(_make_label("循环", color=Colors.TEXT2))
    rl_num.addWidget(_spin(t["loop"], 1, 999, 0, 1, fill=True,
                               on=bind(t, "loop")))
    rl_num.addWidget(_make_label("s", color=Colors.DIM))
    rl_num.addSpacing(6)
    rl_num.addWidget(_make_label("次数", color=Colors.TEXT2))
    rl_num.addWidget(_spin(t["runs"], 1, 999, 0, 1, fill=True,
                               on=bind(t, "runs")))
    rl_num.addWidget(_make_label("次", color=Colors.DIM))
    rl_num.addStretch()
    cl.addWidget(r_num)
    lay.addWidget(c)
    lay.addStretch(1)
    return w


def _page_var(m, a):
    """变量类动作的右栏配置: 读数 / 变量运算 / 条件分支"""
    w, lay = _page()
    k = a["kind"]
    if k == "read":
        lay.addWidget(_make_label("读数设置", color=Colors.DIM))
        c, cl = _card()
        cl.addWidget(_dash_row("读取区域", ["数字·计数", "数字·数值", "文本·标题"], a["src"],
                               bind(a, "src")))
        cl.addWidget(_row_box("写入变量", _make_label(a["var"], color=Colors.BLUE, font=FONT_B)))
        lay.addWidget(c)
    elif k == "varset":
        lay.addWidget(_make_label("变量运算", color=Colors.DIM))
        c, cl = _card()
        r1, rl = _plain()
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(_make_label("变量", color=Colors.TEXT2))
        rl.addWidget(_make_label(a["var"], color=Colors.BLUE, font=FONT_B))
        rl.addWidget(_make_label("运算符", color=Colors.TEXT2))
        op = _make_menu_combo(["+", "-", "×", "÷", "="], width=64)
        op.setCurrentIndex(["+", "-", "×", "÷", "="].index(a["op"]))
        op.currentTextChanged.connect(bind(a, "op"))
        rl.addWidget(op)
        rl.addWidget(_spin(a["val"], -999, 999, 1, 1,
                           on=bind(a, "val")))
        cl.addWidget(r1)
        lay.addWidget(c)
    else:
        lay.addWidget(_make_label("条件分支", color=Colors.DIM))
        c1, l1 = _card()
        r1, rl = _plain()
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(_make_label("当变量", color=Colors.TEXT2))
        rl.addWidget(_make_label(a["var"], color=Colors.BLUE, font=FONT_B))
        rl.addWidget(_make_label("满足", color=Colors.TEXT2))
        cm = _make_menu_combo([">=", "<=", "==", "!="], width=64)
        cm.setCurrentIndex([">=", "<=", "==", "!="].index(a["cmp"]))
        cm.currentTextChanged.connect(bind(a, "cmp"))
        rl.addWidget(cm)
        rl.addWidget(_spin(a["val"], -999, 999, 1, 1,
                           on=bind(a, "val")))
        l1.addWidget(r1)
        lay.addWidget(c1)
        lay.addWidget(_make_label("分支选择 · 条件判定后", color=Colors.DIM))
        c2, l2 = _card()
        seg = segmented_control([("走 Then", "then"), ("走 Else", "else")], a["then"],
                                lambda v, aa=a: aa.__setitem__(
                                    "then" if v == "then" else "else", v),
                                size="normal")
        l2.addWidget(seg)
        lay.addWidget(c2)
    lay.addStretch(1)
    return w


def _page_jump(m, a):
    w, lay = _page()
    lay.addWidget(_make_label("跳转配置", color=Colors.DIM))
    c, cl = _card()
    n = len(m.task()["actions"])
    opts = [f"第{k + 1}行 · {_row_title(act)}" for k, act in enumerate(m.task()["actions"])]
    cur = opts[max(0, min(a["to"] - 1, len(opts) - 1))] if opts else ""
    cl.addWidget(_dash_row("跳转到", opts, cur,
                           bind(a, "to", cast=lambda v: opts.index(v) + 1 if v in opts else 1)))
    c2, cl2 = _card(None)
    cl2.addWidget(_make_label(f"当前目标: 第 {a['to']} 行 / 共 {n} 行", color=Colors.DIM))
    lay.addWidget(c)
    lay.addWidget(c2)
    lay.addStretch(1)
    return w


def _row_title(a):
    """动作行标题 —— 给跳转目标下拉用, 与中栏行内显示一致"""
    if a["kind"] == "key":
        return a["key"]
    return a.get("name", a["kind"])


def _page_branch(m, a):
    w, lay = _page()
    lay.addWidget(_make_label("分支配置", color=Colors.DIM))
    c1, l1 = _card()
    hd, hl = _plain()
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    hl.addWidget(_make_label(a["name"], font=FONT_B))
    hl.addWidget(tag_label("中栏选中", Colors.BLUE, border=rgba_of(Colors.BLUE, 0.5),
                           radius=4, padding="1px 6px"))
    hl.addStretch()
    l1.addWidget(hd)
    l1.addWidget(_seg_block("等待条件", WAIT3, a["wait"],
                            bind(a, "wait")))
    r, rl = _plain()
    rl.setContentsMargins(0, 0, 0, 0)
    rl.setSpacing(8)
    rl.addWidget(_make_label("后延", color=Colors.TEXT2))
    rl.addWidget(_spin(a["delay"], 0, 999, 1, 0.1,
                       on=bind(a, "delay")))
    rl.addWidget(_make_label("s", color=Colors.DIM))
    rl.addSpacing(6)
    rl.addWidget(_make_label("超时", color=Colors.TEXT2))
    rl.addWidget(_spin(a["timeout"], 0, 999, 1, 1,
                       on=bind(a, "timeout")))
    rl.addWidget(_make_label("s", color=Colors.DIM))
    l1.addWidget(r)
    l1.addWidget(_seg_block("超时后", AFTER3, a["after"],
                            bind(a, "after")))
    lay.addWidget(c1)

    if "pick" in a:      # 分支选择只对分支有意义, 等图像没有
        lay.addWidget(_make_label("分支选择 · 条件达成后", color=Colors.DIM))
        c2, l2 = _card()
        l2.addWidget(segmented_control(PICK3, a["pick"],
                                       bind(a, "pick"),
                                       size="normal"))
        lay.addWidget(c2)
    lay.addStretch(1)
    return w
