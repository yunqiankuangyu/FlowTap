"""
停靠栏 —— 窗口底部居中的浮动磁吸条(全新控件, 原 ui/ 无此件)

与分段胶囊是两类东西, 不要混:
  胶囊 —— 并列的档位选择, 药丸在轨道内滑动(引 ui.segmented.segmented_control)
  停靠栏 —— 窗口级浮层, 项自身变形并推开邻位, 悬浮于内容之上

磁吸落位用几何递推, 不含经验系数:
  主项不动, 从主项向两侧依次落位
  紧邻项落位 = 主项该侧边缘 ± (净距 + 该项变形后半宽)
  再往外的项以上一项的落位边缘为基准递推
  每一级都必须参与递推 —— 被推开的项自身也在放大变宽, 它的外邻若原地不动必被压住

两条实现要点:
  底板与项分离: 底板是独立控件, 只改它的几何来变形, dock 自身盒子不动。
    靠加宽 dock 自身变形会让项的位置跟着移动, 指针判定与形变互相追赶, 边扫边抖。
  命中判定走静止矩形而非变形后的 rect: 项正在放大时 rect 跟着变,
    指针停在边缘会在命中/未命中之间反复跳; 静止矩形是布局值, 判定稳定不抖。
"""
from PySide6.QtCore import (Qt, QRect, QEvent, QPropertyAnimation,
                             QVariantAnimation, QEasingCurve, QPoint)
from PySide6.QtGui import QCursor, QFont, QColor, QFontMetrics
from PySide6.QtWidgets import QWidget, QPushButton, QFrame, QGraphicsDropShadowEffect

from config import Colors, FONT_M
from .widgets import btn_qss, flat_btn, rgba_of

# 各项静止尺寸(与预览稿同一套)
BTN_H = 32        # 项静止高
PAD_X = 16        # 项左右留白
DOCK_GAP = 9      # 变形后相邻项之间的净距, 同时是静止间距(与 panel 的 GAP 同名不同义, 这里加前缀区分)
PAD_Y = 10        # 底板上下留白
PAD_XB = 14       # 底板左右留白
RAD = 13          # 底板圆角
DIST = 14         # 底板距窗口下沿
ANIM = 300        # 磁吸动画时长


class DockBtn(QPushButton):
    # 单项: 静止矩形 + 目标矩形, 动画只改 geometry, 不参与 layout
    def __init__(self, text, dock):
        # parent 必须传给 Dock: 漏传则按钮成了独立顶级窗口, 不在 dock 的子控件树里,
        # geometry 全部正确却一个像素都不渲染(实测底板与按钮全空)
        super().__init__(text, dock)
        self.dock = dock
        self.setFont(FONT_M)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFlat(True)
        # 这里不能 setFixedHeight —— 它会把 minH/maxH 锁死, 之后 setGeometry
        # 给的放大高(_h_of(lvl)=45)会被夹回 32, 结果是"宽高都变了只有高不变"。
        # 高度由每次 apply 的 setGeometry 决定; 初始先给静止高。
        self.setStyleSheet(btn_qss(Colors.ACCENT, Colors.TEXT2, Colors.ACCENT, radius=6))
        self.base = QRect()      # 静止矩形(dock 内坐标, 磁吸时不变)
        self.anim = QPropertyAnimation(self, b"geometry", self)
        self.anim.setDuration(ANIM)
        # 正源是 transition: .3s cubic-bezier(.34,1.4,.5,1) —— 中间会超调再回落
        # (1.4 那个控制点)。OutCubic 是纯减速、没有回弹, 视觉上就"很生硬"。
        # Qt 里 OutBack(cubic-bezier(.34,1.56,.64,1)) 最接近这条曲线。
        self.anim.setEasingCurve(QEasingCurve.OutBack)


class Dock(QWidget):
    # 底部居中停靠栏, 绝对定位浮在窗口之上, 不占布局位置
    def __init__(self, parent=None, items=()):
        super().__init__(parent)
        self.setMouseTracking(True)
        # 分级放大倍率: 距离0/1/2/3及以外
        self.LVL = (1.42, 1.14, 1.06, 1.02)
        self.alpha = 0.9          # 底色不透明度, 由 set_alpha 从全局不透明度换算
        self.on_item = None       # f(下标, 文字) 点击回调, 由外部挂窗口切换/启停逻辑
        self.btns = []
        self.hit = -1             # 当前命中的项下标
        self.bg = QFrame(self)    # 底板(独立控件, 靠改几何变形)
        self.bg.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # 底板的左右伸缩也要走动画: 正源给 .dock::before 写了
        # transition: left .3s, width .3s, 不加就是"宽度从 xpx 硬跳到 ypx"
        self.bg_anim = QPropertyAnimation(self.bg, b"geometry", self)
        self.bg_anim.setDuration(ANIM)
        self.bg_anim.setEasingCurve(QEasingCurve.OutBack)
        # 字号同样要有过渡(正源靠 transform:scale 让文字等比长, Qt 是改 pointSizeF,
        # 直接 setFont 会瞬间换字号, 与宽度动画不同步)
        self.font_from = []
        self.font_to = []
        self.font_anim = QVariantAnimation(self)
        self.font_anim.setDuration(ANIM)
        self.font_anim.setEasingCurve(QEasingCurve.OutBack)
        self.font_anim.valueChanged.connect(self._font_step)
        sh = QGraphicsDropShadowEffect(self.bg)
        sh.setBlurRadius(18)
        sh.setOffset(0, 6)
        sh.setColor(QColor(0, 0, 0, 46))
        self.bg.setGraphicsEffect(sh)
        for it in items:
            self.add(it)

    # ── 增删项 ──
    def add(self, text):
        b = DockBtn(text, self)
        i = len(self.btns)
        b.clicked.connect(lambda _c=False, k=i: self._click(k))
        self.btns.append(b)
        self.bg.lower()          # 底板永远在最底
        b.show()
        return b

    def _click(self, i):
        if self.on_item:
            self.on_item(i, self.btns[i].text())

    # ── 尺寸测量: 文字宽 + 左右留白, 字号按档位缩放 ──
    # 字体走项目正源 FONT_M(config 里的 13pt Bold), 不自创字号;
    # 磁吸缩放按 pointSizeF 等比放大, 不用 QFont("MiSans", n) —— 那个 n 是点不是像素,
    # 12点 ≈ 16像素, 会把整条 dock 撑宽三成。
    def _font_of(self, lvl):
        f = QFont(FONT_M)
        f.setPointSizeF(FONT_M.pointSizeF() * lvl)
        return f

    def _w_of(self, i, lvl):
        fm = QFontMetrics(self._font_of(lvl))
        return int(fm.horizontalAdvance(self.btns[i].text()) + PAD_X * 2 * lvl)

    def _h_of(self, lvl):
        return int(BTN_H * lvl)

    def _lvl_of(self, i):
        if self.hit < 0:
            return 1.0
        t = abs(i - self.hit)
        return self.LVL[t] if t < len(self.LVL) else self.LVL[-1]

    def _font_step(self, t):
        # 字号过渡的每一帧: t 由 0 到 1, 在 font_from/font_to 之间插值
        # (正源用 transform:scale 等比放大文字, 这里等价于逐帧改 pointSizeF)
        for i, b in enumerate(self.btns):
            if i >= len(self.font_from) or i >= len(self.font_to):
                continue
            f = QFont(FONT_M)
            f.setPointSizeF(self.font_from[i] +
                            (self.font_to[i] - self.font_from[i]) * t)
            b.setFont(f)

    # ── 几何递推: 排出一组互不重叠的落位矩形 ──
    def _lvl_at(self, i, i0):
        """i0 落在哪个悬停态, 第 i 项就是第几档。不读 self.hit ——
        _need_total 要遍历所有 i0 各算一次, 若内部读 self.hit
        就会把每一种悬停态都算成当前那一种, 预留量永远偏小。"""
        if i0 < 0:
            return 1.0
        t = abs(i - i0)
        return self.LVL[t] if t < len(self.LVL) else self.LVL[-1]

    def _spread(self, i0):
        """某次悬停态的落位(纯计算, 不动窗口尺寸)
        返回 (basx, ctr, h): basx=各项静止 x, ctr=该态下各项中心, h=最大高"""
        n = len(self.btns)
        basx, w = [], 0
        for i in range(n):
            bw = self._w_of(i, 1.0)
            basx.append(w)          # 先落位再累加, 否则首项 x 等于自身宽
            w += bw + DOCK_GAP
        ctr = [basx[i] + self._w_of(i, 1.0) / 2 for i in range(n)]
        if i0 < 0:
            return basx, ctr, BTN_H
        # 从主项向两侧递推落位中心
        c0 = ctr[i0]
        lw = self._w_of(i0, self._lvl_at(i0, i0)) / 2
        lft, rgt = c0 - lw, c0 + lw
        for j in range(i0 - 1, -1, -1):
            hw = self._w_of(j, self._lvl_at(j, i0)) / 2
            lft = lft - DOCK_GAP - hw
            ctr[j] = lft
            lft -= hw
        for j in range(i0 + 1, n):
            hw = self._w_of(j, self._lvl_at(j, i0)) / 2
            rgt = rgt + DOCK_GAP + hw
            ctr[j] = rgt
            rgt += hw
        h = max(self._h_of(self._lvl_at(i, i0)) for i in range(n))
        return basx, ctr, h

    def _extent(self, i0):
        """该悬停态的 (左边缘, 右边缘), 用展开后的真实半宽算"""
        _, ctr, _ = self._spread(i0)
        n = len(self.btns)
        lo = min(ctr[i] - self._w_of(i, self._lvl_at(i, i0)) / 2 for i in range(n))
        hi = max(ctr[i] + self._w_of(i, self._lvl_at(i, i0)) / 2 for i in range(n))
        return lo, hi

    def _need_total(self):
        """dock 的 (宽度, 静止矩形平移量) —— 全局解, 跨所有悬停态取极值

        要同时满足两件事:
          1. 宽度装得下最宽的那一次悬停展开
          2. 存在一个固定平移量, 让每一种悬停态的按钮都落在安全边距内
        所以不是各态各算一个居中量, 而是取全局 min(lo)/max(hi) 再摊开:
          total = (max_hi - min_lo) + 2*PAD_XB
          off    = PAD_XB - min_lo
        off 固定很关键 —— 命中判定读的是静止矩形(见模块注释), 若 off 跟着悬停态
        变, 指针停在原地时命中矩形会移动, 判定在命中/未命中之间反复跳。

        旧写法按 grow(单按钮最大增量)预留: LVL 全档一起变宽再被递推推开,
        累积量远大于单个增量, 最外侧被推出窗口 —— Qt 对超出父矩形的子控件
        直接裁剪(图里「全部开始」左侧被切)。"""
        n = len(self.btns)
        if n == 0:
            return 0, 0
        import math
        lo_all, hi_all = None, None
        for i0 in range(n):
            lo, hi = self._extent(i0)
            lo_all = lo if lo_all is None else min(lo_all, lo)
            hi_all = hi if hi_all is None else max(hi_all, hi)
        # 取整方向很关键: off 向下取整会让 lo_all+off 比 PAD_XB 少零点几像素,
        # 底板再外扩 PAD_XB 就成了 -1, 依然被裁(真机字体比测试宽, 实测过)。
        # off 向上取整保证左端不越过 PAD_XB, total 再按 off 反推校验右端。
        off = math.ceil(PAD_XB - lo_all)
        total = math.ceil(hi_all + off + PAD_XB)
        return total, off

    def _need_h(self):
        """dock 高度: 按最大档位的按钮高预留, 恒定不变(不随悬停态改变)

        HTML 正源里按钮放大走 transform:scale + origin:bottom center —— transform
        是视觉变换, 不进布局, .dk 的 offsetHeight 恒为 32, 底板 top:0;bottom:0
        于是恒等于 dock 高。Qt 没有 transform, 子控件超出父矩形就被裁剪, 所以
        容器必须按最大放大留足高度, 否则悬停时按钮顶端会被切掉。
        但底板仍按静止高画(见 _move_bg): 放大时按钮顶出底板、底板高度不动,
        这才是正源那个效果。"""
        return self._h_of(max(self.LVL)) + PAD_Y * 2

    def _layout(self, i0):
        # i0 = 命中项下标; -1 表示静止态(全部 1.0 倍, 按静止尺寸均匀排开)
        n = len(self.btns)
        if n == 0:
            return [], []
        basx, ctr, h = self._spread(i0)
        total, off = self._need_total()
        ctr = [c + off for c in ctr]
        hh = self._need_h()          # 恒定, 不随 i0 变
        bases = [QRect(basx[i] + off, hh - PAD_Y - BTN_H, self._w_of(i, 1.0), BTN_H)
                 for i in range(n)]
        targets = []
        for i in range(n):
            lvl = self._lvl_at(i, i0)
            tw, th = self._w_of(i, lvl), self._h_of(lvl)
            # 底对齐(origin:bottom center): 放大时向上长, 底边不动
            targets.append(QRect(int(ctr[i] - tw / 2), hh - PAD_Y - th, tw, th))
        self.setFixedSize(total, hh)
        return bases, targets

    # ── 应用一次状态: 落位 + 底板变形 + 字号 ──
    def apply(self, hit, animate=True):
        self.hit = hit
        n = len(self.btns)
        if n == 0:
            self.hide()
            return
        i0 = hit
        bases, targets = self._layout(i0)
        if animate:
            self.show()
        else:
            self.show()
        # 字号过渡: 记录起点(当前字号)与终点(目标字号), 交给 font_anim 逐帧插值。
        # 直接 setFont 会瞬间换字号, 与宽度动画不同步, 看着就是"字突然跳一下"。
        self.font_from = [b.font().pointSizeF() for b in self.btns]
        self.font_to = [FONT_M.pointSizeF() * self._lvl_at(i, hit)
                        for i in range(n)]
        if animate:
            self.font_anim.stop()
            self.font_anim.setStartValue(0.0)
            self.font_anim.setEndValue(1.0)
            self.font_anim.start()
        else:
            self._font_step(1.0)      # 不走动画就直接落到终值

        for i in range(n):
            b = self.btns[i]
            b.base = bases[i]
            act = (i == hit)
            b.setStyleSheet(btn_qss(Colors.GREEN if act else Colors.ACCENT,
                            "#ffffff" if act else Colors.TEXT2,
                            Colors.HOVER_GREEN if act else Colors.ACCENT,
                            radius=6))
            b.raise_()
            if animate:
                b.anim.stop()
                b.anim.setStartValue(b.geometry())
                b.anim.setEndValue(targets[i])
                b.anim.start()
            else:
                b.setGeometry(targets[i])
        self._move_bg(bases, targets, animate=animate)
        # 变形会改 dock 自身尺寸, 尺寸一变位置就得重算, 否则会滑出窗口底部
        w = self.parentWidget()
        if w is not None:
            self.place(w)

    # ── 底板变形: 覆盖变形后所有项的并集边界 ──
    def _move_bg(self, bases, targets, animate=True):
        # 底板直接取变形后所有按钮的几何并集, 左右各留 PAD_XB 边距。
        # 之前用"与静止基线的差值算出外扩量再摊开"的做法会算窄: 悬停末项时按钮
        # 整体左移, 并集左端跟着左移, 但外扩量仍按右侧差值算, 结果底板左端
        # 反而缩在按钮里面(实测底板[-21~451] 没包住按钮[-28~416])。
        lo = min(t.left() for t in targets)
        hi = max(t.right() for t in targets)
        x = lo - PAD_XB
        w = (hi - lo) + PAD_XB * 2
        # 高度恒为静止高(正源 .dock::before 的 top:0;bottom:0 语义: 悬停只改
        # left/width, 不动高度), 底部对齐 dock 下沿 —— 按钮放大时向上顶出底板,
        # 底板自己纹丝不动。若跟 self.height() 走, 放大瞬间底板会跟着长高。
        bh = BTN_H + PAD_Y * 2
        end = QRect(x, self.height() - bh, w, bh)
        if animate:
            # 正源 .dock::before 有 transition: left .3s, width .3s;
            # 直接 setGeometry 会让底板宽度硬跳(用户原话: 生硬的从 xpx 变成 ypx)
            self.bg_anim.stop()
            self.bg_anim.setStartValue(self.bg.geometry())
            self.bg_anim.setEndValue(end)
            self.bg_anim.start()
        else:
            self.bg.setGeometry(end)
        # 这里不套 card_qss: 底板是 dock 专用的半透明毛玻璃, 底色要带 alpha
        # (跟随全局不透明度), 而 card_qss 的语义是"卡片实色背景 + 圆角",
        # 传 bg="" 只会产出 "background: ;" 这种无效声明, 属于扭曲正源语义。
        # 除这层半透明底板外, dock 内所有按钮仍走 btn_qss / flat_btn。
        self.bg.setStyleSheet(
            f"background: {rgba_of(Colors.CARD, self.alpha)};"
            f" border: 1px solid {rgba_of(Colors.DIM, .5)}; border-radius: {RAD}px;")

    def set_alpha(self, a):
        # 底色不透明度跟随全局不透明度, 0=不显示底色 1=满实
        self.alpha = max(0.0, min(1.0, a))
        if self.bg.isVisible() or self.isVisible():
            self._move_bg(*self._layout(self.hit))

    # ── 指针命中: 走静止矩形, 变形不影响判定 ──
    def mouseMoveEvent(self, e):
        x = e.pos().x()
        hit = -1
        for i, b in enumerate(self.btns):
            if b.base.left() <= x <= b.base.right():
                hit = i
        if hit != self.hit:
            self.apply(hit)

    def leaveEvent(self, e):
        if self.hit != -1:
            self.apply(-1)

    def place(self, win):
        # 停靠在窗口底部正中
        # win 是带阴影带的窗口: 贴卡片下沿, 先把四周 SHADOW 摘掉再居中
        sh = getattr(win, "_sh", 0)
        x = sh + (win.width() - 2 * sh - self.width()) // 2
        self.move(x, win.height() - sh - self.height() - DIST)
