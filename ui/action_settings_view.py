"""动作完整设置悬浮页: 设置内容多的动作(wait/branch)独立窗编辑, 编辑期主窗隐藏"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QDoubleSpinBox,
                                QPushButton, QLabel, QComboBox, QInputDialog,
                                QMessageBox)
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QBrush, QColor, QFont, QCursor, QPixmap, QFontMetricsF
from config.themes import Colors
from tasks.keyboard.keyboard_task import fmt_action
from .keyboard_mode import (_fit_spin, _target_combo, _mini_combo,
                            DraggableRow, _refresh_actions as _refresh_main)
from .widgets import (_make_btn, _make_label, _tint_btn, spin_flat, btn_qss,
                     card_qss, F12, FONT_M, FONT_M as FONT13)

RADIUS = 16
# 页标题比正文大一号(标题级); 其余标签一律走 FONT13, 不在此处另写字号
FONT_TITLE = QFont("MiSans", 15, QFont.Bold)



def open_settings_view(app, task, action):
    """打开设置悬浮页并隐藏主窗(不与原窗共存); 关闭时 closeEvent 恢复主窗"""
    v = ActionSettingsView(app, task, action)
    v.adjustSize()
    g = app.geometry()
    v.move(g.center().x() - v.width() // 2, max(0, g.top() + 32))
    v.show()
    v.raise_()
    v.activateWindow()
    app._settings_view = v  # 强引用: 槽里丢弃返回值会被PySide6 GC销毁, 主窗已隐藏→全屏消失
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
        # 跟随主窗透明度: 这是独立顶层窗, 不会继承 app 的 setWindowOpacity
        from .window_opacity import apply_to
        apply_to(self)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(18, 14, 18, 20)
        self._root.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(4)
        head.addWidget(_make_label(fmt_action(action) + " 设置", font=FONT_TITLE))
        head.addStretch(1)
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=Colors.RED,
                                         font="bold 15px 'MiSans'", radius=None))
        close_btn.clicked.connect(self.close)
        head.addWidget(close_btn)
        self._root.addLayout(head)

        self._content = QVBoxLayout()
        self._content.setSpacing(10)
        self._root.addLayout(self._content)
        self._build()

    def _card(self, title):
        card = QFrame()
        # CARD底(非ACCENT): 卡片内的ACCENT底下拉才与卡片有层次可见(ACCENT卡+ACCENT下拉=同色隐形)
        card.setStyleSheet(card_qss(Colors.CARD, radius=10))
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 10, 16, 12)
        v.setSpacing(8)
        if title:
            v.addWidget(_make_label(title, font=FONT13, color=Colors.DIM))
        self._content.addWidget(card)
        return v

    def _move_option(self, fr, to):
        """选项拖拽排序核心(手势drop和测试共用): fr→to 交换"""
        opts = self._action.get("options") or []
        if not (0 <= fr < len(opts)) or fr == to:
            return
        o = opts.pop(fr)
        if fr < to:
            to -= 1
        opts.insert(to, o)
        self._after_change()

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
        from .segmented import segmented_control   # 尺度/超时后/比对精度三卡共用
        app, task, action = self._app, self._task, self._action
        is_wait = action.get("type") == "wait_image"
        is_branch = action.get("type") == "branch"
        is_cond = action.get("type") == "cond_branch"
        is_ocr = action.get("type") == "ocr_read"
        is_vset = action.get("type") == "var_set"
        self._opt_rows = []

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

        if not (is_cond or is_ocr or is_vset):  # 条件分支/读数/变量运算都不等待, 参数见下方专属卡组
            # 卡1 等待条件: 标题与参数并为一行(标题左、参数右靠), 搬入段共享 _ctl
            # (仅 wait/branch 需要; 条件分支的参数与说明在下方专属三卡里)
            _vbox = self._card(None)
            _ctl = QHBoxLayout()
            _ctl.setSpacing(0)
            _ctl.addWidget(_make_label("等待条件", font=FONT13, color=Colors.DIM))
            _ctl.addStretch(1)  # 参数整体右靠
            hold_label = _make_label("超时" if (is_wait or is_branch) else "持续", font=FONT13, color=Colors.DIM)
            _ctl.addWidget(hold_label)

            hold_spin = QDoubleSpinBox()
            if is_wait or is_branch:
                hold_spin.setRange(0, 600)
                hold_spin.setDecimals(0)
                hold_spin.setSingleStep(10)
                hold_spin.setValue(action.get("timeout", 30))
                hold_spin.setSpecialValueText("∞")
                hold_spin.setToolTip("填 0 (∞) = 保持等待：一直等到图像出现/分支命中才继续，永不超时")
            else:
                hold_spin.setRange(0, 30)
                hold_spin.setDecimals(1)
                hold_spin.setSingleStep(0.1)
                hold_spin.setValue(action.get("hold", 0))
            hold_spin.setFixedHeight(25)
            _fit_spin(hold_spin, font=FONT13)
            hold_spin.textChanged.connect(lambda _t, sp=hold_spin: _fit_spin(sp, font=FONT13))
            hold_spin.setAlignment(Qt.AlignRight)
            hold_spin.setFont(FONT13)
            spin_flat(hold_spin)
            hold_spin.valueChanged.connect(lambda v, a=action: a.__setitem__(
                "timeout" if a.get("type") in ("wait_image", "branch") else "hold", round(v, 2)))
            _ctl.addWidget(hold_spin)
            _ctl.addWidget(_make_label("s", font=FONT13, color=Colors.DIM))

            delay_label = _make_label("阈值" if is_wait else "后延", font=FONT13, color=Colors.DIM)
            _ctl.addSpacing(12)  # 组界: 配对内紧、组间松
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
            delay_spin.setFixedHeight(25)
            _fit_spin(delay_spin, font=FONT13, extra=6 if is_wait else 0)  # 只有wait行这个框是阈值  # wait=阈值, branch=后延, 都按13pt字宽贴
            delay_spin.setAlignment(Qt.AlignRight)
            delay_spin.setFont(FONT13)
            spin_flat(delay_spin)
            delay_spin.valueChanged.connect(lambda v, a=action: a.__setitem__(
                "threshold" if a.get("type") == "wait_image" else "delay", round(v, 2)))
            delay_spin.textChanged.connect(lambda _t, sp=delay_spin, _x=(6 if is_wait else 0): _fit_spin(sp, font=FONT13, extra=_x))
            _ctl.addWidget(delay_spin)
            if not is_wait:
                _ctl.addWidget(_make_label("s", font=FONT13, color=Colors.DIM))
            if is_wait:
                _ctl.addSpacing(12)
                # 帧：防抖连续命中次数
                _ctl.addWidget(_make_label("帧", font=FONT13, color=Colors.DIM))
                hit_spin = QDoubleSpinBox()
                hit_spin.setRange(1, 5)
                hit_spin.setDecimals(0)
                hit_spin.setSingleStep(1)
                hit_spin.setValue(int(action.get("min_hits", 2)))
                hit_spin.setFixedHeight(25)
                _fit_spin(hit_spin, font=FONT13)
                hit_spin.textChanged.connect(lambda _t, sp=hit_spin: _fit_spin(sp, font=FONT13))
                hit_spin.setAlignment(Qt.AlignRight)
                hit_spin.setFont(FONT13)
                spin_flat(hit_spin)
                hit_spin.valueChanged.connect(lambda v, a=action: a.__setitem__("min_hits", int(v)))
                _ctl.addWidget(hit_spin)


            # ── 卡: 比对尺度 ──
            # 精确/多尺度搬进本页: 行内一行放不下(实测胶囊比旧翻转按钮宽约 100px,
            # 400px 宽的行连同超时/阈值/帧会挤到重叠)。
            if is_wait:
                            v3 = self._card("比对尺度")
                            v3.addWidget(_make_label(
                                            "精确：只按标定原尺寸比对\n"
                                            "多尺度：UI 缩放 125%/150% 也识别",
                                            font=FONT_M, color=Colors.TEXT2))
                            _SCALES = [("精确", "single"), ("多尺度", "multi")]
                            _has_multi = len(action.get("scales") or [1.0, 1.25, 1.5]) > 1
                            def _on_scale(val, a=action):
                                            # 只更新行内摘要, 不重建本页——重建会销毁控件, 点击看起来没反应
                                            a["scales"] = [1.0, 1.25, 1.5] if val == "multi" else [1.0]
                                            _refresh_main(self._app, self._task)
                            _scale_seg = segmented_control(
                                            _SCALES, "multi" if _has_multi else "single", _on_scale, size="normal")
                            v3.addWidget(_scale_seg)

            # ── 卡: 超时后行为 ──
            # 超时=0(∞)=永不超时 → 这一项无意义, 胶囊整体置灰(药丸也要跟着变暗)
            if is_wait or is_branch:
                            v4 = self._card("超时后行为")
                            v4.addWidget(_make_label(
                                            "跳过：继续下一动作\n"
                                            "跳卡：整张卡片本轮作废（等循环后再来）\n"
                                            "中止：终止任务",
                                            font=FONT_M, color=Colors.TEXT2))
                            _OT3 = [("跳过", "skip"), ("跳卡", "skip_card"), ("中止", "stop")]
                            def _ot_cur(a):
                                            v = a.get("on_timeout", "skip")
                                            return "skip" if v == "next" else v   # branch 旧值 next 归一
                            def _on_ot(val, a=action):
                                            a["on_timeout"] = val
                                            _refresh_main(self._app, self._task)
                            _ot_seg = segmented_control(_OT3, _ot_cur(action), _on_ot, size="normal")
                            v4.addWidget(_ot_seg)
                            # 超时=0(∞)=永不超时 → 超时后行为无意义, 胶囊整体置灰
                            _ot_seg.setEnabled(hold_spin.value() > 0)
                            hold_spin.valueChanged.connect(
                                            lambda v, s=_ot_seg: s.setEnabled(v > 0))

            # ── 卡: 比对精度(放最下) ──
            # 放最后: 它是调容错的最终手段, 尺度与超时是基础设置, 先基础后微调
            if is_wait:
                            from core import vision as _vis
                            v2 = self._card("比对精度")
                            v2.addWidget(_make_label(
                                            "档位越靠右越能容忍画面内变化（数字跳动、文字刷新、微小动画）",
                                            font=FONT_M, color=Colors.TEXT2))
                            _MODES = [(_vis.MATCH_MODE_LABEL[k], k) for k in _vis.MATCH_MODE_ORDER]
                            _cur_mode = action.get("match_mode")
                            if _cur_mode not in _vis.MATCH_GRANT:
                                            _cur_mode = "raw"   # 旧动作没这字段=原版
                            def _on_mode(val, a=action):
                                            # 只更新行内摘要, 不重建本页——重建会把控件销毁, 点击看起来没反应
                                            a["match_mode"] = val
                                            _refresh_main(self._app, self._task)
                            seg = segmented_control(_MODES, _cur_mode, _on_mode, size="normal")
                            seg.setToolTip(
                                            "准确率 = 原图准确率 + 模糊准确率×折扣\n"
                                            "原版：不计模糊（0%）\n"
                                            "精确：+9%\n"
                                            "平衡：+15%\n"
                                            "粗略：+21%")
                            v2.addWidget(seg)
                            self.match_seg = seg

            _vbox.addLayout(_ctl)

        # ═══ cond_branch(条件分支)专属卡组 ═══
        # 行内只放摘要+编辑钮, 完整参数与说明在此页(600px宽才有空间写清"不成立会怎样")
        if is_cond:
            from tasks.keyboard.keyboard_task import next_var_name

            def _known_vars():
                return sorted({a.get("var") for a in task.actions if a.get("var")}
                              | set(getattr(task, "vars", {})))

            # ── 卡A 判断条件 ──
            _vbox = self._card("判断条件")
            _rowA = QHBoxLayout()
            _rowA.setSpacing(0)
            _rowA.addWidget(_make_label("变量", font=FONT13, color=Colors.DIM))
            _rowA.addSpacing(4)
            _cur_var = action.get("var", "v1")
            _items = _known_vars() or ["v1"]
            if _cur_var and _cur_var not in _items:
                _items.append(_cur_var)
            _NEW = "＋ 新建变量…"
            var_cb = _mini_combo(_items + [_NEW], _cur_var, 110, h=25)

            def _var_pick(t, a=action):
                if t == _NEW:
                    name, ok = QInputDialog.getText(self, "新建变量",
                                                    "变量名（字母/数字/下划线）：",
                                                    text=next_var_name(task.actions,
                                                                       getattr(task, "vars", None)))
                    if ok and name.strip():
                        a["var"] = name.strip()
                    self._rebuild()   # 重建: 新变量进入全部同类下拉
                    return
                a["var"] = t
                _refresh_actions()
            var_cb.currentTextChanged.connect(_var_pick)
            _rowA.addWidget(var_cb)

            _rowA.addSpacing(14)
            cmp_cb = _mini_combo([">", ">=", "<", "<=", "==", "!="],
                                 action.get("cmp", ">="), 54, h=25)
            cmp_cb.currentTextChanged.connect(lambda t, a=action: (a.__setitem__("cmp", t), _refresh_actions()))
            _rowA.addWidget(cmp_cb)

            _rowA.addSpacing(14)
            _rowA.addWidget(_make_label("值", font=FONT13, color=Colors.DIM))
            _rowA.addSpacing(4)
            val_spin = QDoubleSpinBox()
            val_spin.setRange(-1e9, 1e9)
            val_spin.setDecimals(2)
            val_spin.setValue(action.get("value", 0))
            val_spin.setAlignment(Qt.AlignRight)
            val_spin.setFont(FONT13)
            val_spin.valueChanged.connect(lambda v, a=action: (a.__setitem__("value", v), _refresh_actions()))
            spin_flat(val_spin)
            _fit_spin(val_spin, font=FONT13, extra=10)
            val_spin.textChanged.connect(lambda _t, sp=val_spin: _fit_spin(sp, font=FONT13, extra=10))
            _rowA.addWidget(val_spin)
            _rowA.addStretch(1)
            _vbox.addLayout(_rowA)
            _vbox.addWidget(_make_label("💡 变量来自上方「读数」动作；从未读过的变量按 0 计算",
                                       font=FONT13, color=Colors.DIM))

            # ── 卡B 条件成立时 ──
            _vbox = self._card("条件成立时")
            _rowB = QHBoxLayout()
            _rowB.setSpacing(0)
            _rowB.addWidget(_make_label("跳到", font=FONT13, color=Colors.DIM))
            _rowB.addSpacing(4)
            _tgt_cb = _target_combo(task, action, big=True)
            _rowB.addWidget(_tgt_cb)
            _rowB.addStretch(1)
            _vbox.addLayout(_rowB)
            #未设目标时明确警示: 条件成立也不会跳, 是最易踩的坑
            if not action.get("target"):
                _vbox.addWidget(_make_label("⚠ 还没选目标 —— 条件成立也不会跳转（等同顺序继续），请选一个目标动作",
                                           font=FONT13, color=Colors.RED))
            _vbox.addWidget(_make_label("💡 成立 → 跳到所选动作；不成立 → 顺序继续下一行（不会跳过）",
                                       font=FONT13, color=Colors.DIM))

            # ── 卡C 用法示例 ──
            _vbox = self._card("用法示例")
            _ex = QVBoxLayout()
            _ex.setSpacing(2)
            for _ln in ("① 先用「读数」把目标数字写进变量（如金币数）",
                        "② 本动作判断该变量是否达到阈值，成立就跳到对应动作（如买装备）",
                        "③ 不成立则继续往下走；想循环就在末尾用「跳转」跳回第①步"):
                _ex.addWidget(_make_label(_ln, font=FONT13, color=Colors.DIM))
            _vbox.addLayout(_ex)

            # ── 卡D 后延 ──
            _vbox = self._card(None)
            _rowD = QHBoxLayout()
            _rowD.setSpacing(0)
            _rowD.addWidget(_make_label("后延", font=FONT13, color=Colors.DIM))
            _rowD.addSpacing(4)
            dly = QDoubleSpinBox()
            dly.setRange(0, 600)
            dly.setDecimals(1)
            dly.setSingleStep(0.1)
            dly.setValue(action.get("delay", 0))
            dly.setAlignment(Qt.AlignRight)
            dly.setFont(FONT13)
            dly.setSuffix(" s")
            dly.valueChanged.connect(lambda v, a=action: (a.__setitem__("delay", v), _refresh_actions()))
            spin_flat(dly)
            _fit_spin(dly, font=FONT13, extra=6)
            dly.textChanged.connect(lambda _t, sp=dly: _fit_spin(sp, font=FONT13, extra=6))
            _rowD.addWidget(dly)
            _rowD.addStretch(1)
            _vbox.addLayout(_rowD)

        # ═══ ocr_read(读数)专属卡组 ═══
        # 行内只留摘要+编辑; 框选需看到真实屏幕 -> 点按钮时本页临时隐藏, 复用现成 capture_region
        if is_ocr:
            from tasks.keyboard.keyboard_task import (PATTERN_PRESETS, pattern_label,
                                                       read_region, _parse_num, next_var_name)
            from .vision_capture import capture_region

            def _known_vars_ocr():
                return sorted({a.get("var") for a in task.actions if a.get("var")}
                              | set(getattr(task, "vars", {})))

            # ── 卡A 读数区域 ──
            _vbox = self._card("读数区域")
            _rowE = QHBoxLayout()
            _rowE.setSpacing(0)
            _rg = action.get("region") or []
            if _rg:
                _rowE.addWidget(_make_label(f"已框选：宽 {_rg[2]} × 高 {_rg[3]} 像素"
                                           f"{'（相对绑定窗口）' if action.get('rel') else '（屏幕绝对）'}",
                                           font=FONT13))
            else:
                _rowE.addWidget(_make_label("⚠ 还没框选区域 —— 不框选就读不到任何数字",
                                           font=FONT13, color=Colors.RED))
            _rowE.addStretch(1)
            box_btn = _make_btn("重新框选", bg=Colors.BLUE, hover=Colors.ACCENT,
                                font=FONT13, height=25)
            box_btn.setFixedWidth(78)
            box_btn.setToolTip("全屏拖拽框选读数区域（绑定窗口时存客户区相对坐标，窗口拖走仍读得准）")

            def _rebox(_c=False, a=action):
                # 框选要在真实屏幕上拖拽, 本页与主窗都得让开 -> 先藏本页, 框完再回来
                def _got(region, sx, sy, rel):
                    a["region"], a["sx"], a["sy"], a["rel"] = region, sx, sy, rel
                def _back():
                    self._rebuild()
                    self.show(); self.raise_(); self.activateWindow()
                self.hide()
                QTimer.singleShot(0, lambda: capture_region(self._app, task, _got, _back))
            box_btn.clicked.connect(_rebox)
            _rowE.addWidget(box_btn)
            _rowE.addSpacing(8)
            try_btn = _make_btn("试读", bg=Colors.GREEN, hover=Colors.ACCENT,
                                font=FONT13, height=25)
            try_btn.setFixedWidth(56)
            try_btn.setToolTip("立刻按当前区域试读一次：显示OCR原文与抽取到的数字，所见即所得")

            def _try_read(_c=False, a=action):
                try:
                    raw = read_region(a)
                    num = _parse_num(raw, a.get("pattern") or None)
                    # 父窗传 self._app: 传 None 时弹窗成独立顶层窗会被盖住, 且模态阻塞让窗口像卡死
                    QMessageBox.information(self._app, "试读结果",
                                            f"OCR识别到：{raw or '（空白，没认出文字）'}\n"
                                            f"抽取结果：{num:g}\n\n"
                                            f"想换抽取方式，用下方「取数方式」下拉。")
                except Exception as e:
                    QMessageBox.warning(self._app, "试读失败", f"读取区域出错：{e}")
            try_btn.clicked.connect(_try_read)
            _rowE.addWidget(try_btn)
            _vbox.addLayout(_rowE)

            _vbox.addWidget(_make_label("💡 框选完先「试读」：显示识别到的原文和抽出的数字，确认对了再往下做",
                                       font=FONT13, color=Colors.DIM))

            # ── 卡B 变量 ──
            _vbox = self._card("变量")
            _rowF = QHBoxLayout()
            _rowF.setSpacing(0)
            _rowF.addWidget(_make_label("存到", font=FONT13, color=Colors.DIM))
            _rowF.addSpacing(4)
            _cur = action.get("var", "v1")
            _items = _known_vars_ocr() or ["v1"]
            if _cur and _cur not in _items:
                _items.append(_cur)
            _NEW2 = "＋ 新建变量…"
            var_cb2 = _mini_combo(_items + [_NEW2], _cur, 110, h=25)

            def _var_pick2(t, a=action):
                if t == _NEW2:
                    name, ok = QInputDialog.getText(self, "新建变量",
                                                    "变量名（字母/数字/下划线）：",
                                                    text=next_var_name(task.actions,
                                                                       getattr(task, "vars", None)))
                    if ok and name.strip():
                        a["var"] = name.strip()
                    self._rebuild()
                    return
                a["var"] = t
                _refresh_actions()
            var_cb2.currentTextChanged.connect(_var_pick2)
            _rowF.addWidget(var_cb2)
            _rowF.addStretch(1)
            _vbox.addLayout(_rowF)
            _vbox.addWidget(_make_label("💡 变量名是给后面的「变量运算」「条件分支」用的；改这里，三处一起变",
                                       font=FONT13, color=Colors.DIM))

            # ── 卡C 取数方式 ──
            _vbox = self._card("取数方式")
            _rowG = QHBoxLayout()
            _rowG.setSpacing(0)
            _pats = [lab for lab, _p in PATTERN_PRESETS] + ["自定义…"]
            pat_cb = _mini_combo(_pats, pattern_label(action.get("pattern", "")), 160, h=25)

            def _pat_pick(t, a=action):
                if t == "自定义…":
                    cur, ok = QInputDialog.getText(self, "自定义取数（正则）",
                                                   "从 OCR 文本里提取（取第一个捕获组）：",
                                                   text=a.get("pattern") or "")
                    if ok:
                        a["pattern"] = cur.strip()
                    self._rebuild()
                    return
                for _lab, _p in PATTERN_PRESETS:
                    if _lab == t:
                        a["pattern"] = _p
                        break
                _refresh_actions()
            pat_cb.currentTextChanged.connect(_pat_pick)
            _rowG.addWidget(pat_cb)
            _rowG.addStretch(1)
            _vbox.addLayout(_rowG)
            _vbox.addWidget(_make_label("💡 下拉挑一种抽数字的方式；「自定义…」里可填正则",
                                       font=FONT13, color=Colors.DIM))

            # ── 卡D 后延 ──
            _vbox = self._card(None)
            _rowH = QHBoxLayout()
            _rowH.setSpacing(0)
            _rowH.addWidget(_make_label("后延", font=FONT13, color=Colors.DIM))
            _rowH.addSpacing(4)
            dly2 = QDoubleSpinBox()
            dly2.setRange(0, 600)
            dly2.setDecimals(1)
            dly2.setSingleStep(0.1)
            dly2.setValue(action.get("delay", 0))
            dly2.setAlignment(Qt.AlignRight)
            dly2.setFont(FONT13)
            dly2.setSuffix(" s")
            dly2.valueChanged.connect(lambda v, a=action: (a.__setitem__("delay", v), _refresh_actions()))
            spin_flat(dly2)
            _fit_spin(dly2, font=FONT13, extra=6)
            dly2.textChanged.connect(lambda _t, sp=dly2: _fit_spin(sp, font=FONT13, extra=6))
            _rowH.addWidget(dly2)
            _rowH.addStretch(1)
            _vbox.addLayout(_rowH)

        # ═══ var_set(变量运算)专属卡组 ═══
        # 行内只留摘要+编辑; 参数与说明在此页(与读数/条件分支同一套卡组写法)
        if is_vset:
            from tasks.keyboard.keyboard_task import next_var_name

            def _known_vars_vset():
                return sorted({a.get("var") for a in task.actions if a.get("var")}
                              | set(getattr(task, "vars", {})))

            # ── 卡A 运算对象 ──
            _vbox = self._card("运算对象")
            _rowI = QHBoxLayout()
            _rowI.setSpacing(0)
            _rowI.addWidget(_make_label("变量", font=FONT13, color=Colors.DIM))
            _rowI.addSpacing(4)
            _curv = action.get("var", "v1")
            _ivs = _known_vars_vset() or ["v1"]
            if _curv and _curv not in _ivs:
                _ivs.append(_curv)
            _NEW3 = "＋ 新建变量…"
            var_cb3 = _mini_combo(_ivs + [_NEW3], _curv, 110, h=25)

            def _var_pick3(t, a=action):
                if t == _NEW3:
                    name, ok = QInputDialog.getText(self, "新建变量",
                                                    "变量名（字母/数字/下划线）：",
                                                    text=next_var_name(task.actions,
                                                                       getattr(task, "vars", None)))
                    if ok and name.strip():
                        a["var"] = name.strip()
                    self._rebuild()
                    return
                a["var"] = t
                _refresh_actions()
            var_cb3.currentTextChanged.connect(_var_pick3)
            _rowI.addWidget(var_cb3)
            _rowI.addStretch(1)
            _vbox.addLayout(_rowI)
            _vbox.addWidget(_make_label("💡 变量来自上方「读数」动作；从未读过的变量按 0 计算",
                                       font=FONT13, color=Colors.DIM))

            # ── 卡B 怎么算 ──
            _vbox = self._card("怎么算")
            _rowJ = QHBoxLayout()
            _rowJ.setSpacing(0)
            _rowJ.addWidget(_make_label("运算", font=FONT13, color=Colors.DIM))
            _rowJ.addSpacing(4)
            _OP3 = [("+", "加"), ("−", "减"), ("×", "乘"), ("÷", "除"), ("=", "直接设为")]
            _cur3 = action.get("op", "+")
            if _cur3 == "*": _cur3 = "×"
            if _cur3 == "/": _cur3 = "÷"
            if _cur3 == "-": _cur3 = "−"
            op_cb3 = _mini_combo([s for s, _ in _OP3], _cur3, 54, h=25)
            op_cb3.setToolTip("、".join(f"{s}={n}" for s, n in _OP3))

            def _op_pick3(t, a=action):
                a["op"] = {"×": "*", "÷": "/", "−": "-"}.get(t, t)
                _refresh_actions()
            op_cb3.currentTextChanged.connect(_op_pick3)
            _rowJ.addWidget(op_cb3)
            _rowJ.addSpacing(14)
            _rowJ.addWidget(_make_label("值", font=FONT13, color=Colors.DIM))
            _rowJ.addSpacing(4)
            val3 = QDoubleSpinBox()
            val3.setRange(-1e9, 1e9)
            val3.setDecimals(2)
            val3.setValue(action.get("value", 0))
            val3.setAlignment(Qt.AlignRight)
            val3.setFont(FONT13)
            val3.valueChanged.connect(lambda v, a=action: (a.__setitem__("value", v), _refresh_actions()))
            spin_flat(val3)
            _fit_spin(val3, font=FONT13, extra=10)
            val3.textChanged.connect(lambda _t, sp=val3: _fit_spin(sp, font=FONT13, extra=10))
            _rowJ.addWidget(val3)
            _rowJ.addStretch(1)
            _vbox.addLayout(_rowJ)
            _vbox.addWidget(_make_label("💡 「=」是直接赋值（不参与运算）；「÷」遇到除以 0 会跳过这一步并保留原值",
                                       font=FONT13, color=Colors.DIM))

            # ── 卡C 例子 ──
            _vbox = self._card("例子")
            _ex3 = QVBoxLayout()
            _ex3.setSpacing(2)
            for _ln3 in ("读数把金币数写进 v1（比如 1200）",
                         "本动作选「−」值 200 → v1 变成 1000（扣掉买装备的钱）",
                         "想让后面的「条件分支」判断，v1 就得是这个算完的值"):
                _ex3.addWidget(_make_label(_ln3, font=FONT13, color=Colors.DIM))
            _vbox.addLayout(_ex3)

            # ── 卡D 后延 ──
            _vbox = self._card(None)
            _rowK = QHBoxLayout()
            _rowK.setSpacing(0)
            _rowK.addWidget(_make_label("后延", font=FONT13, color=Colors.DIM))
            _rowK.addSpacing(4)
            dly3 = QDoubleSpinBox()
            dly3.setRange(0, 600)
            dly3.setDecimals(1)
            dly3.setSingleStep(0.1)
            dly3.setValue(action.get("delay", 0))
            dly3.setAlignment(Qt.AlignRight)
            dly3.setFont(FONT13)
            dly3.setSuffix(" s")
            dly3.valueChanged.connect(lambda v, a=action: (a.__setitem__("delay", v), _refresh_actions()))
            spin_flat(dly3)
            _fit_spin(dly3, font=FONT13, extra=6)
            dly3.textChanged.connect(lambda _t, sp=dly3: _fit_spin(sp, font=FONT13, extra=6))
            _rowK.addWidget(dly3)
            _rowK.addStretch(1)
            _vbox.addLayout(_rowK)

        # 卡2 分支选项: 每选项 缩略图/阈值/尺度/跳到/重拍/排序 + 加分支 (搬入段共享 _vbox)
        if is_branch:
            _vbox = self._card("分支选项 (列表顺序=优先级)")
        if is_branch:
            # 分支选项: 每选项一行 ☰拖拽排序/缩略图/阈值/尺度/跳到/📷重拍/✕删 + 加分支尾行
            from core import vision as _v
            import os as _os
            options = action.get("options") or []
            if not options:
                _sub0 = QHBoxLayout()
                _sub0.setSpacing(3)
                _sub0.addSpacing(0)
                _sub0.addWidget(_make_label("还没有模板 — 点下方 + 加分支 开始框选", font=FONT13, color=Colors.DIM))
                _sub0.addStretch(1)
                _vbox.addLayout(_sub0)
            for k, option in enumerate(options):
                _roww = DraggableRow()
                _roww.setStyleSheet(card_qss(radius=8, sel="DraggableRow"))
                self._opt_rows.append(_roww)
                _rowL = QHBoxLayout(_roww)
                _rowL.setContentsMargins(6, 4, 6, 4)
                _rowL.setSpacing(0)  # 配对紧挨

                # ☰ 拖拽排序手柄(与主界面动作行同款QDrag)
                _h = QPushButton("☰")
                _h.setFixedSize(22, 18)
                _h.setCursor(QCursor(Qt.SizeVerCursor))
                _h.setStyleSheet(btn_qss("transparent", Colors.DIM, hover=Colors.ACCENT,
                                          hover_fg=Colors.TEXT, font=F12, radius=4))
                _h.setToolTip("拖动排序（列表顺序=优先级）")

                def _h_press(e, _i=k, _rw=_roww):
                    if e.button() == Qt.LeftButton:
                        from PySide6.QtGui import QDrag
                        from PySide6.QtCore import QMimeData
                        _rw.setDragging(True)
                        _mime = QMimeData()
                        _mime.setText(str(_i))
                        _drag = QDrag(_rw)
                        _drag.setMimeData(_mime)
                        _drag.exec_(Qt.MoveAction)
                        _rw.setDragging(False)
                _h.mousePressEvent = _h_press
                _rowL.addWidget(_h)

                def _opt_clear_hl():
                    for _r in self._opt_rows:
                        _r.setHighlight()

                def _opt_enter(e, _rw=_roww):
                    if e.mimeData().hasText():
                        e.acceptProposedAction()

                def _opt_move(e, _rw=_roww):
                    if e.mimeData().hasText():
                        e.acceptProposedAction()
                        _opt_clear_hl()
                        _y = e.position().y()
                        _hh = _rw.height()
                        _z = _hh * 0.5
                        if _y < _z:
                            _rw.setHighlight(top=True)
                        elif _y > _hh - _z:
                            _rw.setHighlight(bottom=True)
                        else:
                            _rw.setHighlight(top=True, bottom=True)

                def _opt_drop(e, _idx=k, _rw=_roww):
                    _opt_clear_hl()
                    if e.mimeData().hasText():
                        try:
                            _fr = int(e.mimeData().text())
                            _y = e.position().y()
                            _hh = _rw.height()
                            _z = _hh * 0.5
                            if _y < _z:
                                _to = _idx
                            elif _y > _hh - _z:
                                _to = _idx + 1
                            else:
                                _to = _idx
                            self._move_option(_fr, _to)
                        except Exception:
                            pass
                    e.acceptProposedAction()

                _roww.setAcceptDrops(True)
                _roww.dragEnterEvent = _opt_enter
                _roww.dragMoveEvent = _opt_move
                _roww.dragLeaveEvent = lambda e: _opt_clear_hl()
                _roww.dropEvent = _opt_drop

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
                _rowL.addWidget(_thumb)
                _rowL.addStretch(1)  # 图靠左, 阈值等设定整体右靠
                _rowL.addSpacing(2)

                _rowL.addWidget(_make_label("阈值", font=FONT13, color=Colors.DIM))
                _th = QDoubleSpinBox()
                _th.setRange(0, 1)
                _th.setDecimals(2)
                _th.setSingleStep(0.05)
                _th.setValue(float(option.get("threshold", 0.85)))
                _th.setFixedHeight(25)
                _fit_spin(_th, font=FONT13, extra=6)
                _th.setAlignment(Qt.AlignRight)
                _th.setFont(FONT13)
                spin_flat(_th)
                _th.valueChanged.connect(lambda v, o=option: o.__setitem__("threshold", round(v, 2)))
                _th.textChanged.connect(lambda _t, sp=_th: _fit_spin(sp, font=FONT13, extra=6))
                _rowL.addWidget(_th)
                _rowL.addSpacing(2)

                _sc = _make_btn("", font=FONT13, height=25)
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
                _rowL.addWidget(_sc)

                _rowL.addSpacing(14)  # 组界: 阈值组↔跳到组
                _rowL.addWidget(_make_label("跳到", font=FONT13, color=Colors.DIM))
                _rowL.addSpacing(4)
                _rowL.addWidget(_target_combo(task, option, big=True))
                _rowL.addSpacing(6)

                _cap = _make_btn("重拍", bg=Colors.BLUE, hover=Colors.ACCENT, font=FONT13, height=25)
                _cap.setFixedWidth(int(QFontMetricsF(FONT13).horizontalAdvance("重拍")) + 10)
                _cap.setToolTip("重拍本模板（覆盖原路径）")
                _cap.setToolTip("重拍本模板（覆盖原路径）")
                def _recap(_c=False, o=option):
                    capture_template(
                        app, task,
                        on_got=lambda rel, oo=o: oo.__setitem__("tpl", rel),
                        on_done=lambda: _refresh_actions(app, task),
                        rel=o.get("tpl"))
                _cap.clicked.connect(_recap)
                _rowL.addWidget(_cap)

                def _del_opt(_c=False, a=action, i=k):
                    (a.get("options") or []).pop(i)
                    _refresh_actions(app, task)

                _b = _make_btn("✕", bg=Colors.DIM, hover=Colors.ACCENT, font=FONT13, height=25)
                _b.setFixedWidth(24)
                _b.setToolTip("删除本选项")
                _b.clicked.connect(_del_opt)
                _rowL.addWidget(_b)
                _vbox.addWidget(_roww)

            _subf = QHBoxLayout()
            _subf.setSpacing(3)
            _subf.addSpacing(0)
            _addopt = _make_btn("+ 加分支", bg=Colors.BLUE, hover=Colors.ACCENT, font=FONT13, height=25)
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
            # 页面底=ACCENT(更深), 卡片=CARD(更浅): 形成层次, 且卡片内ACCENT底下拉与卡片有对比可见
            p.setBrush(QBrush(QColor(Colors.ACCENT)))
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


def find_open(app=None):
    """当前打开的悬浮编辑页; 没开返回 None。供透明度统一关口取用。"""
    from PySide6.QtWidgets import QApplication
    for w in QApplication.topLevelWidgets():
        if w.__class__.__name__ == "ActionSettingsView" and w.isVisible():
            return w
    return None