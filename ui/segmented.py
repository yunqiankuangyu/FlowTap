"""
分段选择器: 一排**连成一体**的档位按钮(原版/精确/平衡/粗略这类离散档位)。

视觉: 外层胶囊底 + 一个药丸滑块, 选中态由滑块位置表达, 点击时滑块平滑移动过去。
     按钮本身只管文字, 底色交给滑块绘制——一套 QSS 撑不起跨控件的滑动动画。
样式正源在这里, 别处直接调 segmented_control() 构造, 不另写一份。
字体走 widgets.F12 / config.FONT_M, 与全app按钮族同一套, 不在此处自创字号。
"""
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PySide6.QtGui import QFont, QFontMetricsF, QCursor, QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QPushButton, QWidget, QFrame

from config import Colors
from .widgets import btn_qss

# 三档尺寸, 按宿主行的行高选, 不按控件自己方便选:
#   行高是宿主定的(设置页 24px / 动作行 20px), 胶囊总高必须塞得进去,
#   否则上下溢出压到相邻行的标签上(实测 36px 胶囊在 24px 行里溢出 12px)。
# 每档四项: (药丸高, 留白, 描边, 字号)。留白/描边随档缩, 不是固定值——
# 小档若沿用 3px 留白 + 2px 描边, 两者就吃掉 10px, 药丸只剩 14px。
# 外框总高 = 药丸 + 留白*2 + 描边*2
SIZES = {
    "settings": (14, 1, 1, 11),   # 设置页开关行(行高24) -> 总高 18
    "compact":  (20, 2, 2, 11),   # 动作行内(行高20 起) -> 总高 28
    "normal":   (28, 3, 2, 12),   # 悬浮设置页(行高充足)-> 总高 36
}
ANIM_MS = 180        # 滑块移动时长
# 段宽额外留白也随档缩, 与字号匹配
SEG_GAP = {"settings": 14, "compact": 20, "normal": 28}


def _geom(size):
    """按档位推 (药丸圆角, 外框圆角, 外框总高, 药丸高, 留白, 描边, 字号, 段留白)。
    外框圆角 = 药丸圆角 + 留白 + 描边, 这样描边与药丸的弧线才平行。"""
    seg_h, pad, border, pt = SIZES[size]
    pill_r = seg_h // 2          # 全圆端 = 真正的胶囊
    track_r = pill_r + pad + border
    track_h = seg_h + pad * 2 + border * 2
    return pill_r, track_r, track_h, seg_h, pad, border, pt, SEG_GAP[size]


def _seg_font_qss(pt=12):
    """段内文字样式: 与F12 同字体, 非粗体, 字号可调。

    不直接复用 widgets.F12——那个带 bold, 而"非粗体"正是这里要的差异;
    就地改 F12 的字重串也不干净(F12 是全app 共用常量)。段宽按此字体度量。
    紧凑档传 11, 与行内其他控件同字号。
    """
    return f"{pt}px 'MiSans'"


def _seg_track_qss(track_r, border=2):
    """外层胶囊底: 卡底 + 粗描边 + 大圆角。

    选择器必须写 QFrame——早前误用 btn_qss 生成 QPushButton 规则, 套在 QFrame 上
    选择器不匹配, 整条规则被忽略, 外框直接消失。

    描边: 标准档 2px(1px 在浅色主题下几乎看不见, 控件像没边框);
    小档 1px——留白和描边都按档位缩, 见 SIZES。
    """
    return (f"QFrame {{ background: {Colors.CARD};"
            f" border: {border}px solid {Colors.DIM};"
            f" border-radius: {track_r}px; }}")


def _seg_colors():
    """(滑块底色, 未选中字色, 选中字色)

    底色不用 Colors.ACCENT——各主题的 ACCENT 都比 CARD 浅(如清新绿 #c8e0c8 vs #d8edd8),
    直接铺底会发灰发淡, 看着像没选中。这里用 GREEN 做选中底: 每个主题都有,
    且与 ACCENT 同为深色系, 在浅色主题下对比同样清楚。
    """
    return (Colors.GREEN, Colors.TEXT2, Colors.TEXT)


    class _TrackWatch(QFrame):
        """外层轨道。额外挂 resizeEvent: 布局重新分配必然伴随 resize,
        药丸据此重定位。QLayout 没有"布局定稿"信号可用, resize 是最接近的钩子。"""

        relayoutRequested = Signal()

        def resizeEvent(self, e):
            super().resizeEvent(e)
            self.relayoutRequested.emit()


class _TrackWatch(QFrame):
    """外层轨道。额外挂 resizeEvent: 布局重新分配必然伴随 resize,
    药丸据此重定位。QLayout 没有"布局定稿"信号可用, resize 是最接近的钩子。"""

    relayoutRequested = Signal()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.relayoutRequested.emit()


class _Pill(QWidget):
    """滑块药丸: 自绘圆角矩形, 用几何动画在段之间移动。

    geometry 由 Qt 动画驱动, paintEvent 直接画 self.geometry()——不再另存 _rect,
    否则 setGeometry 覆盖与 QPropertyAnimation 会互相打乱, 药丸跳位。
    """

    def __init__(self, parent=None, radius=14):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 不拦鼠标
        self._bg = _seg_colors()[0]
        self._radius = radius
        self._dim = False

    def setDim(self, on):
        # 置灰。药丸是自绘控件不吃 setEnabled, 必须自己处理,
        # 否则控件整体灰了、药丸还是实色, 看着像仍可点。
        self._dim = on

    def paintEvent(self, e):
        # 只画底色, 不画描边。外层 track 已有 2px 描边, 药丸再加一圈深色描边
        # 会让两层粗细深浅都不同, 看着就是一圈粗一圈细。药丸靠底色与外框区分就够。
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        col = QColor(self._bg)
        if self._dim:
            # 置灰时压低不透明度, 让药丸退回背景层, 不再是突出的选中块
            col.setAlpha(60)
        p.setBrush(col)
        p.drawRoundedRect(self.rect(), self._radius, self._radius)
        p.end()

    def slide_to(self, rect, animate=True):
        # 动画封在药丸自身: 外层控件只给目标矩形, 不关心过程。
        if not animate:
            self.setGeometry(rect)
            return
        self._anim = QPropertyAnimation(self, b'geometry')
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(rect)
        self._anim.start()


class SegmentedControl(QWidget):
    """分段选择器。items 为 [(显示文本, 值), ...], 选中时回调 on_change(值)。
    段宽按各自文字宽度自适应, 不等分——中文字数不同, 等分会显得松散。"""

    def __init__(self, items, current, on_change=None, parent=None, size="normal"):
        super().__init__(parent)
        self._items = list(items)
        self._on_change = on_change
        self._btns = {}
        self._order = [v for _, v in self._items]
        self._current = current
        # size 决定整档几何(药丸高/留白/描边/字号), 必须按宿主行的行高选
        if size not in SIZES:
            raise ValueError(f"未知档位 {size}, 可选 {list(SIZES)}")
        self._size = size
        (self._pill_r, self._track_r, self._track_h, self._seg_h,
             self._pad, self._border, self._pt, self._gap) = _geom(size)

        # track 必须由 seg 的布局居中, 不能当无主子控件直接钉在 (0,0)。
        # 宿主行给的高度常大于 track 固定高(设置页行 24px / track 18px),
        # 无布局时 track 贴顶, 整条胶囊比同行的标签高出一截——看着就是没对齐。
        _outer = QVBoxLayout(self)
        _outer.setContentsMargins(0, 0, 0, 0)
        _outer.setSpacing(0)
        _outer.addStretch(1)

        track = _TrackWatch(self)
        # 高 = 药丸 + 上留白 + 下留白 + 上下描边。
        # 用布局 margin 而不是 contentsMargins 承载留白: QSS 边框画在框内,
        # contentsMargins 从边框内侧起算, 上留白会比下少描边宽度(实测 7 vs 3)。
        PAD = self._pad
        track.setFixedHeight(self._track_h)
        # 选择器必须是 QFrame: 早前误用 btn_qss 生成 QPushButton 规则套在 QFrame 上,
        # 选择器不匹配 -> 整条规则被忽略 -> 外框直接消失
        track.setStyleSheet(_seg_track_qss(self._track_r, self._border))
        lay = QHBoxLayout(track)
        lay.setContentsMargins(PAD, PAD, PAD, PAD)
        lay.setSpacing(0)

        self._pill = _Pill(track, self._pill_r)

        f = QFont("MiSans", self._pt)   # 非粗体: QSS 里已写非bold, 这里保持一致
        fm = QFontMetricsF(f)
        self._w = {}
        for text, val in self._items:
            b = QPushButton(text)
            b.setFixedHeight(self._seg_h)
            b.setFont(f)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setFocusPolicy(Qt.NoFocus)
            b.setFlat(True)
            b.setStyleSheet(self._btn_qss(val == current))
            bw = int(fm.horizontalAdvance(text)) + self._gap
            b.setFixedWidth(bw)
            b.clicked.connect(lambda _c=False, v=val: self._pick(v))
            self._btns[val] = b
            self._w[val] = bw
            lay.addWidget(b)
        self._track = track
        # 显式左对齐 + 垂直居中: 不给 AlignHorizontal 会默认撑满可用宽度(右侧空档),
        # 给 AlignHCenter 又会水平居中(左上角不对齐)。两者都要, 只能显式组合。
        _outer.addWidget(track, 0, Qt.AlignLeft | Qt.AlignVCenter)
        _outer.addStretch(1)
        track.relayoutRequested.connect(self._relayout_pill)
        self._refresh()

    def setEnabled(self, on):
        """整体置灰。药丸是自绘控件, 不吃 setEnabled, 要一并收掉药丸。

        置灰场景: 超时=0(∞)=永不超时 → "超时后行为"无意义, 药丸保持原色会让人以为还能点。
        """
        super().setEnabled(on)
        for b in self._btns.values():
            b.setEnabled(on)
        self._pill.setDim(not on)
        self._pill.update()

    def _btn_qss(self, active):
        """选中段字色提亮, 未选中段 hover 只轻微提亮字色——
        不能给未选中段换底色: 那会在鼠标扫过一排时闪出一串深色块, 比选中态还抢眼。

        padding: 0 让文字在段内精确居中——QPushButton 默认样式带上下内边距,
        文字会略微偏上, 看起来像贴图没对齐。段高固定, 横向留白由段宽提供。
        """
        _bg, unsel, sel = _seg_colors()
        pad = "padding: 0px;"
        font = _seg_font_qss(self._pt)
        if active:
            return btn_qss("transparent", sel, hover="transparent",
                           font=font, radius=self._pill_r, extra=pad)
        return btn_qss("transparent", unsel, hover="transparent", hover_fg=sel,
                       font=font, radius=self._pill_r, extra=pad)

    def value(self):
        return self._current

    def set_value(self, v):
        if v in self._btns and v != self._current:
            self._current = v
            self._refresh()
            self._slide(v)
            if self._on_change:
                self._on_change(v)

    def _pick(self, v):
        if v == self._current:
            return
        self._current = v
        self._refresh()
        self._slide(v)
        if self._on_change:
            self._on_change(v)

    def _slide(self, v, animate=True):
        """把药丸移到第 v 段下方。

        位置直接取按钮的实际 geometry —— 自己按宽度累加会把 TRACK_PAD 算两次,
        药丸比对应段偏 3px(实测药丸 x=6 而按钮 x=3)。
        """
        b = self._btns.get(v)
        if b is None:
            return
        r = b.geometry()
        self._pill.slide_to(QRect(r.x(), r.y(), r.width(), r.height()), animate)

    def _refresh(self):
        for val, b in self._btns.items():
            b.setStyleSheet(self._btn_qss(val == self._current))

    def sizeHint(self):
        # 返回 track 的尺寸即可: 外层布局会把 track 居中, 高度由宿主行决定,
        # 这里只提供宽度与最小高度。不返回会让 Qt 按空壳 QWidget 默认值算,
        # 与 track 固定高对不上, 行高就被撑歪。
        return self._track.sizeHint()

        # 药丸是自绘子控件, 不吃 layout, 位置全靠 _slide 按按钮真实 geometry 算。
        # 宿主行何时把 track/按钮的 geometry 分配完 Qt 不保证(构造末尾调 _slide 时
        # 按钮还在默认位置, 药丸就落到错处)。所以布局一变就得重定位, 不能只在
        # 构造时算一次。这里监听 track 布局的 activated + 自身 showEvent 两处。

    def showEvent(self, e):
        super().showEvent(e)
        self._relayout_pill()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout_pill()

    def _relayout_pill(self):
        # 药丸是自绘子控件, 不吃 layout, 位置全靠 _slide 按按钮真实 geometry 算。
        # 宿主行何时把 track/按钮的 geometry 分配完 Qt 不保证——构造末尾就调
        # _slide 时按钮还在默认位置, 药丸会落到错处。所以布局一变就重定位,
        # 不能只在构造时算一次。布局定稿后再算, 此时按钮 geometry 才是真实值。
        self._slide(self._current, animate=False)

    def minimumSizeHint(self):
        return self._track.minimumSizeHint()


def segmented_control(items, current, on_change=None, parent=None, size="normal"):
    """构造分段选择器。items=[(显示文本, 值), ...]

    size 选几何档位, 必须与宿主行的行高匹配(见 SIZES):
      "settings" 18px 设置页开关行(行高24)
      "compact"  28px 动作行内
      "normal"   36px 悬浮设置页
    """
    return SegmentedControl(items, current, on_change, parent, size)
