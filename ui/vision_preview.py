"""
实时预览面板：显示 wait_image 动作的当前匹配得分与阈值刻度，调阈值即时见效
"""
import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QLabel, QDoubleSpinBox, QPushButton, QHBoxLayout, QVBoxLayout)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Colors

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
        p.fillRect(0, 0, w, h, QColor(255, 255, 255, 26))
        if self.score >= 0:
            sw = int(w * max(0.0, min(1.0, self.score)))
            if self.score >= self.threshold:
                c = QColor("#4ade80")
            elif self.score >= self.threshold - 0.10:
                c = QColor("#facc15")
            else:
                c = QColor(136, 136, 136)
            p.fillRect(0, 0, sw, h, c)
        tx = int(w * self.threshold)
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(tx, 0, tx, h)
        p.end()


def _score_color(score, threshold):
    if score < 0:
        return "#888888"
    if score >= threshold:
        return "#4ade80"
    if score >= threshold - 0.10:
        return "#facc15"
    return "#888888"


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
            "color: #888888; background: transparent; border: none;")
        self._score_lbl.setFixedWidth(96)
        self._score_lbl.setAlignment(Qt.AlignCenter)

        self._bar = _ScoreBar()

        th_lbl = QLabel("阈值")
        th_lbl.setStyleSheet(
            f"color: {Colors.DIM}; background: transparent; border: none; font: bold 11px 'MiSans';")
        self._th_spin = QDoubleSpinBox()
        self._th_spin.setRange(0, 1)
        self._th_spin.setDecimals(2)
        self._th_spin.setSingleStep(0.05)
        self._th_spin.setValue(float(action.get("threshold", 0.85)))
        self._th_spin.setFixedWidth(58)
        self._th_spin.valueChanged.connect(self._on_th)

        stop_btn = QPushButton("⏹")
        stop_btn.setFixedWidth(34)
        stop_btn.setCursor(Qt.PointingHandCursor)
        stop_btn.clicked.connect(self.close)
        stop_btn.setStyleSheet(f"""
            QPushButton {{ background: {Colors.BLUE}; color: #fff; border-radius: 6px; font: bold 13px 'MiSans'; }}
            QPushButton:hover {{ background: {Colors.RED}; }}
        """)

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

        self.setStyleSheet(
            f"VisionPreviewPanel {{ background: #1c1c1e; border: 2px solid {Colors.BLUE}; border-radius: 10px; }}")
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
            self._score_lbl.setText(f"{score:.2f}")
            self._bar.set_value(score, float(a.get("threshold", 0.85)))
            self._score_lbl.setStyleSheet(
                f"color: {_score_color(score, float(a.get('threshold', 0.85)))};"
                " background: transparent; border: none;")
        except Exception as e:
            log_error("preview_tick", e)
            self._score_lbl.setText("--")

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
