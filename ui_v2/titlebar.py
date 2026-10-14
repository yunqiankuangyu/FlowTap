"""
标题栏与窗口拖动 —— 从 ui/titlebar.py 原样复制(隔离副本)

隔离说明: 新 UI 不引用 ui/ 下任何代码。这份与旧文件内容一致(含 build_titlebar
的 buttons/height/title 可选参数与 attach_drag), 新 UI 用后两个参数定制自己的
标题栏, 旧文件保持不动。

相对导入指向同目录的 .widgets(隔离副本), 原文件的 sys.path 注入已删
(新 UI 不依赖项目根路径)。另加两处: 按钮句柄挂 app._title_btns(宿主就地换态用)、
最大化钮的程序绘制双态图标(StateIconBtn, 不走字体字形)。
"""
"""
标题栏组件 (PySide6) — 对齐原版 CTk 样式
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QPainter, QPainterPath, QPen, QColor

from config import Colors, FONT_B
from .widgets import btn_qss, titlebar_qss, _make_label, F17   # ui_v2/widgets.py(隔离副本)

TITLEBAR_H = 36          # 标题栏高(新稿 36, 老版 32) —— 主窗/设置窗共用
MINI_TITLEBAR_H = 28     # 迷你窗标题栏压到 28(主窗 36 的一半档)
ICON_PX = 14             # 最大化钮图标边长(逻辑px, 23px 钮内居中, 与 17px 字形体量相当)
ICON_STROKE = 1.5        # 图标线宽(逻辑px, 细线口径)


def _icon_path(maxed):
    """双态图标的路径, 坐标按 14x14 逻辑框写(改 ICON_PX 时整体等比缩放)"""
    k = ICON_PX / 14.0
    g = QPainterPath()
    if maxed:
        # 还原态: 双框嵌套。前框整画, 后框只画露在前框外的那截 ——
        # 不拿底色矩形挖遮挡, 透明底/换主题都不会露馅
        m, b, o = 1.0 * k, 8.6 * k, 5.4 * k   # 后框左上 / 后框右下 / 前框左上
        g.moveTo(b, o)
        g.lineTo(b, m)
        g.lineTo(m, m)
        g.lineTo(m, b)
        g.lineTo(o, b)          # 两个端点正落在前框的边上, 收口不留缝
        g.addRect(o, o, 7.6 * k, 7.6 * k)     # 前框
    else:
        # 最大化态: 四角向外(展开语义), 角顶在外、开口朝中心 —— 全屏/最大化的通用符号
        x0 = y0 = 1.0 * k
        x1 = y1 = 13.0 * k
        a = 4.0 * k             # 每段折线的臂长
        g.moveTo(x0, y0 + a)
        g.lineTo(x0, y0)
        g.lineTo(x0 + a, y0)
        g.moveTo(x1 - a, y0)
        g.lineTo(x1, y0)
        g.lineTo(x1, y0 + a)
        g.moveTo(x1, y1 - a)
        g.lineTo(x1, y1)
        g.lineTo(x1 - a, y1)
        g.moveTo(x0 + a, y1)
        g.lineTo(x0, y1)
        g.lineTo(x0, y1 - a)
    return g


class StateIconBtn(QPushButton):
    """标题栏双态图标钮 —— 图标在 paintEvent 里现画, 不走字体字形。

    不预渲染 QPixmap 而是画在按钮上: 颜色每帧读当前 Colors(换主题随刷随变,
    不用另挂钩子), 居中与 DPI 由 widget 绘制自己兜(125%/150% 下线条不糊)。
    形态调 set_maxed 切, 颜色随 hover 在 DIM/TEXT 间换, 与字形钮同一口径。"""

    def __init__(self):
        super().__init__()
        self._maxed = False
        self._hov = False

    def set_maxed(self, on):
        #最大化⇄还原就地换形态, 调用方是 win_v2._do_max/_undo_max
        on = bool(on)
        if on != self._maxed:
            self._maxed = on
            self.update()

    def enterEvent(self, e):
        self._hov = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hov = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)       # QSS 的底色/hover 底先照常画, 图标压在上面
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate((self.width() - ICON_PX) / 2, (self.height() - ICON_PX) / 2)
        pen = QPen(QColor(Colors.TEXT if self._hov else Colors.DIM))
        pen.setWidthF(ICON_STROKE)
        pen.setCapStyle(Qt.FlatCap)      # 线端齐根收, 双框交界不凸头
        pen.setJoinStyle(Qt.RoundJoin)   # 转角微圆, 对齐全局小圆角口径
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(_icon_path(self._maxed))
        p.end()


def build_titlebar(app, buttons=None, height=32, title=None):
    """构建标题栏

    buttons: [(text, hover_color, callback[, icon]), ...] 覆盖默认三按钮(新 UI 传
    自己的 —/图标钮/✕ 与回调; 第4项 True = 双态自绘图标钮, 文字忽略)。
    为 None 时用旧版默认组合。
    height:  标题栏高度, 新 UI 用 36。
    title:   标题文字, 为 None 时读设置里的自定义标题。
    """
    bar = QWidget()
    bar.setFixedHeight(height)
    #底色透明+标题字色(三按钮各自make_title_btn设样式, bar级兜底是死规则已删)
    bar.setStyleSheet(titlebar_qss())

    layout = QHBoxLayout(bar)
    layout.setContentsMargins(11, 0, 4, 0)
    layout.setSpacing(0)

    # 标题（可自定义，从设置读取）
    from config import load_settings
    custom_title = load_settings().get("window_title", "")
    title = _make_label(title or custom_title or "FlowTap", font=FONT_B)
    layout.addWidget(title)
    app._title_label = title
    layout.addStretch()

    # 按钮容器
    btn_container = QWidget()
    btn_layout = QHBoxLayout(btn_container)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    btn_layout.setSpacing(0)

    def make_title_btn(text, on_click, hover_color=None, icon=False):
        #icon=True 建双态图标钮(文字忽略, 图标由 StateIconBtn 自绘), 其余同字形钮
        btn = StateIconBtn() if icon else QPushButton(text)
        btn.setFixedSize(23, 23)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        if hover_color:
            btn.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=hover_color,
                                      hover_fg=Colors.TEXT, font=F17, radius=None))
        btn.clicked.connect(on_click)
        return btn

    # 元组顺序为 (文字, hover色, 回调[, icon]) —— 与下面解包一致
    if buttons is None:
        buttons = [("—", Colors.BLUE, app._minimize_to_mini),
                   ("⚙", Colors.BLUE,
                    lambda: app._show_mode("keyboard" if app._current_mode == "settings"
                                           else "settings")),
                   ("✕", Colors.RED, app.quit_app)]
    #按钮句柄挂给宿主(app), 调用方就地换字形/换图标形态时按位取(主窗最大化⇄还原用),
    #不去 findChildren 猜顺序 —— 标签与按钮混排, 顺序一变就取错
    app._title_btns = []
    for text, hover_color, on_click, *rest in buttons:
        b = make_title_btn(text, on_click, hover_color, icon=bool(rest and rest[0]))
        btn_layout.addWidget(b)
        app._title_btns.append(b)

    layout.addWidget(btn_container)

    # ── 拖动支持 ──
    attach_drag(app, bar)

    return bar


def attach_drag(win, target):
    """把窗口拖动接到 target 上。

    无边框窗口没有系统标题栏, 不接这里就完全拖不动 —— 原版靠系统标题栏,
    新 UI 自己画标题栏, 拖动必须显式接。独立成函数是为了让任何控件区域
    (标题栏/空白处/迷你窗)都能复用同一份实现, 而不是各写一遍。

    偏移用 frameGeometry 而非 geometry: 无边框窗口在 Windows 上 frameGeometry
    才含真实窗口位置, geometry 在部分 DPI 下与之差一个边框宽度, 会导致拖动
    时窗口跟手偏移几像素。
    """
    win._drag_data = {"x": 0, "y": 0, "dragging": False}

    def mousePressEvent(e):
        if e.button() == Qt.LeftButton:
            win._drag_data["x"] = e.globalPosition().x() - win.frameGeometry().x()
            win._drag_data["y"] = e.globalPosition().y() - win.frameGeometry().y()
            win._drag_data["dragging"] = True

    def mouseMoveEvent(e):
        if win._drag_data["dragging"]:
            x = int(e.globalPosition().x() - win._drag_data["x"])
            y = int(e.globalPosition().y() - win._drag_data["y"])
            win.move(x, y)

    def mouseReleaseEvent(e):
        win._drag_data["dragging"] = False

    target.mousePressEvent = mousePressEvent
    target.mouseMoveEvent = mouseMoveEvent
    target.mouseReleaseEvent = mouseReleaseEvent
    target.setMouseTracking(True)

    return win._drag_data
