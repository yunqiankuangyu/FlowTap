"""
实时预览面板：显示 wait_image 动作的当前匹配得分与阈值刻度，调阈值即时见效
"""
import os
import sys
import threading

from PySide6.QtCore import Qt, QTimer, QMetaObject, Q_ARG, Slot, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QLabel, QDoubleSpinBox, QPushButton, QHBoxLayout, QVBoxLayout, QApplication)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Colors
from core import coords
from .widgets import spin_flat, _make_btn, btn_qss, label_qss, card_qss

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


class _BBoxOverlay(QWidget):
    """全屏透明置顶窗：在框选位置描一个虚线框。

    位置就是用户当初框的那块（屏幕绝对坐标），不跟随画面内容。
    WA_TransparentForMouseEvents 让鼠标穿透，预览期间照常操作别的窗口。
    """

    def __init__(self, bbox, dpr, vg, color, parent=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)   # 鼠标穿透, 不挡点击
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)       # 显示时不抢焦点
        self.setWindowTitle("FlowTapBoxOverlay")
        self._color = color
        self.setGeometry(vg)
        # bbox 是虚拟桌面物理坐标 -> Qt 全局逻辑 -> 本窗局部坐标
        l, t, r, b = bbox
        x0, y0 = coords.phys_to_qt_point(l, t, dpr)
        x1, y1 = coords.phys_to_qt_point(r, b, dpr)
        self._rect = QRect(x0 - vg.left(), y0 - vg.top(), x1 - x0, y1 - y0)

    def paintEvent(self, e):
        p = QPainter(self)
        pen = QPen(QColor(self._color), 2, Qt.DashLine)
        pen.setDashPattern([5, 4])
        p.setPen(pen)
        p.drawRect(self._rect)
        p.setPen(QPen(QColor(self._color), 1, Qt.SolidLine))
        # 四角加粗实线段, 虚线在浅色背景上偏弱, 加角标更容易看清位置
        L = min(14, self._rect.width() // 3)
        H = min(14, self._rect.height() // 3)
        l, t, w, h = self._rect.left(), self._rect.top(), self._rect.width(), self._rect.height()
        for x0, y0, x1, y1 in ((l, t, l + L, t), (l, t, l, t + H),
                               (l + w, t, l + w - L, t), (l + w, t, l + w, t + H),
                               (l, t + h, l + L, t + h), (l, t + h, l, t + h - H),
                               (l + w, t + h, l + w - L, t + h), (l + w, t + h, l + w, t + h - H)):
            p.drawLine(x0, y0, x1, y1)
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
        # 跟随主窗透明度: 独立顶层窗, 不会继承 app 的 setWindowOpacity
        from .window_opacity import apply_to
        apply_to(self)

        self._score_lbl = QLabel("--")
        self._score_lbl.setFont(QFont("MiSans", 26, QFont.Bold))
        self._score_lbl.setStyleSheet(label_qss(Colors.DIM, border=True))
        self._score_lbl.setFixedWidth(96)
        self._score_lbl.setAlignment(Qt.AlignCenter)

        self._bar = _ScoreBar()

        th_lbl = QLabel("阈值")
        th_lbl.setStyleSheet(label_qss(Colors.DIM, font="bold 14px 'MiSans'", border=True))
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
        title.setStyleSheet(label_qss(Colors.TEXT, font="bold 12px 'MiSans'", border=True))

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

        self.setStyleSheet(card_qss(radius=8, sel="VisionPreviewPanel", extra=f"border: 1px solid {Colors.BLUE};"))
        self.setFixedWidth(330)

        # 后台线程做截图/匹配时, Python 默认的GIL切换间隔(5ms)会让UI线程最坏等5ms+,
        # 实测偶发一次31ms的卡顿; 缩短到2ms后主线程最大延迟降到1.2ms, 无感。
        sys.setswitchinterval(0.002)

        self._busy = False      # 后台是否在跑, 防止任务堆积
        self._timer = QTimer(self)
        # 匹配在后台线程, UI不受影响, 间隔可以短。单轮约74ms(实测), 300ms只用25%占用。
        # 忙不过来时 _busy 会跳过本次, 不会堆积。
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._overlay = self._make_overlay()

    def _make_overlay(self):
        """按框选坐标在屏幕上描一个虚线框(固定位置模式下才有框选坐标)。
        模板是旧的无坐标/开关关掉时没有框可描, 返回 None。"""
        try:
            from core import vision
            if not vision.match_mode_fixed():
                return None
            bbox, _ref = vision.load_template_meta(self._action.get("tpl", ""))
            if not bbox:
                return None
            dpr = coords.system_dpr()
            scr = QGuiApplication.primaryScreen()
            if scr is None:
                return None
            ov = _BBoxOverlay(bbox, dpr, scr.virtualGeometry(), Colors.GREEN)
            ov.show()
            return ov
        except Exception:
            from logger import log_error
            import traceback
            log_error("preview_overlay", traceback.format_exc())
            return None  # 画不出框不影响预览本身

    def _on_th(self, v):
        self._action["threshold"] = round(float(v), 2)
        self._bar.set_value(self._bar.score, self._action["threshold"])
        self._score_lbl.setStyleSheet(label_qss(_score_color(self._bar.score, self._action["threshold"]), border=True))

    def _tick(self):
        """定时器只负责派活: 截图+比对放后台线程, UI 线程永不阻塞。
        单次匹配含全屏截图约100ms+, 放在UI线程会让界面每秒冻住两次(拖窗口一顿一顿、关闭都点不动)"""
        if self._busy:
            return  # 上一轮还没算完, 跳过本次, 避免任务堆积
        a = self._action
        scales = tuple(a.get("scales") or (1.0, 1.25, 1.5))
        # 固定位置比对只认尺度 1.0(match_once 内部已固定), 这里也只跑一轮,
        # 不做尺度轮换——轮换会让读数在不同尺度间跳变, 画面静止时也闪
        from core import vision as _vis
        if _vis.match_mode_fixed():
            scales = (1.0,)
        i = 0
        self._busy = True

        def _work():
            from core import vision
            try:
                _, sc = vision.match_once(
                    a.get("tpl", ""), float(a.get("threshold", 0.85)),
                    scales=(scales[i],), mode=a.get("match_mode"))
            except Exception as e:
                sc = None
                from logger import log_error
                log_error("preview_tick", e)
            # 回到UI线程更新; 面板已关闭时 self 可能已析构, 用 try 兜住
            try:
                QMetaObject.invokeMethod(self, "_apply", Qt.QueuedConnection,
                                          Q_ARG(int, i), Q_ARG(int, len(scales)),
                                          Q_ARG(float, sc if sc is not None else -2.0))
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    @Slot(int, int, float)
    def _apply(self, i, n, sc):
        """后台结果回填(UI线程)。sc=-2 表示该轮失败"""
        self._busy = False
        try:
            a = self._action
            if sc == -2.0:
                self._score_lbl.setText("--")
                return
            # 直接显示本轮结果, 不等三轮跑完再累积——否则尺度轮换期间读数停滞,
            # 看起来像"只有一半时间在刷新"。阈值判断用本轮分数即可(同一尺度足够参考)。
            score = sc
            th = float(a.get("threshold", 0.85))
            self._score_lbl.setText("无效" if score < 0 else f"{score:.2f}")
            self._bar.set_value(score, th)
            self._score_lbl.setStyleSheet(label_qss(
                Colors.RED if score < 0 else _score_color(score, th), border=True))
        except Exception:
            self._busy = False

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
        self._busy = False
        # 虚线框随面板一起收掉, 不能留在屏幕上
        ov = getattr(self, "_overlay", None)
        if ov is not None:
            try:
                ov.close()
                ov.deleteLater()
            except Exception:
                pass
            self._overlay = None
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
        # 跟随主窗透明度: 独立顶层窗, 不会继承 app 的 setWindowOpacity
        from .window_opacity import apply_to
        apply_to(self)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._drag_off = None

        title = QLabel("📷 模板原图")
        title.setStyleSheet(label_qss(Colors.TEXT, font="bold 12px 'MiSans'", border=True))
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=Colors.RED,
                                         hover_fg="#fff", font="bold 13px 'MiSans'", radius=None))
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

        self.setStyleSheet(card_qss(radius=8, sel="TemplateViewPanel", extra=f"border: 1px solid {Colors.BLUE};"))
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
        img_lbl.setStyleSheet(label_qss(border=True))
        info = QLabel()
        info.setStyleSheet(label_qss(Colors.DIM, font="bold 11px 'MiSans'", border=True))
        img = vision._load_template(rel) if rel else None
        if img is None or not os.path.isfile(full):
            img_lbl.setText("模板文件不存在")
            img_lbl.setStyleSheet(label_qss(Colors.DIM, border=True))
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
            info.setStyleSheet(label_qss(Colors.RED, font="bold 11px 'MiSans'", border=True))
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


def find_preview(app=None):
    """当前打开的实时预览面板; 没开返回 None。供透明度统一关口取用。"""
    return _panel if _panel is not None else None


def find_tpl_panel(app=None):
    """当前打开的模板原图面板; 没开返回 None。供透明度统一关口取用。

    面板对象是 show_template_view 的局部变量, 外面拿不到, 只能扫顶层窗按类名认。
    """
    from PySide6.QtWidgets import QApplication
    for w in QApplication.topLevelWidgets():
        if w.__class__.__name__ == "TemplateViewPanel" and w.isVisible():
            return w
    return None