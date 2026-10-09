"""
图像标定：全屏框选目标区域 → 截取存为模板 → on_got 回调
capture_template 为通用框选存图原语（wait 追加 / branch 选项新增与重拍共用）
add_image_wait_action = capture_template + 追加 wait_image 动作
"""
"""
框选输入层 —— 全屏框选截取模板 / 只取矩形区域

从 ui/vision_capture.py 复制(隔离副本): 遮罩交互、冻结帧、DPR 物理坐标换算、
纯色选区拦截、模板落盘 都是功能; 只把与旧窗口的绑定换成新 UI 的。

改动三处:
  * 占用标记 task._capturing_image -> 模块级 _BUSY(不再依赖任务对象)
  * task.actions.append(...)      -> 交给 on_got 回调, 由 Model 接收
  * app._ready                    -> 去掉(那是旧版的"已加载"标志)
app 参数保留原义: 传新 UI 的主窗, 供"让位到屏幕外 + 恢复"用。
"""
import os
import sys

from PySide6.QtCore import Qt, QRect, QPoint, QPointF, QTimer, QEvent
from PySide6.QtGui import QPainter, QPen, QColor, QCursor, QPixmap
from PySide6.QtWidgets import QWidget, QMessageBox, QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Colors
from core import vision
from tasks.keyboard.keyboard_task import make_wait_image_action
from .widgets import tip_label

MIN_SIZE = 8  # 框选最小边长(px)，小于视为误触


_BUSY = False        # 同一时刻只允许一次框选(旧版是 task._capturing_image)


def _notify(app, text):
    """失败提示走主窗的提示条(与 capture 模块共用同一个 sink, 不另建)

    旧版在这里 import .keyboard_mode.show_floating_notification —— 那是旧 UI 的
    浮动通知, ui_v2 没有 keyboard_mode, 一 import 就 ModuleNotFoundError,
    提示反而弹不出来。共享 sink 由 main_v2 在建窗后挂进来。
    """
    from .capture import _SINK
    if _SINK:
        _SINK(text)
    else:
        # 没挂 sink(独立调用/测试) 退回阻塞对话框, 否则失败会静默
        try:
            QMessageBox.warning(app, "框选", text)
        except Exception:
            pass


def _begin():
    global _BUSY
    _BUSY = True


def _end():
    global _BUSY
    _BUSY = False


def _busy():
    return _BUSY


def _phys_bbox(rect, dpr):
    """框选矩形(逻辑坐标) → ImageGrab物理bbox。
    换算实现已收归 core.coords 统一关口(此处仅保留原函数名与签名, 行为不变)"""
    from core.coords import qt_rect_to_phys_bbox
    return qt_rect_to_phys_bbox(rect, dpr)


def _grab_frozen():
    """抓一张全屏冻结帧(QImage, 物理像素)给遮罩垫底。
    遮罩出现前抓, 之后画面怎么动都不影响框选与最终模板 —— 所见即所得"""
    try:
        from PIL import ImageGrab
        from PySide6.QtGui import QImage
        im = ImageGrab.grab(all_screens=True).convert("RGB")
        data = im.tobytes("raw", "RGB")
        q = QImage(data, im.width, im.height, im.width * 3, QImage.Format_RGB888).copy()
        return q
    except Exception:
        return None


class _SelectOverlay(QWidget):
    """全屏框选层：半透明暗罩 + 拖拽矩形，确认/取消走 on_done(accepted, global_rect)"""

    def __init__(self, screen_rect, on_done, frozen=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # 关键属性：缺失时样式表 rgba 的 alpha 不生效，整块变实心黑
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._on_done = on_done
        self._start = None
        self._cur = None
        self._done = False
        # 冻结帧: 遮罩出现那一刻抓的全屏图, 用户框选与最终截图都以它为准。
        # 动态画面(游戏/视频)下, 实时截图会拍到"框完之后"的画面, 与用户所见不符;
        # 用冻结帧则所见即所得, 且与画面是否继续变化完全无关。
        self._frozen = frozen
        self.setGeometry(screen_rect)
        self.setCursor(QCursor(Qt.CrossCursor))
        # 背景不走 QSS：WA_TranslucentBackground 窗口上样式表背景不渲染，由 paintEvent 手画
        tip = tip_label(self, "🖼 拖拽框选目标图像  |  ESC 取消  |  30秒超时",
                        padding="14px 30px")
        tip.adjustSize()
        tip.move((self.width() - tip.width()) // 2, 40)
        tip.show()

    @property
    def frozen(self):
        """冻结帧 QImage(物理像素), 无则 None"""
        return self._frozen

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

    def set_capture_mode(self, on=True):
        """截图模式: 暂停绘制暗罩与选区, 使截图拿到未压暗的原始画面。
        遮罩保持可见(仍接收鼠标), 但画面瞬间变亮 —— 用截图那一刻的原图, 不等隐藏后的画面"""
        self._capture_mode = bool(on)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        if getattr(self, "_capture_mode", False):
            # 截图模式: 什么都不画, 露出原始画面
            p.end()
            return
        # 冻结帧垫底: 用户看到的框选底图就是最终模板的来源, 所见即所得。
        # 冻结帧是物理像素, 按dpr缩放铺满逻辑坐标系的窗口。
        if self._frozen is not None:
            p.drawPixmap(self.rect(), QPixmap.fromImage(self._frozen))
        # 暗罩必须先画且在早退判断之前——这是整个遮罩的底
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))
        if self._start is not None and self._cur is not None:
            rect = QRect(self.mapFromGlobal(self._start), self.mapFromGlobal(self._cur)).normalized()
            p.setPen(QPen(QColor(Colors.BLUE), 2))
            p.drawRect(rect)
            # 框内亮化：局部加深让选区边界清晰（暗罩全屏半透明，选区可读）
            p.fillRect(rect, QColor(255, 255, 255, 18))
        p.end()


def _run_select(app, on_done, on_cancel, handle):
    """框选公共驱动 —— 等图像模板与读数区域两条流程共用的骨架。

    管: 占用检查、主窗让位出屏、遮罩与 30 秒超时、取消/超时的恢复与回调。
    handle(rect, dpr, overlay, restore, done) 管流程各自的取数 —— 模板裁冻结帧
    存文件、区域交付坐标; 收尾(hide/restore/done)由 handle 自己负责, 与原样一致。
    on_done 为 None 时在入口归一化成空操作, 否则收尾处 None() 会抛 TypeError。"""
    on_done = on_done or (lambda: None)
    on_cancel = on_cancel or (lambda: None)
    if _busy():
        return
    _begin()

    _orig_geo = app.geometry()
    screen = app.screen().geometry()
    app.move(screen.width() + 200, screen.height() + 200)

    state = {"done": False}

    def _finish(accepted, rect=None):
        if state["done"]:
            return
        state["done"] = True
        safety_timer.stop()
        _end()

        def _restore():
            overlay.hide()
            overlay.deleteLater()
            app.move(_orig_geo.x(), _orig_geo.y())
            app.raise_()
            app.activateWindow()

        if not accepted:
            QTimer.singleShot(0, lambda: (_restore(), on_cancel and on_cancel()))
            return

        # 遮罩显示期间就取画面/坐标(半透明遮罩只压暗不遮蔽), 隐藏后再取会拿到已变的画面
        _dpr = overlay.screen().devicePixelRatio()  # hide前取屏dpr(隐藏后screen()可能回落主屏)

        def _done_all():
            # 两条流程 finally 里的三行收尾(hide + 恢复主窗 + on_done)只此一份
            overlay.hide()
            _restore()
            on_done()

        QTimer.singleShot(0, lambda: handle(rect, _dpr, overlay, _restore, _done_all))

    overlay = _SelectOverlay(screen, _finish, _grab_frozen())
    safety_timer = QTimer()
    safety_timer.setSingleShot(True)
    safety_timer.timeout.connect(lambda: _finish(False))
    safety_timer.start(30000)

    overlay.show()
    overlay.raise_()
    overlay.activateWindow()


def capture_template(app, on_got, on_done, rel=None, on_cancel=None):
    """全屏框选 → 截取存模板 → on_got(rel)；成功才调 on_done（取消不调）
    rel 指定=覆盖该路径（重拍，缓存自动失效），否则新建路径
    期间把主窗移出屏幕防止截到自己；占用标记复用 task._capturing_image"""
    def _handle(rect, _dpr, overlay, _restore, _done):
        # 遮罩显示期间就把画面抓下来(遮罩半透明, 只压暗不遮蔽内容),
        # 再从里面裁出选区 —— 这样截的是"用户松手那一刻"的画面, 不会因隐藏遮罩后的
        # 等待窗口而拍到已经变化的画面(动态界面下原内容会移位)。
        _err = None
        _exc = None
        try:
            # 逻辑rect→物理bbox: 换算到遮罩所在屏的dpr, 否则150%屏截错位置
            bbox = _phys_bbox(rect, _dpr)
            # 从冻结帧裁剪选区: 与用户框选时看到的完全一致, 画面后续怎么动都不影响
            if overlay.frozen is not None:
                _fx, _fy = bbox[0], bbox[1]
                _fw, _fh = bbox[2] - bbox[0], bbox[3] - bbox[1]
                _full = overlay.frozen
                if (_fx >= 0 and _fy >= 0 and _fx + _fw <= _full.width()
                        and _fy + _fh <= _full.height()):
                    rgb = vision.qimage_to_rgb(_full, _fx, _fy, _fw, _fh)
                else:
                    rgb = None
            else:
                rgb = None
            if rgb is None:
                # 兜底: 无冻结帧或选区越界时才走实时截图
                rgb = vision.grab_rgb(bbox)
            overlay.hide()
            _restore()  # 先恢复窗口, 避免截到主窗
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
                # 记框选时的屏幕绝对坐标, 供固定位置比对使用(不记则该模板走全屏搜索)
                # ref_size=搜索区域尺寸, 供分辨率变化时按比例换算坐标
                vision.save_template_bbox(use_rel, bbox, vision.current_screen_size())
                on_got(use_rel)
        except Exception as e:
            from logger import log_error
            import traceback
            log_error("vision_capture", traceback.format_exc())
            _exc = e
        finally:
            _done()      # hide + 恢复主窗 + on_done, 三件套在 _run_select 一份
        if _err:
            # 父窗传 app: 传 None 会被置顶无边框主窗盖住且模态阻塞主窗
            QMessageBox.warning(app, "模板无效", _err)
        elif _exc:
            # 失败必须让用户看见(如打包版缺依赖), 只写日志会静默吞掉整次框选。
            # 这里原本 import .keyboard_mode.show_floating_notification ——
            # 那是旧 UI 的浮动通知, ui_v2 包里没有 keyboard_mode,
            # 一走这条分支就 ModuleNotFoundError, 提示反而弹不出来。
            _notify(app, f"✕ 截图失败（{type(_exc).__name__}），详见 runtime.log")

    _run_select(app, on_done, on_cancel, _handle)



def add_image_wait_action(app, m, on_done=None):
    """框选模板 -> 写进 Model 的"等图像"行

    on_done 是旧版的刷新回调, 新 UI 由 Model 自己 rebuild, 所以可不传。
    模板文件落 templates/ 下, 路径进 wait_image 动作, 与旧版同一套存法。
    """
    from config import load_settings as _ls

    def _on_got(rel_path):
        m.add_image_wait(tpl=rel_path,
                         delay=_ls().get("default_delay", 0.0))
        m.refresh()
        if on_done:
            on_done()

    capture_template(app, _on_got, on_done)


def capture_region(app, on_got, on_done, on_cancel=None):
    """全屏框选 → 只取矩形（不截图不存模板）→ on_got(region, sx, sy, rel)
    region=[x,y,w,h]：绑定时存客户区相对坐标（rel=True），否则存物理绝对坐标；
    sx/sy 恒为录制瞬间的物理绝对快照（运行时换绑/解绑的兜底）"""
    def _handle(rect, _dpr, overlay, _restore, _done):
        try:
            # 遮罩切截图模式后立即取坐标, 不等隐藏后的画面(动态界面会移位)
            overlay.set_capture_mode(True)
            overlay.repaint()
            QApplication.processEvents()
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
            _done()      # hide + 恢复主窗 + on_done, 三件套在 _run_select 一份

    _run_select(app, on_done, on_cancel, _handle)


def add_ocr_read_action(app, m, on_done=None):
    """框选读数区 -> 写进 Model 的"读数"行, 变量名由 Model 自动编号"""
    from config import load_settings as _ls

    def _on_got(region, sx, sy, rel):
        m.add_var_read(region=region, sx=sx, sy=sy, rel=rel,
                       delay=_ls().get("default_delay", 0.0))
        m.refresh()
        if on_done:
            on_done()

    capture_region(app, _on_got, on_done)