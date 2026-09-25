"""
实时预览面板：显示 wait_image 动作的当前匹配得分与阈值刻度，调阈值即时见效
"""
import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QCursor
from PySide6.QtWidgets import (
    QWidget, QLabel, QDoubleSpinBox, QPushButton, QHBoxLayout, QVBoxLayout, QApplication)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Colors
from .widgets import spin_flat, _make_btn

_panel = None  # 单例（幂等打开）


class _ScoreBar(QWidget):
    """得分进度条 + 白色阈值刻度线；颜色：达标绿/贴线黄/不足灰"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.score = -1.0
        self.threshold = 0.85
        self.setFixedHeight(14)

    def set_value(self, score, threshold):
        self.score = score
        self.threshold = threshold
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(Colors.ACCENT))
        if self.score >= 0:
            sw = int(w * max(0.0, min(1.0, self.score)))
            if self.score >= self.threshold:
                c = QColor(Colors.GREEN)
            elif self.score >= self.threshold - 0.10:
                c = QColor(Colors.YELLOW)
            else:
                c = QColor(Colors.DIM)
            p.fillRect(0, 0, sw, h, c)
        tx = int(w * self.threshold)
        p.setPen(QPen(QColor(Colors.TEXT), 2))
        p.drawLine(tx, 0, tx, h)
        p.end()


def _score_color(score, threshold):
    if score < 0:
        return Colors.DIM
    if score >= threshold:
        return Colors.GREEN
    if score >= threshold - 0.10:
        return Colors.YELLOW
    return Colors.DIM


class VisionPreviewPanel(QWidget):
    """无边框置顶小窗：大号得分 + 分数条 + 阈值 spin（写回 action）+ 停止"""

    def __init__(self, action, on_close=None):
        # 注意：不用 WA_TranslucentBackground——半透明背景窗上 QSS 颜色不渲染（遮罩修复时已确诊），底色走实色
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._action = action
        self._on_close = on_close

        self._score_lbl = QLabel("--")
        self._score_lbl.setFont(QFont("MiSans", 26, QFont.Bold))
        self._score_lbl.setStyleSheet(
            f"color: {Colors.DIM}; background: transparent; border: none;")
        self._score_lbl.setFixedWidth(96)
        self._score_lbl.setAlignment(Qt.AlignCenter)

        self._bar = _ScoreBar()

        th_lbl = QLabel("阈值")
        th_lbl.setStyleSheet(
            f"color: {Colors.DIM}; background: transparent; border: none; font: bold 14px 'MiSans';")
        self._th_spin = QDoubleSpinBox()
        self._th_spin.setRange(0, 1)
        self._th_spin.setDecimals(2)
        self._th_spin.setSingleStep(0.05)
        self._th_spin.setValue(float(action.get("threshold", 0.85)))
        self._th_spin.setFixedWidth(58)
        self._th_spin.setFont(QFont("MiSans", 11, QFont.Bold))
        spin_flat(self._th_spin)  # 隐上下箭头+透底+主题字色, 宽度全留给数值
        self._th_spin.valueChanged.connect(self._on_th)

        stop_btn = _make_btn("⏹", bg=Colors.RED, hover=Colors.HOVER_RED)
        stop_btn.setFixedWidth(34)
        stop_btn.clicked.connect(self.close)

        title = QLabel("🔍 实时预览")
        title.setStyleSheet(
            f"color: {Colors.TEXT}; background: transparent; border: none; font: bold 12px 'MiSans';")

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(th_lbl)
        top.addWidget(self._th_spin)
        top.addWidget(stop_btn)

        mid = QHBoxLayout()
        mid.addWidget(self._score_lbl)
        mid.addWidget(self._bar, 1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)
        lay.addLayout(top)
        lay.addLayout(mid)
        #存attr: UI编辑器wmap按attr名定位控件(悬停参数行→图上高亮)
        self.th_lbl, self.stop_btn, self.title = th_lbl, stop_btn, title
        self.top, self.mid, self.lay = top, mid, lay

        self.setStyleSheet(
            f"VisionPreviewPanel {{ background: {Colors.CARD}; border: 1px solid {Colors.BLUE}; border-radius: 8px; }}")
        self.setFixedWidth(330)

        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _on_th(self, v):
        self._action["threshold"] = round(float(v), 2)
        self._bar.set_value(self._bar.score, self._action["threshold"])
        self._score_lbl.setStyleSheet(
            f"color: {_score_color(self._bar.score, self._action['threshold'])};"
            " background: transparent; border: none;")

    def _tick(self):
        from core import vision
        from logger import log_error
        a = self._action
        try:
            scales = tuple(a.get("scales") or (1.0, 1.25, 1.5))
            _, score = vision.match_once(
                a.get("tpl", ""), float(a.get("threshold", 0.85)), scales=scales)
            if score < 0:
                self._score_lbl.setText("无效")  # 纯色模板/模板比画面大: 无法匹配
            else:
                self._score_lbl.setText(f"{score:.2f}")
            self._bar.set_value(score, float(a.get("threshold", 0.85)))
            self._score_lbl.setStyleSheet(
                f"color: {Colors.RED if score < 0 else _score_color(score, float(a.get('threshold', 0.85)))};"
                " background: transparent; border: none;")
        except Exception as e:
            log_error("preview_tick", e)
            self._score_lbl.setText("--")

    #── 拖动: 面板空白区/标题行按住移动(子控件各自消费, 阈值框和按钮不受影响) ──
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_off = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if getattr(self, "_drag_off", None) is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_off)

    def mouseReleaseEvent(self, e):
        self._drag_off = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, e):
        self._timer.stop()
        cb = self._on_close
        self._on_close = None
        global _panel
        _panel = None
        super().closeEvent(e)
        if cb:
            try:
                cb()
            except Exception:
                from logger import log_error
                import traceback
                log_error("preview_on_close", traceback.format_exc())


def open_preview(action, on_close=None):
    """打开（或换绑到）实时预览面板——幂等不叠窗；on_close 在面板关闭时触发一次"""
    global _panel
    if _panel is not None:
        try:
            if _panel.isVisible():
                _panel._action = action
                _panel._th_spin.setValue(float(action.get("threshold", 0.85)))
                _panel.raise_()
                _panel.activateWindow()
                return _panel
        except RuntimeError:
            pass
        _panel = None
    _panel = VisionPreviewPanel(action, on_close)
    _panel.show()
    _panel.raise_()
    _panel.activateWindow()
    return _panel


_tpl_view = None  # 模板原图查看窗单例


class TemplateViewPanel(QWidget):
    """无边框置顶窗: 标定时截取的静态原图 + 尺寸/对比度; 纯色模板红字警告"""

    def __init__(self, action):
        # 与预览面板同理: 底色走实色, 半透明背景窗上QSS背景不渲染
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._drag_off = None

        title = QLabel("📷 模板原图")
        title.setStyleSheet(
            f"color: {Colors.TEXT}; background: transparent; border: none; font: bold 12px 'MiSans';")
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.DIM}; border: none; font: bold 13px 'MiSans'; }}"
            f"QPushButton:hover {{ background: {Colors.RED}; color: #fff; }}")
        close_btn.clicked.connect(self.close)
        head = QHBoxLayout()
        head.setSpacing(4)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(close_btn)

        self._body = QVBoxLayout()
        self._body.setSpacing(6)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)
        lay.addLayout(head)
        lay.addLayout(self._body)

        self.setStyleSheet(
            f"TemplateViewPanel {{ background: {Colors.CARD}; border: 1px solid {Colors.BLUE}; border-radius: 8px; }}")
        self._load(action)

    def _load(self, action):
        """填充/刷新图片与信息(单例换绑时复用)"""
        while self._body.count():
            it = self._body.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
        import os
        from core import vision
        rel = action.get("tpl", "")
        full = os.path.join(vision._app_dir(), rel)
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("background: transparent; border: none;")
        info = QLabel()
        info.setStyleSheet(
            f"background: transparent; border: none; font: bold 11px 'MiSans'; color: {Colors.DIM};")
        img = vision._load_template(rel) if rel else None
        if img is None or not os.path.isfile(full):
            img_lbl.setText("模板文件不存在")
            img_lbl.setStyleSheet(
                f"color: {Colors.DIM}; background: transparent; border: none;")
            info.setText(rel or "(未标定)")
            self._body.addWidget(img_lbl)
            self._body.addWidget(info)
            return
        pix = QPixmap(full)
        if pix.isNull():
            img_lbl.setText("图片读取失败")
        else:
            # 缩到窗内可读, 防原图(最大1056宽)撑爆屏
            s = min(560 / pix.width(), 640 / pix.height(), 1.0)
            if s < 1.0:
                pix = pix.scaled(int(pix.width() * s), int(pix.height() * s),
                                 Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_lbl.setPixmap(pix)
        sigma = vision.template_sigma(img)
        flat = sigma < vision.MIN_TEMPLATE_STD
        info.setText(f"模板 {img.shape[1]}×{img.shape[0]}  ·  对比度 σ={sigma:.1f}"
                     + ("  ·  纯色模板，无法匹配" if flat else ""))
        if flat:
            info.setStyleSheet(
                f"background: transparent; border: none; font: bold 11px 'MiSans'; color: {Colors.RED};")
        self._body.addWidget(img_lbl)
        self._body.addWidget(info)

    def _center(self):
        scr = QApplication.primaryScreen().geometry()
        g = self.frameGeometry()
        g.moveCenter(scr.center())
        self.move(g.topLeft())

    #── 拖动/ESC: 与预览面板同款 ──
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_off = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if getattr(self, "_drag_off", None) is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_off)

    def mouseReleaseEvent(self, e):
        self._drag_off = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        global _tpl_view
        _tpl_view = None
        super().closeEvent(e)


def open_template_view(action):
    """打开(或换绑到)模板原图查看窗——幂等不叠窗"""
    global _tpl_view
    if _tpl_view is not None:
        try:
            if _tpl_view.isVisible():
                _tpl_view._load(action)
                _tpl_view.raise_()
                _tpl_view.activateWindow()
                return _tpl_view
        except RuntimeError:
            pass
        _tpl_view = None
    _tpl_view = TemplateViewPanel(action)
    _tpl_view.show()
    _tpl_view.raise_()
    _tpl_view.activateWindow()
    _tpl_view._center()
    return _tpl_view
