"""
图像标定：全屏框选目标区域 → 截取存为模板 → on_got 回调
capture_template 为通用框选存图原语（wait 追加 / branch 选项新增与重拍共用）
add_image_wait_action = capture_template + 追加 wait_image 动作
"""
import os
import sys

from PySide6.QtCore import Qt, QRect, QPoint, QPointF, QTimer, QEvent
from PySide6.QtGui import QPainter, QPen, QColor, QCursor
from PySide6.QtWidgets import QWidget, QLabel, QMessageBox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Colors, FONT_B
from core import vision
from tasks.keyboard.keyboard_task import make_wait_image_action
from ui.widgets import tip_qss

MIN_SIZE = 8  # 框选最小边长(px)，小于视为误触


def _phys_bbox(rect, dpr):
    """框选矩形(逻辑坐标) → ImageGrab物理bbox。
    换算实现已收归 core.coords 统一关口(此处仅保留原函数名与签名, 行为不变)"""
    from core.coords import qt_rect_to_phys_bbox
    return qt_rect_to_phys_bbox(rect, dpr)


class _SelectOverlay(QWidget):
    """全屏框选层：半透明暗罩 + 拖拽矩形，确认/取消走 on_done(accepted, global_rect)"""

    def __init__(self, screen_rect, on_done):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # 关键属性：缺失时样式表 rgba 的 alpha 不生效，整块变实心黑
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._on_done = on_done
        self._start = None
        self._cur = None
        self._done = False
        self.setGeometry(screen_rect)
        self.setCursor(QCursor(Qt.CrossCursor))
        # 背景不走 QSS：WA_TranslucentBackground 窗口上样式表背景不渲染，由 paintEvent 手画
        tip = QLabel("🖼 拖拽框选目标图像  |  ESC 取消  |  30秒超时", self)
        tip.setFont(FONT_B)
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet(tip_qss(padding="14px 30px"))
        tip.adjustSize()
        tip.move((self.width() - tip.width()) // 2, 40)
        tip.show()

    def _finish(self, accepted, rect=None):
        if self._done:
            return
        self._done = True
        self._on_done(accepted, rect)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._finish(False)
        else:
            super().keyPressEvent(e)

    def changeEvent(self, e):
        super().changeEvent(e)
        # 失焦（如按 Win 弹开始菜单，shell 会把它提到 topmost 栈顶盖住本窗）→ 延迟重抢顶层
        if e.type() == QEvent.ActivationChange and not self.isActiveWindow() and not self._done:
            QTimer.singleShot(250, self._retop)

    def _retop(self):
        if self._done or not self.isVisible():
            return
        # topmost 层内后抢者上：只改视觉 Z 序，不抢输入焦点（SWP_NOACTIVATE）
        import ctypes
        HWND_TOPMOST = -1
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(
            int(self.winId()), HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        self.raise_()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._start = e.globalPosition().toPoint()
            self._cur = self._start
            self.update()

    def mouseMoveEvent(self, e):
        if self._start is not None:
            self._cur = e.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._start is None:
            return
        end = e.globalPosition().toPoint()
        rect = QRect(self._start, end).normalized()
        if rect.width() >= MIN_SIZE and rect.height() >= MIN_SIZE:
            self._finish(True, rect)
        else:
            self._start = None
            self._cur = None
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        # 暗罩必须先画且在早退判断之前——这是整个遮罩的底
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))
        if self._start is not None and self._cur is not None:
            rect = QRect(self.mapFromGlobal(self._start), self.mapFromGlobal(self._cur)).normalized()
            p.setPen(QPen(QColor(Colors.BLUE), 2))
            p.drawRect(rect)
            # 框内亮化：局部加深让选区边界清晰（暗罩全屏半透明，选区可读）
            p.fillRect(rect, QColor(255, 255, 255, 18))
        p.end()


def capture_template(app, task, on_got, on_done, rel=None, on_cancel=None):
    """全屏框选 → 截取存模板 → on_got(rel)；成功才调 on_done（取消不调）
    rel 指定=覆盖该路径（重拍，缓存自动失效），否则新建路径
    期间把主窗移出屏幕防止截到自己；占用标记复用 task._capturing_image"""
    if not getattr(app, "_ready", False):
        return
    if getattr(task, "_capturing_image", False):
        return
    task._capturing_image = True
    task._action_frame.setVisible(True)

    _orig_geo = app.geometry()
    screen = app.screen().geometry()
    app.move(screen.width() + 200, screen.height() + 200)

    state = {"done": False}

    def _finish(accepted, rect=None):
        if state["done"]:
            return
        state["done"] = True
        safety_timer.stop()
        task._capturing_image = False

        def _restore():
            overlay.hide()
            overlay.deleteLater()
            app.move(_orig_geo.x(), _orig_geo.y())
            app.raise_()
            app.activateWindow()

        if not accepted:
            QTimer.singleShot(0, lambda: (_restore(), on_cancel and on_cancel()))
            return

        # 先藏遮罩再截图，等 DWM 合成一帧，避免截到暗罩
        _dpr = overlay.screen().devicePixelRatio()  # hide前取屏dpr(隐藏后screen()可能回落主屏)
        overlay.hide()

        def _grab_and_save():
            _err = None
            _exc = None
            try:
                # 逻辑rect→物理bbox: 换算到遮罩所在屏的dpr, 否则150%屏截错位置
                bbox = _phys_bbox(rect, _dpr)
                rgb = vision.grab_rgb(bbox)
                _std = vision.template_sigma(rgb)
                if _std < vision.MIN_TEMPLATE_STD:
                    # 纯色选区无法识别(σ≈0时匹配恒为1.0), 拦下提示重框; 重拍场景原模板不被覆盖
                    _err = (f"所选区域几乎是纯色（对比度 std={_std:.1f}，低于 {vision.MIN_TEMPLATE_STD}），"
                            "无法生成可识别的模板，请框选包含文字、图案或按钮的区域。")
                    if rel:
                        _err += " 原模板未被覆盖。"
                    from logger import log_info
                    log_info("capture_flat", f"std={_std:.2f} 拒绝保存")
                else:
                    from PIL import Image
                    use_rel = rel or vision.new_template_path()
                    vision.save_template(Image.fromarray(rgb), use_rel)
                    on_got(use_rel)
            except Exception as e:
                from logger import log_error
                import traceback
                log_error("vision_capture", traceback.format_exc())
                _exc = e
            finally:
                _restore()
                on_done()
            if _err:
                #父窗传app: 传None会被置顶无边框主窗盖住且模态阻塞主窗(同试读弹窗的坑)
                QMessageBox.warning(app, "模板无效", _err)
            elif _exc:
                # 失败必须让用户看见(如打包版缺依赖), 只写日志会静默吞掉整次框选
                from .keyboard_mode import show_floating_notification
                show_floating_notification(
                    app, f"✕ 截图失败（{type(_exc).__name__}），详见 runtime.log", duration_ms=4000)

        QTimer.singleShot(100, _grab_and_save)

    overlay = _SelectOverlay(screen, _finish)
    safety_timer = QTimer()
    safety_timer.setSingleShot(True)
    safety_timer.timeout.connect(lambda: _finish(False))
    safety_timer.start(30000)

    overlay.show()
    overlay.raise_()
    overlay.activateWindow()


def add_image_wait_action(app, task, on_done):
    """进入框选模式，选中后把 wait_image 动作追加进 task.actions 并调 on_done 刷新"""
    from config import load_settings as _ls

    def _on_got(rel_path):
        task.actions.append(make_wait_image_action(
            rel_path,
            threshold=0.85,
            timeout=30,
            delay=_ls().get("default_delay", 0.0),
        ))

    capture_template(app, task, _on_got, on_done)


def capture_region(app, task, on_got, on_done, on_cancel=None):
    """全屏框选 → 只取矩形（不截图不存模板）→ on_got(region, sx, sy, rel)
    region=[x,y,w,h]：绑定时存客户区相对坐标（rel=True），否则存物理绝对坐标；
    sx/sy 恒为录制瞬间的物理绝对快照（运行时换绑/解绑的兜底）"""
    if not getattr(app, "_ready", False):
        return
    if getattr(task, "_capturing_image", False):
        return
    task._capturing_image = True
    task._action_frame.setVisible(True)

    _orig_geo = app.geometry()
    screen = app.screen().geometry()
    app.move(screen.width() + 200, screen.height() + 200)

    state = {"done": False}

    def _finish(accepted, rect=None):
        if state["done"]:
            return
        state["done"] = True
        safety_timer.stop()
        task._capturing_image = False

        def _restore():
            overlay.hide()
            overlay.deleteLater()
            app.move(_orig_geo.x(), _orig_geo.y())
            app.raise_()
            app.activateWindow()

        if not accepted:
            QTimer.singleShot(0, lambda: (_restore(), on_cancel and on_cancel()))
            return

        _dpr = overlay.screen().devicePixelRatio()
        overlay.hide()

        def _deliver():
            try:
                x0, y0, x1, y1 = _phys_bbox(rect, _dpr)
                w, h = max(1, x1 - x0), max(1, y1 - y0)
                from core.window_gate import get_bound_process, window_at_point
                from core import vision
                rel, rx, ry = False, x0, y0
                bound = get_bound_process()
                if bound:
                    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                    hwnd = window_at_point(cx, cy, exclude=int(overlay.winId()), process=bound)
                    if hwnd:
                        bb = vision.client_area_bbox(hwnd)
                        if bb:
                            rel = True
                            rx, ry = x0 - bb[0], y0 - bb[1]
                on_got([rx, ry, w, h], x0, y0, rel)
            except Exception:
                from logger import log_error
                import traceback
                log_error("capture_region", traceback.format_exc())
            finally:
                _restore()
                on_done()

        QTimer.singleShot(100, _deliver)

    overlay = _SelectOverlay(screen, _finish)
    safety_timer = QTimer()
    safety_timer.setSingleShot(True)
    safety_timer.timeout.connect(lambda: _finish(False))
    safety_timer.start(30000)

    overlay.show()
    overlay.raise_()
    overlay.activateWindow()


def add_ocr_read_action(app, task, on_done):
    """框选读数区 → 追加 ocr_read 动作（默认变量名自动生成）→ on_done 刷新"""
    from config import load_settings as _ls
    from tasks.keyboard.keyboard_task import make_ocr_read_action, next_var_name

    def _on_got(region, sx, sy, rel):
        act = make_ocr_read_action(region, next_var_name(task.actions, getattr(task, "vars", None)),
                                    delay=_ls().get("default_delay", 0.0))
        act["sx"], act["sy"], act["rel"] = sx, sy, rel
        task.actions.append(act)

    capture_region(app, task, _on_got, on_done)