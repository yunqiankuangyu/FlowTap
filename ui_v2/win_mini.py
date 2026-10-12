"""
迷你窗 —— 旧 UI 观感: 250x100, 标题栏 + 两个按钮 + 底部一行状态文字

照旧版 ui/mini_mode.py 复刻三段, 不再做新 UI 翻新(用户拍板):
  标题栏 32   标题 + ✕ 退出 + 整条拖动(松手存 mini_pos_x/y, 与旧版同键)
  按钮行      「取消最小化」蓝 + 「▶ 全部开始」绿, 各 32 高 stretch 均分
  状态行      ● 就绪 / ● 运行中 N/M / ● 已停止 N 个任务, GREEN/DIM
底色两段: 标题栏卡片色 + 内容区 ACCENT(旧版同款), 画在 base.paintEvent, 圆角保住。
中段任务 chip 与 ⚙ 设置入口一并删: 单任务启停回主窗任务卡, 设置回主窗。

状态不轮询(旧版 1s QTimer 不搬): 接 Model 推送 —— sync_btn 与
Model.refresh->rebuild, 数据源与主窗 dock 同一份(m.running / len(m.tasks))。

复用: titlebar.build_titlebar(标题栏+拖动正源) / widgets._make_btn·flat_btn·
style_label / panel._plain —— 不 import ui/。
"""
from PySide6.QtCore import Qt

from config import FONT_B, Colors, load_settings, save_settings

from .base import V2Win
from .panel import _plain
from .titlebar import build_titlebar
from .widgets import _make_btn, _make_label, flat_btn, style_label

W, H = 250, 100
BAR_H = 32          # 标题栏高, 与旧版同(旧翻新稿的 titlebar.MINI_TITLEBAR_H=28 不再用)


class MiniWin(V2Win):
    # 迷你浮窗: 旧版三段式 —— 标题栏 / 两个全局按钮 / 底部状态行
    def __init__(self, m=None):
        # m: 与主窗共用的 Model。给了就跟着主窗任务表走, 不给则按空模型显示
        super().__init__(W, H)
        self.m = m
        # 两段色: 标题栏留卡片色, 标题栏以下刷 ACCENT —— 对齐旧版 ui/mini_mode.py
        # (mini 底 ACCENT / 标题栏 CARD); 画法在 base.paintEvent, 圆角照旧自绘
        self._seg = (BAR_H, "ACCENT")
        self.setWindowTitle("FlowTap")
        # 两个回调由外部(main_v2)接管: 恢复主窗 / 退出; 按钮点击时才读
        self.on_restore = None
        self.on_quit = None
        s = load_settings()
        self.move(int(s.get("mini_pos_x", 1100)), int(s.get("mini_pos_y", 520)))
        # 窗口壳(root 保活、必须进窗口 layout)在 base.V2Win.mount_root 唯一实现
        lay = self.mount_root()
        lay.addWidget(self._bar())
        lay.addWidget(self._btns())
        # 状态行居中, 吃掉剩余高度(32 + 44 + 24 = 100, 与旧版同分布)
        self.st = _make_label("● 就绪", align=Qt.AlignCenter)
        lay.addWidget(self.st)
        self.sync_btn()

    def _bar(self):
        # 标题栏走 build_titlebar 正源(标题/✕/拖动一体); 32 高与旧版同
        bar = build_titlebar(self, height=BAR_H,
                             buttons=[("✕", Colors.RED,
                                       lambda: self.on_quit and self.on_quit())])
        # 拖动松手存位置: attach_drag 是正源不改, 外面包一层只补落盘
        press, rel = bar.mousePressEvent, bar.mouseReleaseEvent

        def _press(e):
            press(e)
            self._p0 = (self.x(), self.y())

        def _rel(e):
            rel(e)
            if (self.x(), self.y()) != getattr(self, "_p0", None):
                self._save_pos()

        bar.mousePressEvent = _press
        bar.mouseReleaseEvent = _rel
        return bar

    def _btns(self):
        # 按钮行: 两个 32 高 stretch 均分, 边距/间距与旧版同 (8,8,8,4) / 3
        w, l = _plain("h")
        l.setContentsMargins(8, 8, 8, 4)
        l.setSpacing(3)
        res = _make_btn("取消最小化", Colors.BLUE, hover=Colors.ACCENT,
                        font=FONT_B, height=32)
        res.clicked.connect(lambda: self.on_restore and self.on_restore())
        l.addWidget(res, 1)
        self.go = _make_btn("▶ 全部开始", Colors.GREEN, hover=Colors.HOVER_GREEN,
                            font=FONT_B, height=32)
        self.go.clicked.connect(self.toggle_all)
        l.addWidget(self.go, 1)
        return w

    def toggle_all(self):
        # 全局启停转主窗同一条真启停路: 只翻 Model 标志的 m.toggle_all() 不开线程
        # (Runner.start_all 全仓唯一调用点是 win.toggle_all_tasks), 转过去完事
        # 它自己会回推 sync_btn
        w = getattr(self.m, "_main_win", None) if self.m else None
        if w is not None and hasattr(w, "toggle_all_tasks"):
            w.toggle_all_tasks()
            return
        if self.m:
            self.m.toggle_all()      # 无主窗(裸 Model 场景)只翻标志
        self.sync_btn()

    def sync_btn(self):
        # 按钮与状态行一次读 Model(与主窗 dock 同源), 只在这里改文案与色, 不轮询
        n = len(self.m.tasks) if self.m else 0
        on = self.m.running if self.m else 0
        self.running = on > 0
        self.go.setText("■ 全部停止" if on else "▶ 全部开始")
        flat_btn(self.go, Colors.RED if on else Colors.GREEN,
                 hover=Colors.HOVER_RED if on else Colors.HOVER_GREEN)
        if on:
            self._st(f"● 运行中 {on}/{n}", Colors.GREEN)
        elif n:
            self._st(f"● 已停止 {n} 个任务", Colors.DIM)
        else:
            self._st("● 就绪", Colors.DIM)

    def rebuild(self):
        # Model.refresh 的迷你窗入口: chip 已删, 任务数变化只需重算状态行
        self.sync_btn()

    def _st(self, text, color):
        self.st.setText(text)
        style_label(self.st, color)

    def _save_pos(self):
        # 与旧版同键存位置, wire.show_mini 每次显示读它 —— 主窗/迷你窗各记各的
        s = load_settings()
        s["mini_pos_x"], s["mini_pos_y"] = self.x(), self.y()
        save_settings(s)
