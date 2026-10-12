"""
迷你窗 —— 扁横条 320x124, 常驻置顶

相对旧版(mini_mode.py 250x100)的三处翻新:
  任务 chip 横排一览   旧版只有一行「运行中 2/3」, 看不出是哪两个在跑
  状态并进全局按钮     旧版状态单独占一行, 信息量却只有一个数字
  底部加 ⚙ 设置入口    旧版进设置得点「取消最小化」回主窗再点设置, 迷你是常驻小窗很绕

复用: widgets.card_qss / btn_qss / dot_qss / _make_btn / _make_label / flat_btn
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt

from config import Colors, FONT_B, FONT_M
from .widgets import (btn_qss, dot_qss, flat_btn, F12,
                        _make_btn, _make_label, style_label, tag_label, hit_btn, set_bg,
                        rgba_of)
from .base import V2Win
from .titlebar import attach_drag, MINI_TITLEBAR_H
from .panel import _card, _restyle_card, _plain

W, H = 320, 124


class MiniWin(V2Win):
    # 迷你浮窗: 任务一览 + 全局启停
    def __init__(self, m=None):
        # m: 与主窗共用的 Model。给了就跟着主窗的任务表走, 不给则自建一份
        super().__init__(W, H)
        self.m = m
        self.setWindowTitle("FlowTap")
        # 三个回调由外部(main_v2)接管: 恢复主窗 / 打开设置 / 退出
        # 必须在 _bar() 之前就位, _bar 里的按钮 connect 时就要读它们
        self.on_restore = None
        self.on_settings = None
        self.on_quit = None
        # 窗口壳(root 保活、必须进窗口 layout)在 base.V2Win.mount_root 唯一实现
        lay = self.mount_root()
        lay.addWidget(self._bar())

        # 任务 chip: 撑满中段高度, 状态点 + 名字, 点一下单独启停
        chips, cl = _plain()
        cl.setContentsMargins(9, 8, 9, 0)
        cl.setSpacing(6)
        self._chip_holder = chips      # 存引用: rebuild 时 chips 已被清空, 取不到 parent
        self.chips = []
        self._hits = []      # (chip, 热区按钮) 对, 布局定稿后给热区对几何
        names = [t["name"] for t in (self.m.tasks if self.m else [])] or ["任务1"]
        for n in names:
            self._mk_chip(n, cl)
        lay.addWidget(chips, 1)

        foot, fl = _plain()
        fl.setContentsMargins(9, 0, 9, 9)
        fl.setSpacing(6)
        gear = _make_btn("⚙", height=28)
        gear.setFixedWidth(28)
        gear.setStyleSheet(btn_qss("transparent", Colors.TEXT2,
                                   hover=Colors.ACCENT, radius=6, font="13px 'MiSans'"))
        gear.clicked.connect(lambda: self.on_settings and self.on_settings())
        fl.addWidget(gear)
        self.go = _make_btn("▶ 全部开始", height=28)
        flat_btn(self.go, Colors.GREEN, hover=Colors.HOVER_GREEN)
        self.go.setFont(FONT_M)
        self.go.clicked.connect(self.toggle_all)
        fl.addWidget(self.go, 1)
        lay.addWidget(foot)

        self.move(1100, 520)
        self.sync_btn()

    def _bar(self):
        bar, lay = _plain()
        bar.setFixedHeight(MINI_TITLEBAR_H)
        lay.setContentsMargins(9, 0, 4, 0)
        lay.setSpacing(6)
        lay.addWidget(tag_label("MINI", Colors.BLUE, bg=rgba_of(Colors.BLUE, 0.14),
                                border=rgba_of(Colors.BLUE, 0.4), radius=4, padding="1px 5px"))
        lay.addWidget(_make_label("FlowTap", font=FONT_B))
        lay.addStretch()
        # ▣ = 恢复主窗, ✕ = 真正退出; 两者交由外部决定
        restore = _make_btn("▣", height=20)
        restore.setFixedWidth(24)
        restore.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=Colors.BLUE,
                                      hover_fg="#ffffff", radius=4, font="11px 'MiSans'"))
        restore.clicked.connect(lambda: self.on_restore and self.on_restore())
        lay.addWidget(restore)
        quit_b = _make_btn("✕", height=20)
        quit_b.setFixedWidth(24)
        quit_b.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=Colors.RED,
                                     hover_fg="#ffffff", radius=4, font="11px 'MiSans'"))
        quit_b.clicked.connect(lambda: self.on_quit and self.on_quit())
        lay.addWidget(quit_b)
        # 拖动引用正源 ui.titlebar.attach_drag。迷你窗标题栏只有 28px 高,
        # 只接标题栏的话可拖区太窄, 所以同时接整个 root 空白处 ——
        # chip 与按钮各自消费事件, 不会误触发拖动。
        attach_drag(self, bar)
        return bar

    # ── 全局启停: 状态并进按钮, 不另占一行 ──
    def toggle_all(self):
        # 走 Model, 与主窗同一份状态; 有 Model 时以它的结果为准
        if self.m:
            self.m.toggle_all()
            for c, t in zip(self.chips, self.m.tasks):
                self._set_chip(c, t["run"])
        else:
            run = not self.running
            for c in self.chips:
                self._set_chip(c, run)
        self.sync_btn()

    def toggle_one(self, c):
        i = self.chips.index(c)
        if self.m:
            self.m.toggle_one(i)
        self._set_chip(c, not c._run)
        self.sync_btn()

    def _set_chip(self, c, on):
        c._run = on
        _restyle_card(c, extra=f"border: 1px solid {Colors.GREEN};" if on else "")
        # 圆点样式走 dot_qss 正源(它自带 background + border-radius)。
        # 别再叠 set_bg: 那是整块 stylesheet, 后写只会把圆点规则冲成空心方块。
        c._dot.setStyleSheet(dot_qss(Colors.GREEN if on else Colors.DIM, radius=4))
        style_label(c._lbl, Colors.TEXT if on else Colors.TEXT2)

    def rebuild(self):
        # 任务数变了(主窗增删任务)重建 chip: chip 数量在构造时定死, 加任务后对不上
        if not self.m:
            return
        names = [t["name"] for t in self.m.tasks] or ["任务1"]
        if len(names) == len(self.chips):
            for c, t in zip(self.chips, self.m.tasks):
                self._set_chip(c, t["run"])
            self.sync_btn()
            return
        for c, h in self._hits:
            h.setParent(None)
        self._hits = []
        holder = self.chips[0].parentWidget()
        while holder.layout().count():
            it = holder.layout().takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
        self.chips = []
        self._build_chips(names)
        self.sync_btn()

    def _build_chips(self, names):
        holder = self._chip_holder      # 容器在构造时已存引用, 不从 chips[0] 反查
        for n in names:
            self._mk_chip(n, holder.layout())

    def _mk_chip(self, n, lay):
        """chip 构造唯一实现 —— 首次建与 rebuild 建同一份, 不再各写一遍。

        点击热区用真控件(hit_btn), 不在 sync_btn 里挂 mousePressEvent:
        每次重挂都会让上一轮的绑定对象被 Qt 回收, 再访问就报
        "Internal C++ object already deleted"; 热区浮在 chip 上层不入布局,
        直接 addWidget 会把它挤进流里(状态点与名字之间多出空框, 实测截图)。
        """
        c, hl = _card(radius=6, margins=(8, 0, 8, 0), spacing=5, kind="h")
        d = QFrame()
        d.setFixedSize(8, 8)
        # 圆点样式走 dot_qss 正源, 理由见 _set_chip 里的注释
        d.setStyleSheet(dot_qss(Colors.DIM, radius=4))
        hl.addWidget(d)
        t = _make_label(n, color=Colors.TEXT2)
        hl.addWidget(t, 1)
        c._dot, c._lbl = d, t
        c._run = False
        hit = hit_btn(c, lambda _x=False, w=c: self.toggle_one(w))
        self.chips.append(c)
        lay.addWidget(c, 1)
        self._hits.append((c, hit))

    def sync_btn(self):
        # 全停显开始, 否则显停止+计数; 有 Model 时以它的计数为准(与主窗同源)。
        # 只在这里读模型改 chip, _set_chip 不回调 sync_btn, 不会递归。
        n = len(self.chips)
        on = sum(1 for c in self.chips if c._run)
        if self.m:
            on = self.m.running
            for c, t in zip(self.chips, self.m.tasks):
                self._set_chip(c, t["run"])
        self.running = on > 0
        self.go.setText(f"■ 全部停止 {on}/{n}" if on else "▶ 全部开始")
        flat_btn(self.go, Colors.RED if on else Colors.GREEN,
                 hover=Colors.HOVER_RED if on else Colors.HOVER_GREEN)
