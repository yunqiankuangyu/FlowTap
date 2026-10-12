"""
无边框圆角窗口基类 —— 主窗/设置窗/迷你窗共用

圆角为什么必须自绘: 无边框顶层窗口上样式表 border-radius 完全无效, 画出来是纯色方块;
DwmSetWindowAttribute(属性33) 只有直角/8px/4px 三档, 8px 封顶, 要任意半径只能
WA_TranslucentBackground + paintEvent 里 drawRoundedRect。
阴影同理自绘(见 paintEvent 的阴影带): DWM 的描边与投影跟它自己的小圆角走,
自绘大圆角时那圈描边会从透明角里露出来 —— 形状与投影只留一套, DWM 全程 DONOTROUND。
参与圆角的各层容器底色必须全是 transparent, 任一层糊上实色就会方角盖掉圆角。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QRect, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QBrush

from config import Colors
from .window_gate import apply_round_corners

WIN_R = 16          # 窗口圆角半径(与 ui/app.py 的 WIN_RADIUS 同值)
SHADOW = 16         # 阴影带宽: 窗口四周各留 16 透明区, 阴影画在这里面(卡片尺寸不变)


def screen_rect_at(x, y):
    """取 (x, y) 所在屏幕的可用区域, 用来把窗口坐标 clamp 回屏内。

    不用 primaryScreen(): 多屏时主屏右缘与窗口所在屏无关, 据此定位会把窗口
    放到屏幕外。QApplication.screenAt 在点不在任何屏上(拔屏/落盘坐标过期)时
    返回 None, 那种情况退回主屏。
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication
    s = QApplication.screenAt(QPoint(x, y))
    if s is None:
        s = QApplication.primaryScreen()
    return s.availableGeometry()


class V2Win(QWidget):
    # 无边框 + 置顶 + 逐像素透明 + 自绘圆角 + 自绘阴影
    def __init__(self, w, h, radius=WIN_R):
        super().__init__()
        self._r = radius
        self._cw, self._ch = w, h      # 卡片(可见窗体)尺寸
        self._sh = SHADOW              # 阴影带宽
        # 两段色(可选): (标题栏高, 第二段色的 Colors 属性名), None = 整卡单色。
        # 第二段画在标题栏**以下**(标题栏留卡片底色), 与旧版 ui/mini_mode.py 同
        # (mini 底 ACCENT / 标题栏 CARD)。只在 paintEvent 里画, 不新增任何实底容器,
        # 参与圆角的各层仍是透明 —— base.py 头部那条红线不破。只有迷你窗设它。
        self._seg = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # 窗口 = 卡片 + 四周阴影带; 布局边距把内容压回卡片区, 所以内容宽高仍是 w×h
        self.setFixedSize(w + 2 * SHADOW, h + 2 * SHADOW)
        # 窗体不透明度: 建窗即按设置套(与旧 UI window_opacity 同义; 拖滑条的实时链在 main_v2.wire)。
        # 框选遮罩/预览框不套 —— 它们靠半透明标注目标区域, 与旧 UI 排除口径一致。
        try:
            from config import get_setting
            v = float(get_setting("opacity"))
            if 0.0 < v <= 1.0:
                self.setWindowOpacity(v)
        except Exception:
            pass
        apply_round_corners(self)

    def paintEvent(self, e):
        # 实时读主题色, 换主题自动跟随
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            s, cw, ch, r = self._sh, self._cw, self._ch, self._r
            # 阴影: 由外向内叠半透明圆角矩形(靠卡片最深), 代替 DWM 投影 ——
            # DWM 的描边/投影跟它自己的小圆角(封顶8px)走, 自绘大圆角时那圈描边
            # 会从透明角里露出来("旧圆角虚影"), 所以形状和阴影全部自绘、DWM 不参与。
            for i in range(s, 0, -1):
                # 峰值 11 + 指数 2.6: 十六层叠加后贴卡处约 18% 压暗、向外收得更快。
                # 手感调校记录: 58→贴卡70%黑(糊成一坨) / 20+2.2→31%(仍偏重, 用户反馈) /
                # 11+2.6→18%(当前)。改这两个数就行, 改完量"贴卡 lum 与远场之比"。
                a = int(11 * ((s - i + 1) / s) ** 2.6)
                if a <= 0:
                    continue
                p.setBrush(QColor(0, 0, 0, a))
                p.drawRoundedRect(QRectF(s - i, s - i, cw + 2 * i, ch + 2 * i),
                                  r + i, r + i)
            p.setBrush(QBrush(QColor(Colors.CARD)))
            p.drawRoundedRect(QRectF(s, s, cw, ch), r, r)
            # 两段色: 第二段盖住标题栏以下的卡片(见 __init__ 的 _seg)。
            # 分界线用轴对齐 clipRect 切 —— 直且不锯; 下缘圆角由被切的圆角矩形
            # 自己画(AA 只发生在绘制上, 不发生在 clip 上), 所以圆角照旧保住。
            seg = getattr(self, "_seg", None)
            if seg:
                bh = max(0, min(int(seg[0]), ch - 1))
                p.save()
                p.setClipRect(QRect(s, s + bh, cw, ch - bh), Qt.IntersectClip)
                p.setBrush(QBrush(QColor(getattr(Colors, seg[1], Colors.CARD))))
                p.drawRoundedRect(QRectF(s, s, cw, ch), r, r)
                p.restore()
            p.end()
        except Exception:
            pass
        super().paintEvent(e)

    def mount_root(self):
        """窗口壳唯一实现 —— 透明 root 挂进窗口布局, 返回它的内层布局。

        root 必须挂成 self 的属性: 只做局部变量, __init__ 一返回它就被回收,
        整棵子树(标题栏/chips/底部栏)跟着被 Qt 销毁, 之后一访问就报
        "Internal C++ object already deleted"; 也必须 addWidget 进窗口自身的
        layout —— 只 new 不 addWidget, 窗口里只剩 paintEvent 画的圆角底色
        (实测截图全空但所有几何断言都过)。"""
        self.root = QWidget()
        self.root.setStyleSheet("background: transparent")
        out = QVBoxLayout(self)
        # 外圈留阴影带, 内容(卡片)正好是 w×h
        out.setContentsMargins(self._sh, self._sh, self._sh, self._sh)
        out.setSpacing(0)
        out.addWidget(self.root)
        lay = QVBoxLayout(self.root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        return lay

    def _fit_hits(self):
        """透明热区按宿主几何铺开(设置窗主题格 / 迷你窗任务 chip 共用)。

        热区不入布局 —— 入布局会被 QPushButton 的 sizeHint 顶爆宿主;
        setGeometry 用父坐标, 减 1px 边框让热区正好盖住宿主可见区, 再抬到上层。"""
        for cell, hit in getattr(self, "_hits", []):
            g = cell.geometry()
            hit.setGeometry(g.x() + 1, g.y() + 1, g.width() - 2, g.height() - 2)
            hit.raise_()

    def showEvent(self, e):
        # 布局在 showEvent 里还没定稿, 此刻拿到的是默认几何, 直接铺会铺错位置,
        # 所以延后一拍(event loop 转一圈)再按真实几何铺开。
        super().showEvent(e)
        if getattr(self, "_hits", None) is not None:
            QTimer.singleShot(0, self._fit_hits)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "_hits", None) is not None:
            self._fit_hits()
