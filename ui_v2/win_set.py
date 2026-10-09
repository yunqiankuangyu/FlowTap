"""
设置窗 —— 横板 640x400, 两页两列(外观 / 功能)

复用: widgets.slider_qss / segmented_control / card_qss / btn_qss / _make_label
底部按钮随分页变化: 主题要重建整棵 UI 树, 结构上无法即时刷新才留「应用」;
其余项改完即生效, 不摆一个点了才有反应的按钮。
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QSlider, QScrollArea, QPushButton, QApplication, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

from config import Colors, FONT_B, THEMES, DEFAULTS
from .widgets import (card_qss, btn_qss, slider_qss, _make_btn,
                        _make_label, style_label, tag_label, set_bg, scroll_qss,
                        restyle_tree, palette_now)
from .segmented import segmented_control
from .base import V2Win, apply_round_corners
from .titlebar import attach_drag, TITLEBAR_H
from .panel import _spin, _card, _row_box, _plain

W, H = 640, 400


class SetWin(V2Win):
    # 设置弹窗: 与主窗同风格, 独立顶层窗
    def __init__(self):
        super().__init__(W, H)
        # 设置是"程序的弹窗": Tool 窗口不进任务栏、不进 Alt+Tab —— 任务栏里只该有
        # 一条 FlowTap, 不该一开设置就变成"FlowTap + 设置"两个窗。
        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        apply_round_corners(self)   # setWindowFlags 会重建句柄, DWM 圆角属性重挂
        self.setWindowTitle("设置")
        # 打开设置窗时从 settings.json 读回真实值 —— 硬编码会让改过的项
        # 重启后看起来"没保存"。键名与旧 UI 一致, 读的就是旧版写的那份。
        from config import load_settings as _ls
        _s = _ls()
        self.alpha = float(_s.get("opacity", 0.9))
        self._cur_theme = _s.get("theme")
        # 窗口壳(root 保活、必须进窗口 layout)在 base.V2Win.mount_root 唯一实现
        lay = self.mount_root()
        lay.addWidget(self._bar())

        self.nav = QWidget()
        nl = QHBoxLayout(self.nav)
        # 上边距 = 双页签与顶栏的间隔, 用户定 2px(原 10, 也可给 0)
        nl.setContentsMargins(12, 2, 12, 2)
        nl.setSpacing(4)
        self.pg_btns = {}
        for key, txt in (("ap", "外观设置"), ("fn", "功能设置")):
            b = _make_btn(txt, height=28)
            b.clicked.connect(lambda _c=False, k=key: self.pick_page(k))
            self.pg_btns[key] = b
            nl.addWidget(b, 1)
        lay.addWidget(self.nav)

        # 内容区: 单页容器 + 纵向滚动。页由 pick_page 换进去(见那里的说明),
        # 两页不同时挂着 —— 挂着的话内容多的一页会把窗口顶大
        self.body = QScrollArea()
        self.body.setWidgetResizable(True)
        self.body.setStyleSheet(scroll_qss("transparent"))
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.pages = {}
        self.segs = {}      # 两页共用的胶囊字典, 在此建一次免得互相清空
        self.pages["ap"] = self._page_ap()
        self.pages["fn"] = self._page_fn()
        lay.addWidget(self.body, 1)

        self.foot = QFrame()
        self.foot.setStyleSheet("background: transparent; border-top: 1px solid "
                                f"rgba(100,116,139,0.32);")
        fl = QVBoxLayout(self.foot)
        fl.setContentsMargins(12, 8, 12, 12)
        self.wins = []      # 参与整树换肤的其它窗口(主窗/迷你窗, 接线见 main_v2.wire)
        self.on_top_change = None   # 窗口置顶开关的即时生效出口(接线见 main_v2.wire)
        self.on_radius_change = None   # 圆角拉条的即时生效出口(同上)
        self.foot_ap = _make_btn("应用主题", height=28)
        self.foot_ap.clicked.connect(self._apply_clicked)
        fl.addWidget(self.foot_ap)
        self.foot_fn = _make_label("功能项即时生效，无需应用", color=Colors.DIM,
                                   align=Qt.AlignCenter)
        fl.addWidget(self.foot_fn)
        lay.addWidget(self.foot)

        self.pick_page("ap")
        self.move(1100, 40)

    # ── 标题栏 ──
    def _bar(self):
        bar, lay = _plain()
        bar.setFixedHeight(TITLEBAR_H)
        lay.setContentsMargins(14, 0, 6, 0)
        lay.setSpacing(0)
        t = _make_label("设置", font=FONT_B)
        lay.addWidget(t)
        lay.addStretch()
        x = _make_btn("✕", height=28)
        x.setFixedWidth(34)
        x.setStyleSheet(btn_qss("transparent", Colors.TEXT2, hover=Colors.RED,
                                hover_fg="#ffffff", radius=5))
        # 关窗走回调而不直接 close: 主窗压着遮罩, 需要它一起撤
        x.clicked.connect(self._close)
        lay.addWidget(x)
        # 拖动引用正源 ui.titlebar.attach_drag, 不自己写一套
        attach_drag(self, bar)
        return bar

    def _save(self, **kw):
        """落盘 settings.json —— 与旧 UI 同一份文件, 改完即写, 不设"应用"按钮。

        旧版的键名是这些设置的既定来源(opacity/theme/always_on_top/
        start_countdown/fixed_position_match/match_mode/default_delay...),
        新 UI 直接沿用, 所以旧版改过的设置新界面能读到, 反之亦然。
        """
        from config import load_settings, save_settings
        try:
            s = load_settings()
            s.update(kw)
            save_settings(s)
        except Exception:
            pass              # 只读环境(如打包的无写权限目录)下不打断界面

    def refresh_hotkeys(self):
        """把热键轮询里的当前键名刷到标签上(改绑后也会被回调触发)"""
        from .hotkey import hk_name
        info = getattr(self, "_hk_info", None)
        for which, lbl in getattr(self, "_hk_keys", {}).items():
            if info is None:
                lbl.setText("…")
                continue
            st = info["state"]()
            if st["capturing"] and st["target"] == which:
                # 正在等你按新键: 显示提示而不是旧键名
                lbl.setText("按下新键…")
                style_label(lbl, Colors.YELLOW)
            else:
                lbl.setText(hk_name(st[which]))
                style_label(lbl, Colors.BLUE)

    def _cap_hotkey(self, which):
        """点「修改热键」: 进入捕获, 下一个按下的键成为该热键(ESC 取消)"""
        info = getattr(self, "_hk_info", None)
        if info is None:
            return
        info["begin"](which)
        self.refresh_hotkeys()

    def _close(self):
        # 关设置窗 = 放弃未应用的预览, 还原到上次「应用主题」定下的主题
        if self.cur_theme != self._cur_theme:
            self.cur_theme = self._cur_theme
            self.apply_theme(self._cur_theme)
        self.hide()
        if getattr(self, "on_close", None):
            self.on_close()      # 通知主窗撤遮罩(接线见 main_v2.wire)

    # ── 两列卡组骨架 ──
    # 两列的 layout 随页一起返回, 不存在 self.l1/self.l2 上 ——
    # 那是实例属性, 建第二页时会被覆盖, 第一页再切回来就往错的列里加卡片。
    def _page(self):
        row, rl = _plain()
        # 卡片之间的间隔 = M=4; 卡片到窗口左右边 = 12, 与双页签(nav 左右边距 12)、
        # 底部按钮对齐 —— 三处横向边距一个口径(用户定, 取双页签那个值)。
        # 只给左右留边: 上下边会算进内容高, 而视口是定死的(超了就冒滚动条)。
        rl.setContentsMargins(12, 0, 12, 0)
        rl.setSpacing(4)
        cols = []
        for _ in range(2):
            c, vl = _plain("v")
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(4)   # 同列上下卡片 = M
            rl.addWidget(c, 1)
            cols.append(vl)
        return row, cols

    def _pin(self, c):
        """卡纵向定成 Fixed: 卡高 = 内容高(sizeHint)。

        默认 Preferred 时, 列里最后一张卡会去分栏内剩余空间(实测外观页圆角卡、
        功能页识图卡都被撑到 101, 比 hint 78 高出一截), 长宽就和隔壁卡不齐了。
        Fixed 后剩余空间全归列尾的 stretch, 每张卡都按内容定高。"""
        c.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        return c

    # ── 外观页 ──
    def _page_ap(self):
        page, cols = self._page()
        ca, cb = cols        # 两列: ca 左 cb 右
        # 不透明度: 滑条 + 实时百分比, 同时驱动停靠栏毛玻璃底色
        c1, cl1 = _card(title="👁 窗口不透明度")
        row, rl = _plain()
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self.sl = QSlider(Qt.Horizontal)
        self.sl.setRange(30, 100)
        self.sl.setValue(int(self.alpha * 100))
        self.sl.setStyleSheet(slider_qss())
        self.sl.valueChanged.connect(self._on_alpha)
        rl.addWidget(self.sl, 1)
        self.alpha_lbl = _make_label(f"{int(self.alpha * 100)}%")
        self.alpha_lbl.setFixedWidth(44)
        rl.addWidget(self.alpha_lbl)
        cl1.addWidget(row)

        # 外观页左栏原本只有一张卡, 下面 300px 全空。补这张让两栏视觉密度相当。
        # 圆角: 0-90 拉条(与不透明度同款), 拖动即时重绘三个窗 —— 只改 V2Win._r + update,
        # 不碰窗口属性, 所以没有"隐藏再显示"的闪。
        # 停靠栏阴影那行已删: 新 UI 停靠栏根本没有阴影可调(dock_shadow 只有旧 UI 在读),
        # 摆个开关是死控件。
        c4, cl4 = _card(title="🔲 窗口圆角")
        from config import load_settings as _ls_r
        cur_r = int(_ls_r().get("win_radius", 16))
        rrow, rrl = _plain()
        rrl.setContentsMargins(0, 0, 0, 0)
        rrl.setSpacing(8)
        self.rsl = QSlider(Qt.Horizontal)
        # 0-60(用户定): 再大角部透明区会吃进标题/页签, 后面的窗口露出来就穿帮
        self.rsl.setRange(0, 60)
        self.rsl.setValue(cur_r)
        self.rsl.setStyleSheet(slider_qss())
        self.rsl.valueChanged.connect(self._on_radius)
        rrl.addWidget(self.rsl, 1)
        self.radius_lbl = _make_label(str(cur_r))
        self.radius_lbl.setFixedWidth(44)
        rrl.addWidget(self.radius_lbl)
        cl4.addWidget(rrow)

        c2, cl2 = _card(title="🪟 窗口行为")
        # 键名沿用 settings.json 旧版的既定写法, 旧版改的这里能读到, 反之亦然
        from config import load_settings as _ls3
        _s3 = _ls3()     # 读回旧版写过的真值, 不用硬编码初值
        for lab, key, cur, sk in (("窗口置顶", "top",
                                   bool(_s3.get("always_on_top", True)),
                                   "always_on_top"),
                                  ("记住窗口高度", "hgt",
                                   bool(_s3.get("remember_height", True)),
                                   "remember_height")):
            def _cb(v, k=key, name=sk):
                self._save(**{name: v})
                if name == "always_on_top" and getattr(self, "on_top_change", None):
                    self.on_top_change(v)   # 置顶即时生效(功能项即时生效同一口径)
            sg = segmented_control([("开", True), ("关", False)], cur,
                                   _cb, size="settings")
            self.segs[key] = sg
            cl2.addWidget(_row_box(lab, sg))

        # 内边距/卡内间距按这张卡单独收紧: 10 枚 4 行的高度(294)超过视口 275 会冒滚动条,
        # 收这里省 15px, 别的卡维持默认 (12,10,12,12)/9; 网格 4px 节奏是旧 UI 的样子, 不动
        c3, cl3 = _card(title="🎨 色彩主题", margins=(12, 6, 12, 6), spacing=4)
        grid, gl = _plain("g")
        # 旧 UI 同款(settings_mode.py:215): 每个主题一枚文字胶囊, 底色/字色用该主题自己的
        # CARD/TEXT、悬停该主题的 ACCENT —— 一眼能看全 10 个主题的真实配色; 3 列等宽、间距 4。
        gl.setContentsMargins(0, 0, 0, 0)
        # 行间隔 2(原 4, 旧 UI 的节奏): 省下的 6px 给胶囊加高 —— 行距仍是 32(30+2),
        # 胶囊占行距 94%, 既填满行带又比原来高
        gl.setSpacing(2)
        self.themes = {}
        self._hits = []      # 主题格本身就是可点按钮, 不再铺透明热区(保留空表给 base._fit_hits)
        names = list(THEMES.keys())
        # 当前主题从 settings 读, 读不到就退回第一个
        self.cur_theme = self._cur_theme if self._cur_theme in names else names[0]
        for i, n in enumerate(names):
            t = THEMES[n]
            on = (n == self.cur_theme)
            b = QPushButton(n)
            b.setProperty("keepColor", True)   # 色卡各自保持本主题颜色, 不参与整树换肤
            b.setFont(FONT_B)
            # 30: 比页签/底部按钮(28)再高一档, 配合行间隔 4->2 ——
            # 网格 4x30+3x2=126 -> 主题卡 166 -> 右列 280 <= 视口 283, 仍无滚动条
            b.setFixedHeight(30)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setStyleSheet(self._theme_qss(n, on))
            b.clicked.connect(lambda _c=False, k=n: self._pick_theme(k))
            self.themes[n] = b
            gl.addWidget(b, i // 3, i % 3)
        for c in range(3):
            gl.setColumnStretch(c, 1)
        cl3.addWidget(grid)
        # 外观页: 左列 不透明度 + 圆角, 右列 窗口行为 + 主题
        for _c in (c1, c4, c2, c3):
            self._pin(_c)
        ca.addWidget(c1)
        ca.addWidget(c4)
        cb.addWidget(c2)
        cb.addWidget(c3)
        ca.addStretch()
        cb.addStretch()
        return page, cols

    # ── 功能页 ──
    def _page_fn(self):
        page, cols = self._page()
        ca, cb = cols
        c1, cl1 = _card(title="⌨ 全局热键")
        # 键名不写死: 读热键轮询里的实际键(设置.json 里有就用文件的,
        # 否则与旧版常量一致的默认 F11/F12)。写死 F8/F9 会显示一个根本没绑的键。
        self._hk_keys = {}
        for which, lab in (("start", "开始"), ("stop", "停止")):
            w, wl = _plain()
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(8)
            wl.addWidget(_make_label(lab, color=Colors.TEXT2))
            key = tag_label("…", Colors.BLUE, bg="rgba(90,156,255,0.12)",
                            border="rgba(90,156,255,0.4)", radius=5, padding="2px 8px")
            wl.addWidget(key)
            wl.addStretch()
            b = _make_btn("修改热键", height=28)
            b.setFixedWidth(80)
            b.clicked.connect(lambda _c=False, w=which: self._cap_hotkey(w))
            wl.addWidget(b)
            cl1.addWidget(w)
            self._hk_keys[which] = key
        # 轮询接进来后立即刷一次; 没接(独立跑设置窗)就显示缺省
        self.refresh_hotkeys()

        # 三项都读 settings 再落盘: 写死 80/0.5/3 会让改过的值一关窗就"没保存",
        # 而且这三项正是执行链在读的(新建任务的 loop、动作 delay、起停倒计时)。
        from config import load_settings as _ls5
        _s5 = _ls5()

        c2, cl2 = _card(title="📋 新建任务默认值")
        w, wl = _plain()
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(8)
        wl.addWidget(_make_label("循环间隔", color=Colors.TEXT2))
        wl.addWidget(_spin(_s5.get("default_loop", DEFAULTS["default_loop"]), 1, 999, 1, 10,
                           lambda v: self._save(default_loop=int(v))))
        wl.addWidget(_make_label("s", color=Colors.DIM))
        wl.addStretch()
        wl.addWidget(_make_label("动作后延", color=Colors.TEXT2))
        wl.addWidget(_spin(_s5.get("default_delay", DEFAULTS["default_delay"]), 0, 999, 1, 0.1,
                           lambda v: self._save(default_delay=float(v))))
        wl.addWidget(_make_label("s", color=Colors.DIM))
        cl2.addWidget(w)

        c3, cl3 = _card(title="⏱ 启动倒计时")
        w3, w3l = _plain()
        w3l.setContentsMargins(0, 0, 0, 0)
        w3l.setSpacing(8)
        w3l.addWidget(_make_label("点击开始后等待", color=Colors.TEXT2))
        w3l.addStretch()
        w3l.addWidget(_spin(_s5.get("start_countdown", DEFAULTS["start_countdown"]), 0, 30, 0, 1,
                            lambda v: self._save(start_countdown=int(v))))
        w3l.addWidget(_make_label("秒", color=Colors.DIM))
        cl3.addWidget(w3)

        c4, cl4 = _card(title="🔍 识图匹配")
        from config import load_settings as _ls4
        _fix = bool(_ls4().get("fixed_position_match", True))
        sg = segmented_control([("开", True), ("关", False)], _fix,
                               lambda v: self._save(fixed_position_match=v),
                               size="settings")
        self.segs["fix"] = sg
        cl4.addWidget(_row_box("固定位置比对", sg))
        for _c in (c1, c2, c3, c4):
            self._pin(_c)
        ca.addWidget(c1)
        ca.addWidget(c2)
        cb.addWidget(c3)
        cb.addWidget(c4)
        ca.addStretch()
        cb.addStretch()
        return page, cols

    # ── 分页切换: 内容与底部按钮同步 ──
    def pick_page(self, k):
        # 一次只把当前页挂进容器: 两页同时挂着时 QStackedWidget 取所有页的 sizeHint 最大值,
        # 内容多的功能页会把设置窗顶到 640x480(实测), 隐藏页也照样撑大父容器。
        body = self.pages[k][0]
        # self.body 是 QScrollArea(自己没有 layout), 换页换的是它的 widget。
        # 旧页必须 takeWidget 取下(实测: 取走不删, 父对象归 None):
        #   setWidget 换页会把旧页连同子控件直接 delete —— 而 setParent(None) 拦不住,
        #   实测 setParent 后 sa.widget() 仍指旧页, 原来那套"先 detach 再换"形同虚设。
        #   不取走的话两页来回切几次, self.pages 里存的就是悬空指针, 下一次切换或
        #   _fit_hits 直接 RuntimeError; pythonw 没控制台, 异常看不见, 就是"设置页卡死"。
        self.body.takeWidget()
        self.body.setWidget(body)   # 重复点同一页 = 取下再挂回, 无副作用
        for key, b in self.pg_btns.items():
            if key == k:
                b.setStyleSheet(btn_qss(Colors.ACCENT, Colors.TEXT,
                                        Colors.ACCENT, radius=6, font="bold 17px 'MiSans'"))
            else:
                b.setStyleSheet(btn_qss("transparent", Colors.DIM,
                                        "transparent", hover_fg=Colors.TEXT2, radius=6,
                                        font="17px 'MiSans'"))
        self.foot_ap.setVisible(k == "ap")
        self.foot_fn.setVisible(k == "fn")
        self._fit_hits()

    @staticmethod
    def _theme_qss(name, on):
        """主题胶囊样式(旧 UI 口径): 该主题自己的 CARD 底 + TEXT 字 + ACCENT 悬停;
        当前主题压一道蓝边标明选中(旧版靠整窗配色隐含, 新版加一道免得看不出来)。"""
        t = THEMES.get(name) or {}
        return btn_qss(t.get("CARD", Colors.CARD), t.get("TEXT", Colors.TEXT),
                       hover=t.get("ACCENT", Colors.ACCENT), radius=6,
                       extra=f"border: 1.5px solid {Colors.BLUE};" if on else None)

    def _pick_theme(self, n):
        """点胶囊 = 预览: 全窗换肤但不落盘 —— 落盘归「应用主题」, 关窗则放弃预览"""
        self.cur_theme = n
        self.apply_theme(n)

    def _mark_theme_chips(self):
        """选中标记跟预览走(色卡不参与整树换肤, 见 restyle_tree 的 keepColor)"""
        for name, b in self.themes.items():
            b.setStyleSheet(self._theme_qss(name, name == self.cur_theme))

    def _apply_clicked(self):
        """「应用主题」= 抉当前预览落盘; 按钮给个回执"""
        self.apply_theme(self.cur_theme, save=True)
        b = self.foot_ap
        b.setText("✓ 已应用")
        QTimer.singleShot(1200, lambda: b.setText("应用主题"))

    def apply_theme(self, n, save=False):
        """把主题色写进 Colors, 并把 self + 其它窗口整棵子树里烤死的 QSS 一起换掉。

        只改 Colors 是不够的: 各控件的 QSS 建窗时就用旧色拼死了, 不跟着变就只有
        paintEvent 画的窗口底色会动(表现为"只变了一小部分")。
        与 main_v2._apply_theme 同口径: 不调 config.Colors.apply(它内部 import
        ui.widgets, 会让新 UI 反向依赖旧目录, 破隔离)。
        save=True 才落盘 —— 预览与关窗还原都走 False。
        """
        from config import Colors, THEMES, DEFAULT_THEME
        from .widgets import tooltip_qss
        old = palette_now()
        t = THEMES.get(n) or THEMES[DEFAULT_THEME]
        for k, v in t.items():
            setattr(Colors, k, v)
        new = palette_now()
        # 先冻结更新再整树换色: 几百次 setStyleSheet 各自触发重绘会满屏抖("像闪一下"),
        # 冻住之后只在解冻时出一次画面
        trees = [self, *self.wins]
        # 游离页补进来: pick_page 用 takeWidget 摘下的当前页(及未挂载的另一页)是
        # 无父对象, 不在 self 子树里, 不显式列出就漏换肤 —— 表现为"切到另一页才
        # 看到旧颜色"(功能页 27 处旧色的根因)。已挂载的页会在子树遍历里走到, 不重复。
        for _v in getattr(self, "pages", {}).values():
            _pgw = _v[0] if isinstance(_v, (tuple, list)) else _v
            if _pgw is not None and _pgw.parent() is None and all(_pgw is not t for t in trees):
                trees.append(_pgw)
        for w in trees:
            w.setUpdatesEnabled(False)
        try:
            for w in trees:
                restyle_tree(w, old, new)
        finally:
            for w in trees:
                w.setUpdatesEnabled(True)
        # 应用级样式(tooltip)也按新主题重设 —— 与启动时 _apply_theme 之后那步一致
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(tooltip_qss())
        if save:
            self._save(theme=n)
            self._cur_theme = n      # 已应用的主题, 关窗时按它还原
        self._mark_theme_chips()

    def _on_radius(self, v):
        """圆角拉条: 落盘 + 通知三个窗重绘(只改 _r, 不动窗口属性 = 无闪)"""
        self.radius_lbl.setText(str(int(v)))
        self._save(win_radius=int(v))
        if getattr(self, "on_radius_change", None):
            self.on_radius_change(int(v))

    # ── 不透明度联动: 两个消费端两套值 ──
    # op = v/100: 窗体不透明度, 与标签、旧UI同一语义(setWindowOpacity 同款 0.3~1.0),
    #   落盘也用它(旧版读到的必须是标签上那个数, 之前存重映射值 = 旧UI窗体错档)。
    # alpha = (v-50)/50 锚50放大: 只喂停靠栏毛玻璃底色(alpha=0 不显示底色, alpha=1 满实),
    #   与"透明"字面方向相反, 别拿它当窗体透明度。
    def _on_alpha(self, v):
        self.alpha_lbl.setText(f"{v}%")
        op = v / 100.0
        self.alpha = max(0.0, min(1.0, (v - 50) / 50))
        if getattr(self, "on_alpha_change", None):
            self.on_alpha_change(self.alpha, op)
        self._save(opacity=round(op, 3))           # 键义=不透明度(与旧版同键同义)
