"""
新 UI 主窗 —— 横版三栏 + 底部停靠栏

窗口外壳沿用主窗既有的做法(引 core.window_gate.apply_round_corners):
  无边框顶层窗口上, 样式表 border-radius 完全无效, 圆角必须 paintEvent 自绘;
  参与圆角的各层容器底色必须全为 transparent, 任一层糊上实色就会方角盖掉圆角。
标题栏直接引用 ui.titlebar.build_titlebar —— 拖动逻辑/按钮样式/titlebar_qss
都在那一份实现里, 这里只传高度、三按钮组合与标题三处差异。不自己重写标题栏:
两套实现意味着每次改动要同步两处, 且拖动这种基础能力容易只改一处就漏。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import QTimer, Qt

from config import Colors
from .widgets import scroll_qss, set_bg, style_label, tip_label, rgba_of
from .base import V2Win, SHADOW
from .dock import Dock
from .titlebar import build_titlebar, TITLEBAR_H
from .model import Model
from .panel import build_left, build_mid, build_right, RATIO, _line, _plain

WIN_W, WIN_H = 1024, 640


def _log(tag, msg, error=False):
    """走项目自带的 logger(与旧 UI 同一份日志文件), 失败不打断界面"""
    try:
        from logger import log_info, log_error
        if error:
            log_error(tag, msg)
        else:
            log_info(tag, msg)
    except Exception:
        pass


def _color(c, default):
    """引擎的状态色是 '#4ade80' 这类 hex, 空值/异常就退回主题色"""
    try:
        return c if c else default
    except Exception:
        return default


class WinV2(V2Win):
    def __init__(self):
        super().__init__(WIN_W, WIN_H)
        self.setWindowTitle("FlowTap")
        # 外部接管: 收迷你 / 退出 / 重启(必须在 _titlebar 之前就位)
        self.on_minimize = None
        self.on_quit = None
        self.on_restart = None
        self.m = Model()          # 运行时数据; 界面只读它并按变化重建
        self._veil_box = None     # 设置窗弹出时的压暗遮罩, 见 _veil
        self._rounds = {}         # 每任务已完成轮数(反馈用, 见 _on_status)
        outer = QVBoxLayout(self)
        # 外圈留阴影带(V2Win.__init__ 已按卡片尺寸定窗, 这里把内容压回卡片区)
        outer.setContentsMargins(SHADOW, SHADOW, SHADOW, SHADOW)
        outer.setSpacing(0)
        outer.addWidget(self._titlebar())

        # 三栏容器
        body, bl = _plain()
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        # 三栏互相回调: 选中任务/行后对方要跟着换
        self.m._left = self.m._mid = self.m._right = None
        left, self.combo = build_left(self.m)
        mid = self._mid_scroll()
        right = build_right(self.m)
        self.m._left, self.m._mid, self.m._right = left, mid, right
        # 三栏按 RATIO 百分比算固定宽度, 不用 addStretch 分配 ——
        # stretch 会让"内容最窄需求大"的栏多吃(实测中栏吃到 38.9%, 比例失真)。
        # 窗口本身是 setFixedSize, 算一次就够; 余数交给末尾的 stretch 吃掉,
        # 免得 layout 把零头摊到某一栏上。
        for i, (w, p) in enumerate(zip((left, mid, right), RATIO)):
            w.setFixedWidth(int(WIN_W * p / 100))
            bl.addWidget(w)
            if i < 2:                       # 分隔线只在栏与栏之间
                bl.addWidget(_line(), 0)
        bl.addStretch()                      # 吃掉 int 取整的零头
        outer.addWidget(body, 1)
        self.body = body

        # 停靠栏浮在窗口底部正中
        self.dock = Dock(self, ["▶ 全部开始", "设置", "MINI", "重启"])
        self.dock.apply(-1, animate=False)
        self.m.on_toast = self._toast
        self.m.on_run_change = self._toggle_one
        self.m._main_win = self           # 录制坐标时主窗让位, 见 capture.capture_click

    # ── 遮罩: 设置窗弹出时压暗主窗 ──
    # 设置窗 640x400 覆盖主窗 1024x640 的大半, 直接居中摆上去会遮住正在编辑的
    # 内容。覆盖式子窗口的惯例是给宿主压一层暗色, 让"这是临时弹层"这件事一眼可见。
    def _veil(self):
        if self._veil_box is not None:
            return
        v = QWidget(self)
        v.setStyleSheet(f"background: {rgba_of('#000000', 0.28)};")
        # 只盖卡片区: 盖到阴影带会把透明区糊成深色方块, 直角就露出来了
        v.setGeometry(SHADOW, SHADOW, self._cw, self._ch)
        # 遮罩只管"压暗"这一件事, 不许挡鼠标 —— 它盖住整窗(含顶栏), 一旦吃事件,
        # 设置窗开着时顶栏就拖不动了(内容区靠 _set_panel 禁用挡住, 不需要遮罩代劳)
        v.setAttribute(Qt.WA_TransparentForMouseEvents)
        v.raise_()
        v.show()
        self._veil_box = v

    def _unveil(self):
        if self._veil_box is not None:
            self._veil_box.hide()
            self._veil_box.setParent(None)
            self._veil_box = None

    def toast(self, text):
        self._toast(text)

    def _runner(self):
        # 懒建执行器: 首次点开始才 import 执行层, 启动主窗不碰 tasks/
        if getattr(self, "_run", None) is None:
            from .runner import Runner
            self._run = Runner(self.m, on_status=self._on_status)
        return self._run

    def _toggle_one(self, i):
        """单卡启停 —— 只跑这一个, 不影响其他卡

        调用时 m.toggle_one 已经把 run 翻转过了, 这里读到的是**翻转后**的新值:
        True=要启动, False=要停止。方向反了会让点「停止」反而启动任务。
        """
        t = self.m.tasks[i]
        r = self._runner()
        if not t["run"]:
            r.stop(i)
        else:
            n = r.start(i)
            if not n:
                t["run"] = False
                self.toast(f"{t['name']} 启动失败")

    def _on_status(self, kind, *a):
        """执行器的反馈出口: 倒计时 / 引擎状态 / 一轮完成 / 异常

        只改状态文字与色点, 不 rebuild 三栏 —— 倒计时每秒来一次,
        rebuild 会整栏重建, 闪烁且丢焦点。
        """
        if kind == "error":
            self.toast(str(a[0]))
            _log("ui_v2.status", str(a[0]), error=True)
            return
        if kind == "cd":
            i, text = a[0], a[1]
            self._set_task_st(i, text, Colors.YELLOW)
        elif kind == "cd_all":
            i, text = a[0], a[1]
            for k in range(len(self.m.tasks)):
                self._set_task_st(k, text, Colors.YELLOW)
        elif kind == "stat":
            i, text, color = a[0], a[1], a[2]
            c = _color(color, Colors.GREEN)
            self._set_task_st(i, text, c)
        elif kind == "round":
            i = a[0]
            self._rounds[i] = self._rounds.get(i, 0) + 1
            self._set_task_st(i, f"已完成 {self._rounds[i]} 次", Colors.GREEN)
        self._sync_go()

    def _set_task_st(self, i, text, color):
        """只改任务卡的状态文字与色点"""
        cards = getattr(self.m._left, "task_cards", None) or []
        if 0 <= i < len(cards):
            card = cards[i]
            st = getattr(card, "_st", None)
            if st is not None:
                #剥掉状态文本自带的●前缀, 圆点统一由下方状态灯表达
                st.setText(text.removeprefix("● ").removeprefix("●"))
                style_label(st, color)
            dot = getattr(card, "_dot", None)
            if dot is not None:
                dot.setStyleSheet(f"background: {color}; border-radius: 4px;")

    def _sync_go(self):
        # 只把播放键文案刷成与模型一致, 不碰启停 ——
        # 重置/载入这类只想刷文案的地方误调 toggle_all_tasks 会真的开跑
        n = len(self.m.tasks)
        pend = bool(getattr(getattr(self, "_run", None), "_pending", {}))
        b = self.dock.btns[0]
        if pend or self.m.running:
            b.setText(f"■ 全部停止 {self.m.running}/{n}"
                      if not pend else "● 准备中…")
        else:
            b.setText("▶ 全部开始")
        self.dock.apply(-1, animate=False)      # 文案变了, 宽度要重算

    def toggle_all_tasks(self):
        # 全局启停二值化: 只要还有任务在跑就先全停, 全停了再点才全开。
        # 判定写 "只要没全停就全停" —— 若写成"部分运行才动作",
        # 全开(3/3)时点按钮会没反应, 那是最容易撞上的状态。
        run = not (self.m.running == 0)      # 二值化: 还在跑就全停
        if run:
            self._runner().stop_all()
            self.m.running = 0
            for t in self.m.tasks:
                t["run"] = False
        else:
            n = self._runner().start_all()    # 真跑: 转成引擎动作并启动线程
            if n:
                self.m.running = len(self.m.tasks)
                for t in self.m.tasks:
                    t["run"] = True
                self.toast(f"已启动 {n} 个任务")
                _log("ui_v2.start_all", f"{n} 个任务")
            else:
                self.toast("启动失败")
                _log("ui_v2.start_all", "启动失败", error=True)
        self.m.refresh(panes=("left",), mini=False)
        if self.m._mini:
            self.m._mini.sync_btn()   # 迷你窗读同一份模型, 主动推一次
        self._sync_go()          # 只刷文案

    def _hint(self, text, sticky=False):
        """常驻/可自动消失的提示条。

        与 toast 共用同一个控件, 但 sticky=True 不定时回收 —— 录制回显走这条:
        capture_keys 每 15ms 报一次组合键, 若每次开新 toast(各自挂 1.2s 回收)
        会堆几十个定时器并疯狂闪烁。
        """
        lbl = getattr(self, "_toast_lbl", None)
        if lbl is None:
            lbl = tip_label(self, "", padding="8px 22px")
            lbl.hide()
            self._toast_lbl = lbl
        lbl.setText(text)
        lbl.adjustSize()
        lbl.move((self.width() - lbl.width()) // 2,
                 self.height() - SHADOW - self.dock.height() - lbl.height() - 30)
        lbl.show()
        lbl.raise_()
        if not sticky:
            QTimer.singleShot(1200, lbl.hide)

    def _toast(self, text):
        # 提示条: 独立控件, 借停靠栏播放键显示会让那个键在提示期间点不动,
        # 而且文案与真实状态冲突(提示"已保存"时按钮显示的是提示不是"全部开始")。
        # 控件与排布只在 _hint 一份, 这里只是"定时回收"的那一档。
        self._hint(text)

    def _mid_scroll(self):
        # 中栏内容可滚: 动作行数不封顶, 超出时滚动而不是被裁掉。
        # build_mid 内部已自带滚动区, 直接用它当栏容器 —— 若再套一层 QScrollArea,
        # m._mid 拿到的是滚动壳, 上面没有 rebuild, 选中行/增删动作都会炸。
        return build_mid(self.m)

    def _titlebar(self):
        # 引用 ui.titlebar.build_titlebar —— 拖动逻辑/按钮样式/titlebar_qss 都在
        # 那里面, 不自己重写一遍(两套标题栏实现意味着改动要同步两处)。
        # 只传自己不同的三项: 高度 36、三按钮组合与回调、固定标题。
        return build_titlebar(
            self, height=TITLEBAR_H, title="FlowTap",
            buttons=[("—", Colors.BLUE, lambda: self.on_minimize and self.on_minimize()),
                     ("▢", Colors.BLUE, lambda: None),      # 占位: 无最大化行为
                     ("✕", Colors.RED, lambda: self.on_quit and self.on_quit())])
