"""
通用控件工厂 — 按钮/数字框/输入框/下拉/标签/卡片的共享样式唯一真源
(全app的控件样式只在这一处定义, 改样式=改这里; 行内禁止手搓QSS, 一律调这里的QSS生成器或工厂)
xxx_qss()生成器: 返回字符串, 供拼接/换色/带extra的场合; xxx_xxx()工厂: 直接设到控件上
"""
from PySide6.QtWidgets import QPushButton, QLabel, QWidget
from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import QCursor, QFont
from config import Colors, FONT_M, FONT_B

# QSS字体串(px单位, 只写在需要QSS字体的按钮族里; 与setFont的pt体系互不混用)
F12 = "bold 12px 'MiSans'"
F17 = "bold 17px 'MiSans'"
SPIN_ARROWS = "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; border: none; }"


# ══════════ QSS 生成器（样式字符串的唯一定义处） ══════════

def btn_qss(bg=None, fg=None, hover=None, hover_fg=None, font=None, radius=4, disabled=None, extra=""):
    """按钮底色QSS(全app按钮族唯一模板: 普通/状态/幽灵/设置页/标题栏/行内小钮全走这里)
    hover_fg单独给=悬停只变字色; radius=None=无圆角; disabled=(底色,字色)追加:disabled规则;
    extra=基础规则内追加属性(如padding/text-align)"""
    bg = bg or Colors.BLUE
    fg = fg or Colors.TEXT
    q = f"QPushButton {{ background: {bg}; color: {fg}; border: none;"
    if radius is not None:
        q += f" border-radius: {radius}px;"
    if font:
        q += f" font: {font};"
    if extra:
        q += f" {extra}"
    q += " }"
    if hover is not None or hover_fg is not None:
        h = " QPushButton:hover {"
        if hover is not None:
            h += f" background: {hover};"
        if hover_fg is not None:
            h += f" color: {hover_fg};"
        h += " }"
        q += h
    if disabled:
        q += f" QPushButton:disabled {{ background: {disabled[0]}; color: {disabled[1]}; }}"
    return q

def label_qss(color=None, font=None, bg="transparent", border=False, extra=""):
    """标签文字色QSS(_make_label/style_label/各处裸标签唯一模板)
    border=True补border:none; font=QSS字体串; extra=追加属性(如padding)"""
    q = f"color: {color or Colors.TEXT}; background: {bg};"
    if border:
        q += " border: none;"
    if font:
        q += f" font: {font};"
    if extra:
        q += f" {extra}"
    return q

def card_qss(bg=None, radius=11, sel="QFrame", extra=""):
    """卡片容器QSS(任务卡/预设栏/设置区/动作行/悬浮面板/色块共用)
    radius=None=无圆角; sel=""=裸规则只作用于本控件; extra=追加属性(如边框)"""
    bg = Colors.CARD if bg is None else bg
    q = f"background: {bg};"
    if radius is not None:
        q += f" border-radius: {radius}px;"
    if extra:
        q += f" {extra}"
    if sel:
        return f"{sel} {{ {q} }}"
    return q

def scroll_qss(bg="transparent"):
    """滚动区QSS含细滚动条三态(初始化/rebuild/任务列表三处共用);
    bg按场景: transparent=透出下层圆角底, CARD=重建路径实底, ACCENT=任务列表底"""
    return f"""
        QScrollArea {{ background: {bg}; border: none; }}
        QScrollBar:vertical {{ background: {Colors.ACCENT}; width: 6px; border-radius: 3px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {Colors.DIM}; border-radius: 3px; min-height: 30px; }}
        QScrollBar::handle:vertical:hover {{ background: {Colors.BLUE}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    """

def tip_qss(padding="16px 32px"):
    """全屏遮罩提示条QSS(框选/点击绑定两处共用; 半透明背景窗上QSS背景不渲染故为实色)"""
    return f"""
        background: {rgba_of('#1e1e1e', 220)};
        color: #fff;
        border-radius: 10px;
        padding: {padding};
        border: 2px solid {Colors.BLUE};
    """

def dot_qss(color, radius=2):
    """圆点色块QSS(状态指示灯/主题色块共用)"""
    return f"background: {color}; border-radius: {radius}px;"

def slider_qss():
    """横向滑块QSS(设置页滑块唯一定义处, 透明度/圆角共用)

    groove 不能用 ACCENT: 卡片底就是 ACCENT, 轨道会跟卡片同色而消失 ——
    值拉到端点(如圆角 0)时填充为 0, 整条轨道看不见, 只剩一个圆点。
    改用 dim@45%(与下拉描边同口径): 明暗主题都看得见, 又压得过填充色。"""
    return f"""
        QSlider::groove:horizontal {{ background: {_dim_rgba(0.45)}; height: 6px; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {Colors.BLUE}; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}
        QSlider::sub-page:horizontal {{ background: {Colors.BLUE}; border-radius: 3px; }}
    """

def menu_qss():
    """菜单弹层QSS(任务行菜单钮弹出层唯一定义处)"""
    return f"""
        QMenu {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: 1px solid {Colors.DIM}; border-radius: 4px; }}
        QMenu::item {{ padding: 4px 12px; min-height: 22px; }}
        QMenu::item:selected {{ background: {Colors.BLUE}; }}
    """

def menu_btn_qss():
    """下拉按钮QSS(全app下拉唯一样式正源)——尺寸/内边距/圆角与原 QComboBox 版逐项对齐
    (padding 2px 8px、圆角 6px、CARD 底+微妙描边), 不加三角箭头(原 QComboBox 也没有)
    对齐 HTML .selbox: 背景 CARD + 1px 描边 rgba(dim,.45)"""
    return btn_qss(Colors.CARD,
                   extra=f"padding: 2px 8px; text-align: left;"
                         f" border: 1px solid {_dim_rgba(0.45)}; border-radius: 6px;") + f"""
        QPushButton::menu-indicator {{ image: none; width: 0; height: 0; border: none; }}
    """

def titlebar_qss():
    """标题栏容器QSS(bar及子孙QWidget透明底+QLabel字色, build_titlebar唯一用)"""
    return f"QWidget {{ background-color: transparent; }} QLabel {{ color: {Colors.TEXT}; }}"


def tooltip_qss():
    """工具提示QSS(主题切换时刷给QApplication全局; 显式着色防系统暗色黑上叠黑)"""
    return f"QToolTip {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: 1px solid {Colors.BLUE}; padding: 3px 7px; border-radius: 3px; }}"


# ══════════ 控件工厂（直接设样式到实例） ══════════

def _make_btn(text, bg=None, fg=None, hover=None, font=None, height=25):
    btn = QPushButton(text)
    btn.setFont(font or FONT_M)
    btn.setFixedHeight(height)
    btn.setCursor(QCursor(Qt.PointingHandCursor))
    btn.setStyleSheet(btn_qss(bg, fg, hover or Colors.ACCENT))
    return btn

def _tint_btn(btn, bg):
    """动态按钮换底色（与 _make_btn 同款样式）：状态切换按钮专用"""
    flat_btn(btn, bg, hover=Colors.ACCENT)

def _make_label(text, font=None, color=None, extra="", align=None, parent=None):
    """标签唯一工厂 —— 全应用不再裸建 QLabel:

    font 默认 FONT_M, color 默认主题文字色(None 走 label_qss 的 TEXT),
    extra=追加 QSS(描边/内边距), align=对齐, parent=挂到谁名下。"""
    lbl = QLabel(text, parent)
    lbl.setFont(font or FONT_M)
    if align is not None:
        lbl.setAlignment(align)
    lbl.setStyleSheet(label_qss(color, extra=extra))
    return lbl


def tip_label(parent, text="", padding="16px 32px", font=FONT_B):
    """全屏提示条标签唯一工厂 —— 框选绑定 / 图像框选 / 主窗提示 共用,
    tip_qss 只在这一处上身(别处不要再拿 QLabel 手拼提示条)。"""
    return _make_label(text, font=font, align=Qt.AlignCenter,
                       extra=tip_qss(padding), parent=parent)


def tag_label(text, color, bg="", border="", radius=4, padding="1px 6px", bold=False):
    """描边小标签唯一工厂 —— 中栏选中 / MINI 角标 / 快捷键位块 共用一套
    底色 + 描边 + 圆角 + 内边距, 差异只走参数, 不再各拼一份 label_qss。"""
    extra = f"background: {bg};" if bg else ""
    if border:
        extra += f" border: 1px solid {border};"
    extra += f" border-radius: {radius}px; padding: {padding};"
    if bold:
        extra += " font-weight: bold;"
    return _make_label(text, color=color, extra=extra)


def hit_btn(parent, on_click=None):
    """透明点击热区唯一工厂 —— 不能 addWidget 进布局: QPushButton 的 sizeHint 会把
    宿主顶宽(实测 88px 格子被顶成整行), 所以不入布局, 由调用方按宿主几何铺开。"""
    b = QPushButton(parent)
    b.setFlat(True)
    b.setStyleSheet("background: transparent")
    b.setCursor(QCursor(Qt.PointingHandCursor))
    if on_click is not None:
        b.clicked.connect(on_click)
    return b

def state_btn(btn, bg, fg=None, hover=None):
    """17px大状态按钮底色(任务开始/停止、全部控制、暂停条共用)"""
    btn.setStyleSheet(btn_qss(bg, fg, hover, font=F17))

def flat_btn(btn, bg, fg=None, hover=None):
    """常规按钮底色(迷你窗/设置页等, 字体走setFont不在QSS里)"""
    btn.setStyleSheet(btn_qss(bg, fg, hover))

def ghost_btn(btn, hover=None, hover_fg=None):
    """透明幽灵按钮底色(画布提示/删除确认钮, 各变体共用)"""
    if not hover:
        hover, hover_fg = None, None
    else:
        hover_fg = hover_fg or Colors.TEXT
    btn.setStyleSheet(btn_qss("transparent", Colors.DIM, hover, hover_fg, font=F17, radius=None))

def rgba_of(color, alpha):
    """主题色转半透明 rgba 串(QSS 用), alpha 是不透明度(0=全透, 1=满实)
    颜色换算只此一处, 其它地方不要手拼 rgba(r,g,b,a)"""
    from PySide6.QtGui import QColor
    c = QColor(color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"



# ── 主题换肤: 把建窗时用 f-string 烤死的 QSS 里的主题色顶掉 ──
_THEME_KEYS = ("CARD", "ACCENT", "BLUE", "GREEN", "RED", "YELLOW",
               "TEXT", "TEXT2", "DIM", "HOVER_GREEN", "HOVER_RED")


def palette_now():
    """当前主题色快照 —— 换肤前后各取一次, 差集就是要顶掉的旧色"""
    from config import Colors
    return {k: getattr(Colors, k, "") for k in _THEME_KEYS}


def _rgb_of(hexs):
    """#rrggbb -> "r,g,b"(样式表 rgba() 里用的就是三元组)"""
    h = hexs.lstrip("#")
    if len(h) != 6:
        return ""
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def restyle_tree(w, old, new):
    """把 w 整棵子树里用旧主题色拼死的样式表换成新主题色。

    各控件的 QSS 是建窗时用 Colors 拼的字符串, 换主题不会自己跟随 ——
    不做这步只有 paintEvent 实时读 Colors 的窗口底色会变, 表现为"只变了一小部分"。
    property("keepColor") 的控件跳过: 主题色卡每枚都必须保持自己主题的颜色。
    """
    try:
        if w.property("keepColor"):
            return
    except Exception:
        pass
    ss = w.styleSheet()
    if ss:
        s = ss
        for key in _THEME_KEYS:
            o, n = old.get(key), new.get(key)
            if o and n and o != n:
                s = s.replace(o, n).replace(_rgb_of(o), _rgb_of(n))
        if s != ss:
            w.setStyleSheet(s)
    for c in w.children():
        if isinstance(c, QWidget):
            restyle_tree(c, old, new)
    w.update()

def _dim_rgba(alpha):
    # DIM 色的半透明写法(HTML .num/.selbox 的描边就是 rgba(dim, .32/.45))
    return rgba_of(Colors.DIM, alpha)


def spin_fill(spin):
    """数字框填底样式(任务卡片循环/次数、设置页默认值)
    对齐 HTML .num: 背景 CARD(与面板同色) + 1px 微妙描边 + 圆角 5px ——
    不是 border:none 的裸框, 也不是 spin_flat 的透底; 描边是控件唯一的视觉边界"""
    spin.setStyleSheet(
        f"QDoubleSpinBox {{ background: {Colors.CARD}; color: {Colors.TEXT};"
        f" border: 1px solid {_dim_rgba(0.45)}; border-radius: 5px;"
        f" padding: 0px 5px; }} {SPIN_ARROWS}")

def spin_flat(spin):
    """数字框透底样式(动作设置页/任务卡片行内输入)"""
    spin.setStyleSheet(f"QDoubleSpinBox {{ background: transparent; color: {Colors.TEXT}; border: none; padding: 0px; }} {SPIN_ARROWS}")

def line_flat(le):
    """文本输入透底样式(任务卡片行内输入, 与 spin_flat 同款; 行底已是ACCENT故不铺底)"""
    le.setStyleSheet(f"QLineEdit {{ background: transparent; color: {Colors.TEXT}; border: none; padding: 0px 2px; }}")

def line_fill(le, padding="2px 8px"):
    """文本输入填底样式(卡片级输入: 任务名/设置页标题, 与 spin_fill 同族)"""
    le.setStyleSheet(f"QLineEdit {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: none; border-radius: 4px; padding: {padding}; }}")

def style_label(lbl, color=None):
    """标签文字色+透明底(全app状态文字共用)"""
    lbl.setStyleSheet(label_qss(color))

def set_bg(w, color):
    """容器底色一行式(transparent/CARD/rgba等纯背景切换共用)"""
    w.setStyleSheet(f"background: {color};")


class WheelScrollFilter(QObject):
    """滚轮转发过滤器：光标在数字框/输入框等可交互控件上时, 滚轮不再增减控件的值,
    而是转去滚动所在页面(用户原意是滚页面, 不是改数字)。
    装法: app.installEventFilter(WheelScrollFilter(app))"""
    # 这些控件会自己吃掉滚轮(改数值/换选项), 需要把滚轮转给页面。
    # 按 isinstance 判基类, 不按类名字符串——后者会漏: 如 QSlider 的 type().__name__
    # 是 "QSlider" 而基类名是 "QAbstractSlider", 字符串匹配必然对不上
    @staticmethod
    def _eats_wheel(obj):
        from PySide6.QtWidgets import (QAbstractSpinBox, QLineEdit, QComboBox, QTextEdit,
                                       QPlainTextEdit, QAbstractSlider, QAbstractItemView)
        return isinstance(obj, (QAbstractSpinBox, QLineEdit, QComboBox, QTextEdit,
                                QPlainTextEdit, QAbstractSlider, QAbstractItemView))

    def __init__(self, target):
        super().__init__()
        self.target = target

    def _page_scrollbar(self, obj):
        """从控件往上找所属的 QScrollArea, 返回它的竖向滚动条(找不到返回 None)"""
        from PySide6.QtWidgets import QScrollArea
        p = obj.parent()
        while p is not None:
            if isinstance(p, QScrollArea):
                return p.verticalScrollBar()
            p = p.parent()
        # 不在滚动区里(悬浮编辑页等)则用主窗口的滚动条
        kb = getattr(self.target, "_keyboard_scroll", None)
        return kb.verticalScrollBar() if kb is not None else None

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if ev.type() != QEvent.Wheel:
            return False
        # 只拦"会吃滚轮的控件"; QPushButton 类下拉不吃滚轮, 天然冒泡到页面, 不用管
        if not self._eats_wheel(obj):
            return False
        if getattr(obj, "_wheel_pass", False):      # 转发的滚轮别再被自己拦一次
            return False
        bar = self._page_scrollbar(obj)
        if bar is None:
            return False
        delta = ev.angleDelta().y()
        if delta == 0:
            delta = ev.pixelDelta().y()          # 触控板
        if delta == 0:
            return False
        step = max(1, bar.singleStep()) * 3
        bar.setValue(bar.value() - (delta // 120) * step if abs(delta) >= 120
                     else bar.value() - delta // 40 * step // 3)
        return True          # 吃掉事件: 控件值不变