"""
标题栏与窗口拖动 —— 从 ui/titlebar.py 原样复制(隔离副本)

隔离说明: 新 UI 不引用 ui/ 下任何代码。这份与旧文件内容一致(含 build_titlebar
的 buttons/height/title 可选参数与 attach_drag), 新 UI 用后两个参数定制自己的
标题栏, 旧文件保持不动。

改动只有一处: 相对导入指向同目录的 .widgets(隔离副本), 以及删掉原文件里的
sys.path 注入(新 UI 不依赖项目根路径)。
"""
"""
标题栏组件 (PySide6) — 对齐原版 CTk 样式
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from config import Colors, FONT_B
from .widgets import btn_qss, titlebar_qss, _make_label, F17   # ui_v2/widgets.py(隔离副本)

TITLEBAR_H = 36          # 标题栏高(新稿 36, 老版 32) —— 主窗/设置窗共用
MINI_TITLEBAR_H = 28     # 迷你窗标题栏压到 28(主窗 36 的一半档)


def build_titlebar(app, buttons=None, height=32, title=None):
    """构建标题栏

    buttons: [(text, hover_color, callback), ...] 覆盖默认三按钮(新 UI 传
    自己的 —/▢/✕ 与回调)。为 None 时用旧版默认组合。
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

    def make_title_btn(text, on_click, hover_color=None):
        btn = QPushButton(text)
        btn.setFixedSize(23, 23)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        if hover_color:
            btn.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=hover_color,
                                      hover_fg=Colors.TEXT, font=F17, radius=None))
        btn.clicked.connect(on_click)
        return btn

    # 元组顺序为 (文字, hover色, 回调) —— 与下面解包一致
    if buttons is None:
        buttons = [("—", Colors.BLUE, app._minimize_to_mini),
                   ("⚙", Colors.BLUE,
                    lambda: app._show_mode("keyboard" if app._current_mode == "settings"
                                           else "settings")),
                   ("✕", Colors.RED, app.quit_app)]
    for text, hover_color, on_click in buttons:
        btn_layout.addWidget(make_title_btn(text, on_click, hover_color))

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
