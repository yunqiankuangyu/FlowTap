"""动作完整设置悬浮页: 设置内容多的动作(wait/branch)独立窗编辑, 编辑期主窗隐藏"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QDoubleSpinBox, QPushButton, QLabel
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QBrush, QColor, QFont, QCursor, QPixmap
from config.themes import Colors
from tasks.keyboard.keyboard_task import fmt_action
from .keyboard_mode import (_make_btn, _make_label, _tint_btn, _fit_spin, _target_combo,
                            _refresh_actions as _refresh_main)

RADIUS = 16
FONT13 = QFont("MiSans", 13, QFont.Bold)


def open_settings_view(app, task, action):
    """打开设置悬浮页并隐藏主窗(不与原窗共存); 关闭时 closeEvent 恢复主窗"""
    v = ActionSettingsView(app, task, action)
    v.adjustSize()
    g = app.geometry()
    v.move(g.center().x() - v.width() // 2, max(0, g.top() + 32))
    v.show()
    v.raise_()
    v.activateWindow()
    app.hide()
    return v


class ActionSettingsView(QWidget):
    def __init__(self, app, task, action):
        super().__init__()
        self._app, self._task, self._action = app, task, action
        self._drag_off = None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(600)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(18, 14, 18, 20)
        self._root.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(4)
        head.addWidget(_make_label(fmt_action(action) + " 设置", font=QFont("MiSans", 15, QFont.Bold)))
        head.addStretch(1)
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.DIM}; border: none; font: bold 15px 'MiSans'; }}"
            f"QPushButton:hover {{ background: {Colors.RED}; }}")
        close_btn.clicked.connect(self.close)
        head.addWidget(close_btn)
        self._root.addLayout(head)

        self._content = QVBoxLayout()
        self._content.setSpacing(10)
        self._root.addLayout(self._content)
        self._build()

    def _card(self, title):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {Colors.ACCENT}; border-radius: 10px; }}")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 10, 16, 12)
        v.setSpacing(8)
        v.addWidget(_make_label(title, font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM))
        self._content.addWidget(card)
        return v

    def _after_change(self, app=None, task=None):
        """搬入段的结构变化回调: 行内摘要同步 + 本页重建"""
        _refresh_main(self._app, self._task)
        self._rebuild()

    def _rebuild(self):
        while self._content.count():
            item = self._content.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # 同步摘树, 防deleteLater异步期残留在子树
                w.deleteLater()
            elif item.layout():
                _clear_layout(item.layout())
        self._build()
        self.adjustSize()

    def _build(self):
        app, task, action = self._app, self._task, self._action
        is_wait = action.get("type") == "wait_image"
        is_branch = action.get("type") == "branch"

        def _refresh_actions(_a=None, _t=None):
            # 遮蔽搬入段的调用: 选项增删排序后重建本页
            self._after_change()

        from .vision_capture import capture_template as _real_capture

        def capture_template(_app, _task, on_got, on_done, rel=None):
            # 遮蔽搬入段的调用: 拍图期间把本页移出屏幕防止截入模板
            g = self.geometry()
            scr = self.screen().geometry()
            self.move(scr.width() + 400, scr.height() + 400)

            def _back():
                self.move(g.x(), g.y())
                self.show()

            def _done():
                _back()
                on_done()

            def _cancel():
                _back()

            _real_capture(_app, _task, on_got, _done, rel=rel, on_cancel=_cancel)

        # 卡1 等待条件: 超时/阈值(后延)/帧/尺度/超时后 (搬入段共享 _ctl)
        _vbox = self._card("等待条件")
        _ctl = QHBoxLayout()
        _ctl.setSpacing(0)
        _ctl.addSpacing(8)
        hold_label = _make_label("超时" if (is_wait or is_branch) else "持续", font=FONT13, color=Colors.DIM)
        _ctl.addWidget(hold_label)

        hold_spin = QDoubleSpinBox()
        if is_wait or is_branch:
            hold_spin.setRange(0, 600)
            hold_spin.setDecimals(0)
            hold_spin.setSingleStep(10)
            hold_spin.setValue(action.get("timeout", 30))
        else:
            hold_spin.setRange(0, 30)
            hold_spin.setDecimals(1)
            hold_spin.setSingleStep(0.1)
            hold_spin.setValue(action.get("hold", 0))
        hold_spin.setFixedHeight(20)
        _fit_spin(hold_spin, font=FONT13)
        hold_spin.textChanged.connect(lambda _t, sp=hold_spin: _fit_spin(sp, font=FONT13))
        hold_spin.setAlignment(Qt.AlignRight)
        hold_spin.setFont(FONT13)
        hold_spin.setStyleSheet(f"QDoubleSpinBox {{ background: transparent; color: {Colors.TEXT}; border: none; padding: 0px; }} QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}")
        hold_spin.valueChanged.connect(lambda v, a=action: a.__setitem__(
            "timeout" if a.get("type") in ("wait_image", "branch") else "hold", round(v, 2)))
        _ctl.addWidget(hold_spin)
        _ctl.addWidget(_make_label("s", font=FONT13, color=Colors.DIM))

        delay_label = _make_label("阈值" if is_wait else "后延", font=FONT13, color=Colors.DIM)
        _ctl.addSpacing(2)  # 组界: 配对内紧、组间松
        _ctl.addWidget(delay_label)

        delay_spin = QDoubleSpinBox()
        if is_wait:
            delay_spin.setRange(0, 1)
            delay_spin.setDecimals(2)
            delay_spin.setSingleStep(0.05)
            delay_spin.setValue(action.get("threshold", 0.85))
        else:
            delay_spin.setRange(0, 30)
            delay_spin.setDecimals(1)
            delay_spin.setSingleStep(0.1)
            delay_spin.setValue(action.get("delay", 0.5))
        delay_spin.setFixedHeight(20)
        _fit_spin(delay_spin, font=FONT13)  # wait=阈值, branch=后延, 都按13pt字宽贴
        delay_spin.setAlignment(Qt.AlignRight)
        delay_spin.setFont(FONT13)
        delay_spin.setStyleSheet(f"QDoubleSpinBox {{ background: transparent; color: {Colors.TEXT}; border: none; padding: 0px; }} QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}")
        delay_spin.valueChanged.connect(lambda v, a=action: a.__setitem__(
            "threshold" if a.get("type") == "wait_image" else "delay", round(v, 2)))
        delay_spin.textChanged.connect(lambda _t, sp=delay_spin: _fit_spin(sp, font=FONT13))
        _ctl.addWidget(delay_spin)
        if not is_wait:
            _ctl.addWidget(_make_label("s", font=FONT13, color=Colors.DIM))
        if is_wait:
            _ctl.addSpacing(2)
            # 帧：防抖连续命中次数
            _ctl.addWidget(_make_label("帧", font=FONT13, color=Colors.DIM))
            hit_spin = QDoubleSpinBox()
            hit_spin.setRange(1, 5)
            hit_spin.setDecimals(0)
            hit_spin.setSingleStep(1)
            hit_spin.setValue(int(action.get("min_hits", 2)))
            hit_spin.setFixedHeight(20)
            _fit_spin(hit_spin, font=FONT13)
            hit_spin.textChanged.connect(lambda _t, sp=hit_spin: _fit_spin(sp, font=FONT13))
            hit_spin.setAlignment(Qt.AlignRight)
            hit_spin.setFont(FONT13)
            hit_spin.setStyleSheet(f"QDoubleSpinBox {{ background: transparent; color: {Colors.TEXT}; border: none; padding: 0px; }} QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}")
            hit_spin.valueChanged.connect(lambda v, a=action: a.__setitem__("min_hits", int(v)))
            _ctl.addWidget(hit_spin)

            _ctl.addSpacing(2)
            # 尺度：多尺度/精确 动态切换（点击翻转 action.scales）
            scale_btn = _make_btn("", font=FONT13, height=20)
            scale_btn.setFixedWidth(60)
            scale_btn.setToolTip("多尺度：UI缩放125%/150%也识别；精确：只按标定原尺寸")
            def _flip_scale(_checked=False, a=action, b=scale_btn):
                cur = a.get("scales") or [1.0, 1.25, 1.5]
                if len(cur) > 1:
                    a["scales"] = [1.0]
                    b.setText("精确")
                    _tint_btn(b, Colors.DIM)
                else:
                    a["scales"] = [1.0, 1.25, 1.5]
                    b.setText("多尺度")
                    _tint_btn(b, Colors.BLUE)
            scale_btn.clicked.connect(_flip_scale)
            _multi = len(action.get("scales") or [1.0, 1.25, 1.5]) > 1
            scale_btn.setText("多尺度" if _multi else "精确")
            _tint_btn(scale_btn, Colors.BLUE if _multi else Colors.DIM)
            _ctl.addWidget(scale_btn)

        if is_wait or is_branch:
            _ctl.addSpacing(2)
            # 超时后行为：跳过/中止 动态切换（中止=红）
            _ctl.addWidget(_make_label("超时后", font=FONT13, color=Colors.DIM))
            ot_btn = _make_btn("", font=FONT13, height=20)
            ot_btn.setFixedWidth(43)
            ot_btn.setToolTip("等待超时后：跳过=继续执行下一动作；中止=终止本轮")
            def _flip_ot(_checked=False, a=action, b=ot_btn):
                if a.get("on_timeout", "skip") == "skip":
                    a["on_timeout"] = "stop"
                    b.setText("中止")
                    _tint_btn(b, Colors.RED)
                else:
                    a["on_timeout"] = "skip"
                    b.setText("跳过")
                    _tint_btn(b, Colors.BLUE)
            ot_btn.clicked.connect(_flip_ot)
            _stop = action.get("on_timeout", "skip") == "stop"
            ot_btn.setText("中止" if _stop else "跳过")
            _tint_btn(ot_btn, Colors.RED if _stop else Colors.BLUE)
            _ctl.addWidget(ot_btn)
        _ctl.addStretch(1)
        _vbox.addLayout(_ctl)

        # 卡2 分支选项: 每选项 缩略图/阈值/尺度/跳到/重拍/排序 + 加分支 (搬入段共享 _vbox)
        if is_branch:
            _vbox = self._card("分支选项 (列表顺序=优先级)")
        if is_branch:
            # 分支子行：每选项 缩略图/阈值/尺度/跳到/📷重拍/✕删/↑↓优先级 + 加分支尾行
            from core import vision as _v
            import os as _os
            options = action.get("options") or []
            if not options:
                _sub0 = QHBoxLayout()
                _sub0.setSpacing(3)
                _sub0.addSpacing(0)
                _sub0.addWidget(_make_label("还没有模板 — 点下方 + 加分支 开始框选", font=QFont("MiSans", 11, QFont.Bold), color=Colors.DIM))
                _sub0.addStretch(1)
                _vbox.addLayout(_sub0)
            for k, option in enumerate(options):
                _subA = QHBoxLayout()
                _subA.setSpacing(0)  # 配对紧挨
                _subA.addSpacing(0)

                _thumb = QLabel()
                _full = _os.path.join(_v._app_dir(), option.get("tpl", ""))
                if _os.path.isfile(_full):
                    from PySide6.QtGui import QPixmap
                    _pm = QPixmap(_full)
                    if not _pm.isNull():
                        _thumb.setPixmap(_pm.scaledToHeight(56))
                if _thumb.pixmap() is None or _thumb.pixmap().isNull():
                    _thumb.setText("—")
                _thumb.setFixedHeight(56)
                _thumb.setFont(FONT13)
                _subA.addWidget(_thumb)
                _subA.addSpacing(2)

                _subA.addWidget(_make_label("阈值", font=FONT13, color=Colors.DIM))
                _th = QDoubleSpinBox()
                _th.setRange(0, 1)
                _th.setDecimals(2)
                _th.setSingleStep(0.05)
                _th.setValue(float(option.get("threshold", 0.85)))
                _th.setFixedHeight(20)
                _fit_spin(_th, font=FONT13)
                _th.setAlignment(Qt.AlignRight)
                _th.setFont(FONT13)
                _th.setStyleSheet(f"QDoubleSpinBox {{ background: transparent; color: {Colors.TEXT}; border: none; padding: 0px; }} QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}")
                _th.valueChanged.connect(lambda v, o=option: o.__setitem__("threshold", round(v, 2)))
                _th.textChanged.connect(lambda _t, sp=_th: _fit_spin(sp, font=FONT13))
                _subA.addWidget(_th)
                _subA.addSpacing(2)

                _sc = _make_btn("", font=FONT13, height=20)
                _sc.setFixedWidth(60)
                def _flip_sc(_c=False, o=option, b=_sc):
                    cur = o.get("scales") or [1.0, 1.25, 1.5]
                    if len(cur) > 1:
                        o["scales"] = [1.0]
                        b.setText("精确")
                        _tint_btn(b, Colors.DIM)
                    else:
                        o["scales"] = [1.0, 1.25, 1.5]
                        b.setText("多尺度")
                        _tint_btn(b, Colors.BLUE)
                _sc.clicked.connect(_flip_sc)
                _m = len(option.get("scales") or [1.0, 1.25, 1.5]) > 1
                _sc.setText("多尺度" if _m else "精确")
                _tint_btn(_sc, Colors.BLUE if _m else Colors.DIM)
                _subA.addWidget(_sc)

                _subA.addSpacing(14)  # 组界: 阈值组↔跳到组
                _subA.addWidget(_make_label("跳到", font=FONT13, color=Colors.DIM))
                _subA.addSpacing(4)
                _subA.addWidget(_target_combo(task, option, big=True))
                _subA.addSpacing(6)

                _cap = _make_btn("📷", bg=Colors.BLUE, hover=Colors.ACCENT, font=FONT13, height=20)
                _cap.setFixedWidth(26)
                _cap.setToolTip("重拍本模板（覆盖原路径）")
                def _recap(_c=False, o=option):
                    capture_template(
                        app, task,
                        on_got=lambda rel, oo=o: oo.__setitem__("tpl", rel),
                        on_done=lambda: _refresh_actions(app, task),
                        rel=o.get("tpl"))
                _cap.clicked.connect(_recap)
                _subA.addWidget(_cap)

                def _del_opt(_c=False, a=action, i=k):
                    (a.get("options") or []).pop(i)
                    _refresh_actions(app, task)

                def _up_opt(_c=False, a=action, i=k):
                    o = a.get("options")
                    if i > 0:
                        o[i - 1], o[i] = o[i], o[i - 1]
                    _refresh_actions(app, task)

                def _down_opt(_c=False, a=action, i=k):
                    o = a.get("options")
                    if i < len(o) - 1:
                        o[i + 1], o[i] = o[i], o[i + 1]
                    _refresh_actions(app, task)

                for _txt, _fn, _tip in (("↑", _up_opt, "上移（列表顺序=优先级）"),
                                        ("↓", _down_opt, "下移"),
                                        ("✕", _del_opt, "删除本选项")):
                    _b = _make_btn(_txt, bg=Colors.DIM, hover=Colors.ACCENT, font=FONT13, height=20)
                    _b.setFixedWidth(24)
                    _b.setToolTip(_tip)
                    _b.clicked.connect(_fn)
                    _subA.addWidget(_b)
                _subA.addStretch(1)  # 多余空间归行尾, 防label被拉宽
                _vbox.addLayout(_subA)

            _subf = QHBoxLayout()
            _subf.setSpacing(3)
            _subf.addSpacing(0)
            _addopt = _make_btn("+ 加分支", bg=Colors.BLUE, hover=Colors.ACCENT, font=FONT13, height=20)
            _addopt.setFixedWidth(92)
            def _add_option(_c=False, a=action):
                capture_template(
                    app, task,
                    on_got=lambda rel, aa=a: aa.setdefault("options", []).append(
                        {"tpl": rel, "threshold": 0.85, "scales": [1.0, 1.25, 1.5],
                         "min_hits": 2, "target": None}),
                    on_done=lambda: _refresh_actions(app, task))
            _addopt.clicked.connect(_add_option)
            _subf.addWidget(_addopt)
            _subf.addStretch(1)
            _vbox.addLayout(_subf)

    def mousePressEvent(self, e):
        # 窗口拖拽: 按下记录偏移(子控件消费各自事件, 到不了这里)
        if e.button() == Qt.LeftButton:
            self._drag_off = e.globalPosition().toPoint() - self.geometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if getattr(self, "_drag_off", None) is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_off)
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_off = None
        super().mouseReleaseEvent(e)

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(Colors.CARD)))
            p.drawRoundedRect(QRectF(self.rect()), RADIUS, RADIUS)
            p.end()
        except Exception:
            pass
        super().paintEvent(event)

    def closeEvent(self, event):
        # 关闭=回主窗: 恢复显示并刷新行内摘要
        _refresh_main(self._app, self._task)
        self._app.show()
        self._app.raise_()
        self._app.activateWindow()
        super().closeEvent(event)


def _clear_layout(lay):
    while lay.count():
        item = lay.takeAt(0)
        w = item.widget()
        if w:
            w.setParent(None)
            w.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())
