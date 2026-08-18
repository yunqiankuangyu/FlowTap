"""
键盘模式页面（支持键鼠混合动作）
直接 pack 布局：pf(顶) → handle → bf(底) → container(中间 expand)
"""
import ctypes
import threading
import time

import customtkinter as ctk
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Colors, FONT_B, FONT_M, load_presets, save_presets
from tasks.keyboard.keyboard_task import KeyboardTask, TaskStatus, make_key_action, make_click_action, fmt_action
from vk_map import VK_MAP, VK_NAME


def build_keyboard_mode(app):
    """构建键盘模式页面（直接 pack，无中间层）"""
    kf = app.keyboard_frame

    # ── 预设栏（顶部）──
    pf = ctk.CTkFrame(kf, fg_color=Colors.CARD, corner_radius=11)
    pf.pack(side="top", fill="x", padx=5, pady=(5, 3))
    presets = load_presets()
    preset_names = list(presets.keys()) if presets else ["无预设"]
    app._preset_var = ctk.StringVar(value=preset_names[0])
    app._preset_menu = ctk.CTkOptionMenu(pf, variable=app._preset_var, values=preset_names,
                                         font=FONT_M, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                                         button_color=Colors.DIM, width=120, height=25)
    app._preset_menu.pack(side="left", padx=(7, 4), pady=7)
    ctk.CTkButton(pf, text="加载", width=36, height=25, font=FONT_M,
                  fg_color=Colors.BLUE, text_color=Colors.TEXT,
                  hover_color=Colors.ACCENT, command=app._load_preset).pack(side="right", padx=2)
    ctk.CTkButton(pf, text="保存", width=36, height=25, font=FONT_M,
                  fg_color=Colors.GREEN, text_color=Colors.TEXT,
                  hover_color=Colors.ACCENT, command=app._save_preset_dialog).pack(side="right", padx=2)
    ctk.CTkButton(pf, text="删除", width=36, height=25, font=FONT_M,
                  fg_color=Colors.RED, text_color=Colors.TEXT,
                  hover_color=Colors.ACCENT, command=app._delete_preset).pack(side="right", padx=2)

    # ── 拖动条（place 固定底部，不参与 pack）──
    HANDLE_H = 12
    handle = ctk.CTkFrame(kf, fg_color="transparent", height=HANDLE_H, width=336, cursor="sb_v_double_arrow")
    handle.place(relx=0, rely=1, anchor="sw", relwidth=1)
    indicator = ctk.CTkFrame(handle, fg_color="#555", corner_radius=2, height=3, width=40)
    indicator.place(relx=0.5, rely=0.5, anchor="center")

    # ── 底部按钮栏（place 固定底部，不参与 pack）──
    bf = ctk.CTkFrame(kf, fg_color="transparent", height=66, width=336)
    bf.place(relx=0, rely=1, anchor="sw", relwidth=1, y=-(HANDLE_H + 11))
    bf.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkButton(bf, text="＋ 新建任务", font=FONT_B, fg_color=Colors.GREEN,
                  text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=43,
                  command=app._add_task).grid(row=0, column=0, sticky="ew", padx=(0, 3))
    app._all_btn = ctk.CTkButton(bf, text="▶ 全部开始", font=FONT_B, fg_color=Colors.GREEN,
                  text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=43,
                  command=app._toggle_all)
    app._all_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))

    # ── 拖动逻辑（Win32 API 全接管，绕过 Tk 事件循环）──
    import ctypes
    _user32 = ctypes.windll.user32
    _dpi_scale = _user32.GetDpiForSystem() / 96.0 if hasattr(_user32, 'GetDpiForSystem') else 1.0
    # 获取根窗口真实 HWND
    _root_hwnd = int(app.tk.call('winfo', 'id', '.'), 16)
    app._drag = {"active": False, "start_y": 0, "start_h": 0}
    def _on_handle_enter(e):
        indicator.configure(fg_color="#888")
    def _on_handle_leave(e):
        if not app._drag["active"]:
            indicator.configure(fg_color="#555")
    def _on_handle_press(e):
        app._manual_resize = True
        app._drag["active"] = True
        pt = ctypes.wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        app._drag["start_y"] = pt.y
        app._drag["start_h"] = app._tracked_height
        indicator.configure(fg_color="#4fc3f7")
    def _on_handle_release(e):
        app._drag["active"] = False
        indicator.configure(fg_color="#555")
    def _on_handle_drag(e):
        if not app._drag["active"]:
            return
        pt = ctypes.wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        dy = (pt.y - app._drag["start_y"]) / _dpi_scale
        new_h = int(app._drag["start_h"] + dy)
        new_h = max(189, min(600, new_h))
        if new_h == app._tracked_height:
            return
        app._tracked_height = new_h
        # SetWindowPos 直接改窗口大小，不走 Tk 事件循环，零延迟
        _user32.SetWindowPos(_root_hwnd, None, 0, 0, 346, new_h, 0x0002 | 0x0004)

    for w in (handle, indicator):
        w.bind("<Enter>", _on_handle_enter)
        w.bind("<Leave>", _on_handle_leave)
        w.bind("<ButtonPress-1>", _on_handle_press)
        w.bind("<ButtonRelease-1>", _on_handle_release)
        w.bind("<B1-Motion>", _on_handle_drag)

    # ── 任务滚动区（最后 pack，expand 填充剩余空间）──
    # 底部留白给 place 的 handle(12) + 间距(11) + bf(66) = 89px
    BOTTOM_RESERVE = HANDLE_H + 11 + 66  # 89
    container = ctk.CTkFrame(kf, fg_color="transparent")
    container.pack(fill="both", expand=True, pady=(0, BOTTOM_RESERVE))

    app.task_canvas = ctk.CTkCanvas(container, bg=Colors.ACCENT, highlightthickness=0)
    app.task_scroll = ctk.CTkFrame(app.task_canvas, fg_color="transparent")
    app.task_canvas_window = app.task_canvas.create_window(0, 0, window=app.task_scroll, anchor="nw")
    app.task_canvas.bind("<Configure>", lambda e: app.task_canvas.itemconfig(app.task_canvas_window, width=e.width))
    app.task_canvas.pack(side="left", fill="both", expand=True)

    def _on_mousewheel(event):
        app.task_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    app.task_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # 悬浮通知状态
    app._floating_panel = None
    app._floating_timer = None

    # 初始化跟踪高度
    app._tracked_height = 201  # 默认最小高度


def show_floating_notification(app, text, duration_ms=2000):
    """在窗口内显示一条悬浮通知（自动消失）"""
    hide_floating_notification(app)

    # 创建一个浮动标签，用 place 定位在窗口底部上方
    panel = ctk.CTkFrame(app.keyboard_frame, fg_color=Colors.CARD,
                         corner_radius=10, border_width=1, border_color=Colors.BLUE)
    lbl = ctk.CTkLabel(panel, text=text, font=FONT_M, text_color=Colors.TEXT,
                       fg_color="transparent", padx=12, pady=8)
    lbl.pack()
    panel.place(relx=0.5, rely=0.85, anchor="center")
    panel.lift()
    app._floating_panel = panel

    if duration_ms > 0:
        app._floating_timer = app.after(duration_ms, lambda: hide_floating_notification(app))


def hide_floating_notification(app):
    """隐藏悬浮通知"""
    if hasattr(app, '_floating_timer') and app._floating_timer:
        app.after_cancel(app._floating_timer)
        app._floating_timer = None
    if hasattr(app, '_floating_panel') and app._floating_panel:
        app._floating_panel.place_forget()
        app._floating_panel.destroy()
        app._floating_panel = None


def add_task(app):
    """添加新任务"""
    task = KeyboardTask(app.next_task_id, f"任务{app.next_task_id}")
    app.next_task_id += 1
    app.keyboard_tasks.append(task)
    create_card(app, task)


def create_card(app, task):
    """创建任务卡片"""
    card = ctk.CTkFrame(app.task_scroll, fg_color=Colors.CARD, corner_radius=11)
    card.pack(fill="x", pady=5)

    # ── 头部：名称 + 状态 ──
    hdr = ctk.CTkFrame(card, fg_color="transparent")
    hdr.pack(fill="x", padx=11, pady=(11, 5))
    name_e = ctk.CTkEntry(hdr, font=FONT_B, fg_color=Colors.ACCENT,
                          text_color=Colors.TEXT, border_width=0, width=79, height=25)
    name_e.insert(0, task.name)
    name_e.pack(side="left")
    name_e.bind("<FocusOut>", lambda e: setattr(task, 'name', name_e.get()))
    task._name_entry = name_e

    # ── 动作列表区域（无动作时不显示）──
    action_frame = ctk.CTkFrame(card, fg_color="transparent")
    task._action_frame = action_frame
    task._action_rows = []
    _refresh_actions(app, task)

    # ── 添加按钮行 ──
    af = ctk.CTkFrame(card, fg_color="transparent")
    af.pack(fill="x", padx=11, pady=3)
    af.grid_columnconfigure((0, 1, 2), weight=1)
    ctk.CTkButton(af, text="⌨ 添加键位", font=FONT_B, fg_color=Colors.BLUE,
                  text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                  command=lambda: add_key_action(app, task)).grid(row=0, column=0, sticky="ew", padx=(0, 3))
    ctk.CTkButton(af, text="🖱 添加点击", font=FONT_B, fg_color=Colors.BLUE,
                  text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                  command=lambda: add_click_action(app, task)).grid(row=0, column=1, sticky="ew", padx=(0, 3))
    ctk.CTkButton(af, text="清空", font=FONT_B, fg_color=Colors.DIM,
                  text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                  command=lambda: clear_actions(app, task)).grid(row=0, column=2, sticky="ew")

    # ── 循环间隔 + 关系 ──
    sf = ctk.CTkFrame(card, fg_color="transparent")
    sf.pack(fill="x", padx=11, pady=5)
    sf.grid_columnconfigure((0, 1), weight=1)

    # 左：循环间隔
    lf = ctk.CTkFrame(sf, fg_color="transparent")
    lf.grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(lf, text="循环:", font=FONT_M, text_color=Colors.TEXT2).pack(side="left")
    lv_var = ctk.DoubleVar(value=task.loop_interval)
    spin = make_spinbox(app, lf, lv_var, 0, 999, 5, task, 'loop_interval')
    spin.pack(side="left", padx=6)
    task._loop_var = lv_var
    task._loop_frame = spin

    # 右：关系
    rf = ctk.CTkFrame(sf, fg_color="transparent")
    rf.grid(row=0, column=1, sticky="e")
    ctk.CTkLabel(rf, text="关系:", font=FONT_M, text_color=Colors.TEXT2).pack(side="left")
    rel_var = ctk.StringVar(value=task.relation_type)
    ctk.CTkOptionMenu(rf, variable=rel_var, values=["独立", "在任务x后"],
                      font=FONT_M, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                      button_color=Colors.DIM, width=72, height=25,
                      command=lambda v: on_rel_change(app, v, task, rf, rel_var)).pack(side="left", padx=6)

    dep_frame = ctk.CTkFrame(rf, fg_color="transparent")
    dep_var = ctk.StringVar(value="无")
    dep_menu_widget = [None]

    def update_dep_menu():
        opts = ["无"] + [f"任务{t.task_id}" for t in app.keyboard_tasks if t.task_id != task.task_id]
        if dep_var.get() not in opts:
            dep_var.set("无")
        if dep_menu_widget[0]:
            dep_menu_widget[0].destroy()
        dep_menu_widget[0] = ctk.CTkOptionMenu(dep_frame, variable=dep_var, values=opts,
                                               font=FONT_M, fg_color=Colors.ACCENT, text_color=Colors.TEXT,
                                               button_color=Colors.DIM, width=58, height=25)
        dep_menu_widget[0].pack(side="left")

    app._rel_frames = getattr(app, '_rel_frames', {})
    app._rel_frames[task.task_id] = (rel_var, dep_frame, dep_var, update_dep_menu)

    # ── 底部：状态 + 开始/停止 + 删除 ──
    btm = ctk.CTkFrame(card, fg_color="transparent")
    btm.pack(fill="x", padx=11, pady=(5, 11))
    st_lbl = ctk.CTkLabel(btm, text=task.status.value, font=FONT_M, text_color=Colors.DIM)
    st_lbl.pack(side="left")
    go_btn = ctk.CTkButton(btm, text="▶ 开始", font=FONT_B, fg_color=Colors.GREEN,
                           text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, width=79, height=27,
                           command=lambda: toggle_task(app, task, go_btn, st_lbl))
    go_btn.pack(side="right")
    task._go_btn = go_btn
    task._st_lbl = st_lbl
    del_btn = ctk.CTkButton(btm, text="✕", width=22, height=22, fg_color="transparent",
                            text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B,
                            command=lambda: del_task(app, task, card))
    del_btn.pack(side="right", padx=(0, 5))
    check_start_btn(task)
    app.after(150, app._auto_size)


def _refresh_actions(app, task):
    """刷新动作列表UI"""
    # 清除旧行
    for row_info in task._action_rows:
        row_info["frame"].destroy()
    task._action_rows.clear()

    # 有动作时才 pack action_frame
    if task.actions and not task._action_frame.winfo_ismapped():
        task._action_frame.pack(fill="x", padx=11, pady=5)
    elif not task.actions and task._action_frame.winfo_ismapped():
        task._action_frame.pack_forget()

    # 逐个创建新行
    for idx, action in enumerate(task.actions):
        row = ctk.CTkFrame(task._action_frame, fg_color=Colors.ACCENT, corner_radius=8)
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(1, weight=1)

        # 序号
        num_lbl = ctk.CTkLabel(row, text=f"{idx+1}.", font=FONT_M, text_color=Colors.DIM, width=22)
        num_lbl.grid(row=0, column=0, padx=(6, 2))

        # 动作描述
        desc = fmt_action(action)
        desc_lbl = ctk.CTkLabel(row, text=desc, font=FONT_B, text_color=Colors.TEXT, anchor="w")
        desc_lbl.grid(row=0, column=1, sticky="w", padx=4)

        # delay spinbox
        delay_var = ctk.DoubleVar(value=action.get("delay", 0.5))
        delay_spin = _make_mini_spinbox(row, delay_var, 0, 30.0, 0.1,
                                        lambda v, a=action: a.__setitem__("delay", round(v, 2)))
        delay_spin.grid(row=0, column=2, padx=4)

        # 删除按钮
        del_btn = ctk.CTkButton(row, text="✕", width=18, height=18, fg_color="transparent",
                                text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B,
                                command=lambda i=idx: _delete_action(app, task, i))
        del_btn.grid(row=0, column=3, padx=(2, 6))

        task._action_rows.append({"frame": row, "action": action, "desc_lbl": desc_lbl})


def _delete_action(app, task, idx):
    """删除指定动作"""
    if 0 <= idx < len(task.actions):
        task.actions.pop(idx)
        _refresh_actions(app, task)


def _make_mini_spinbox(parent, var, lo, hi, step, on_change):
    """创建迷你spinbox用于delay编辑"""
    def _set(v):
        v = round(max(lo, min(hi, v)), 2)
        var.set(v)
        entry.delete(0, "end")
        entry.insert(0, str(v))
        if on_change: on_change(v)

    c = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkButton(c, text="◀", width=14, height=18, font=FONT_M, fg_color="transparent",
                  text_color=Colors.TEXT, hover_color=Colors.BLUE,
                  command=lambda: _set(var.get() - step)).pack(side="left")
    entry = ctk.CTkEntry(c, font=FONT_M, fg_color="transparent", text_color=Colors.TEXT,
                         border_width=0, width=36, height=18, justify="center")
    entry.insert(0, str(var.get()))
    entry.pack(side="left")
    ctk.CTkButton(c, text="▶", width=14, height=18, font=FONT_M, fg_color="transparent",
                  text_color=Colors.TEXT, hover_color=Colors.BLUE,
                  command=lambda: _set(var.get() + step)).pack(side="left")
    ctk.CTkLabel(c, text="s", font=FONT_M, text_color=Colors.DIM, width=10).pack(side="left")

    def on_enter(e):
        try: _set(float(entry.get()))
        except: entry.delete(0, "end"); entry.insert(0, str(var.get()))
    entry.bind("<Return>", on_enter)
    entry.bind("<FocusOut>", on_enter)
    return c


def add_key_action(app, task):
    """捕获按键并添加到动作列表"""
    if getattr(task, '_capturing', False):
        task._capturing = False
        time.sleep(0.05)
    task._capturing = True

    # 更新底部按钮状态
    if task._action_rows:
        last_desc = task._action_rows[-1].get("desc_lbl")
        if last_desc:
            last_desc.configure(text="⏳ 按下任意键...", text_color=Colors.YELLOW)

    app.focus_set()
    def listen():
        u32 = ctypes.windll.user32
        for vk in range(0x08, 0x100):
            u32.GetAsyncKeyState(vk)
        time.sleep(0.15)
        while task._capturing:
            for vk in range(0x08, 0x100):
                if not task._capturing:
                    return
                if u32.GetAsyncKeyState(vk) & 0x0001:
                    task.actions.append(make_key_action(vk))
                    app.after(0, lambda: _refresh_actions(app, task))
                    task._capturing = False
                    return
            time.sleep(0.01)
    threading.Thread(target=listen, daemon=True).start()


def add_click_action(app, task):
    """录制鼠标位置并添加到动作列表"""
    if getattr(task, '_recording_click', False):
        return
    task._recording_click = True

    app.withdraw()
    overlay = ctk.CTkToplevel(app)
    overlay.overrideredirect(True)
    overlay.geometry(f"{app.winfo_screenwidth()}x{app.winfo_screenheight()}+0+0")
    overlay.configure(fg_color="#808080")
    overlay.attributes("-alpha", 0.4)
    overlay.attributes("-topmost", True)
    tip = ctk.CTkLabel(overlay, text="🎯 点击鼠标左键确认位置", font=("MiSans", 16, "bold"),
                       text_color="#ffffff", fg_color="#333333", corner_radius=8)
    tip.place(relx=0.5, rely=0.5, anchor="center")

    def wait_click():
        import ctypes.wintypes
        u32 = ctypes.windll.user32
        time.sleep(0.3)
        # 等鼠标松开
        while u32.GetAsyncKeyState(0x01) & 0x8000:
            time.sleep(0.01)
        # 等鼠标按下
        while not (u32.GetAsyncKeyState(0x01) & 0x8000):
            time.sleep(0.01)
        p = ctypes.wintypes.POINT()
        u32.GetCursorPos(ctypes.byref(p))
        task.actions.append(make_click_action(p.x, p.y))
        task._recording_click = False
        app.after(0, overlay.destroy)
        app.after(0, lambda: _refresh_actions(app, task))
        app.after(0, app.deiconify)

    threading.Thread(target=wait_click, daemon=True).start()


def clear_actions(app, task):
    """清空所有动作"""
    task.actions.clear()
    _refresh_actions(app, task)


def on_rel_change(app, value, task, parent_frame, rel_var):
    """任务关系切换时更新UI"""
    task.relation_type = rel_var.get()
    frame_info = app._rel_frames.get(task.task_id)
    if frame_info:
        dep_frame, dep_var, update_fn = frame_info[1], frame_info[2], frame_info[3]
        if value == "在任务x后":
            update_fn()
            dep_frame.pack(side="left", padx=(6, 0))
            task.loop_interval = 10
            spin_step(task, 0)
            if hasattr(task, '_loop_frame'):
                for child in task._loop_frame.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        txt = child.cget("text")
                        cmd = (lambda: spin_step(task, -1)) if txt == "◀" else \
                              (lambda: spin_step(task, 1)) if txt == "▶" else None
                        if cmd: child.configure(command=cmd)
            dep_str = dep_var.get()
            if dep_str.startswith("任务"):
                try: task.dependency_task_id = int(dep_str[2:])
                except: task.dependency_task_id = None
        else:
            dep_frame.pack_forget()
            task.dependency_task_id = None
            if hasattr(task, '_loop_frame'):
                for child in task._loop_frame.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        txt = child.cget("text")
                        cmd = (lambda: spin_step(task, -5)) if txt == "◀" else \
                              (lambda: spin_step(task, 5)) if txt == "▶" else None
                        if cmd: child.configure(command=cmd)


def toggle_task(app, task, btn, lbl):
    """启动/停止任务"""
    if task._running or getattr(task, '_countdown_active', False):
        task._countdown_active = False
        task.stop()
        btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
        lbl.configure(text=f"已完成 {task.done_count} 次", text_color=Colors.DIM)
        app._update_all_btn()
    else:
        if task.relation_type == "在任务x后":
            frame_info = app._rel_frames.get(task.task_id)
            if frame_info:
                dep_str = frame_info[2].get()
                if dep_str.startswith("任务"):
                    try: task.dependency_task_id = int(dep_str[2:])
                    except: task.dependency_task_id = None
                else:
                    task.dependency_task_id = None
        update_dependencies(app)
        trigger = task.relation_type == "在任务x后"
        if trigger:
            task._callback = lambda: app.after(0, lambda: lbl.configure(
                text=f"已完成 {task.done_count} 次", text_color=Colors.GREEN))
            task._countdown_callback = lambda t, c: app.after(0, lambda t=t, c=c: lbl.configure(text=t, text_color=c))
            task.start()
            btn.configure(text="■ 停止", fg_color=Colors.RED)
            lbl.configure(text="● 等待前置任务", text_color=Colors.YELLOW)
            app._update_all_btn()
        else:
            btn.configure(text="■ 停止", fg_color=Colors.RED)
            task._countdown_active = True
            def do_countdown():
                for i in range(3, 0, -1):
                    if not task._countdown_active: return
                    app.after(0, lambda t=i: lbl.configure(
                        text=f"● 准备中 {t}...", text_color=Colors.YELLOW))
                    time.sleep(1)
                if not task._countdown_active: return
                task._countdown_active = False
                task._countdown_callback = lambda t, c: app.after(0, lambda t=t, c=c: lbl.configure(text=t, text_color=c))
                task.start(callback=lambda: app.after(0, lambda: lbl.configure(
                    text=f"已完成 {task.done_count} 次", text_color=Colors.GREEN)),
                    countdown_callback=task._countdown_callback)
                app.after(0, lambda: lbl.configure(
                    text=task.status.value, text_color=Colors.GREEN))
                app.after(0, app._update_all_btn)
            threading.Thread(target=do_countdown, daemon=True).start()


def update_dependencies(app):
    """更新任务依赖关系"""
    for t in app.keyboard_tasks:
        t._dependents.clear()
    for t in app.keyboard_tasks:
        if t.relation_type == "在任务x后" and t.dependency_task_id is not None:
            frame_info = app._rel_frames.get(t.task_id)
            if frame_info:
                dep_var = frame_info[2]
                dep_str = dep_var.get()
                if dep_str.startswith("任务"):
                    try:
                        dep_id = int(dep_str[2:])
                        t.dependency_task_id = dep_id
                        for parent in app.keyboard_tasks:
                            if parent.task_id == dep_id:
                                parent._dependents.append(t)
                                break
                    except:
                        t.dependency_task_id = None


def update_all_btn(app):
    """根据任务状态更新全部按钮"""
    if not hasattr(app, '_all_btn') or not app._all_btn:
        return
    running_count = sum(1 for t in app.keyboard_tasks if t._running)
    if running_count > 0:
        app._all_btn.configure(text="■ 全部停止", fg_color=Colors.RED,
                               hover_color=Colors.HOVER_RED)
    else:
        app._all_btn.configure(text="▶ 全部开始", fg_color=Colors.GREEN,
                               hover_color=Colors.HOVER_GREEN)


def del_task(app, task, card):
    """删除任务"""
    task.stop()
    app.keyboard_tasks.remove(task)
    card.destroy()
    app.after(150, app._auto_size)
    app._update_all_btn()


def make_spinbox(app, parent, var, lo, hi, step, task, attr, integer=False, on_change=None):
    """创建自定义spinbox控件"""
    def _set(v):
        v = round(v, 0) if integer else round(v, 2)
        v = max(lo, min(hi, v))
        var.set(v)
        setattr(task, attr, v)
        entry.delete(0, "end")
        entry.insert(0, str(v))
        if on_change: on_change(v)
    c = ctk.CTkFrame(parent, fg_color=Colors.ACCENT, corner_radius=8)
    c.pack(side="left")
    ctk.CTkButton(c, text="◀", width=17, height=25, font=FONT_M, fg_color="transparent",
                  text_color=Colors.TEXT, hover_color=Colors.BLUE, command=lambda: _set(var.get() - step)).pack(side="left")
    entry = ctk.CTkEntry(c, font=FONT_B, fg_color="transparent", text_color=Colors.TEXT,
                         border_width=0, width=47, height=25, justify="center")
    entry.insert(0, str(var.get()))
    entry.pack(side="left")
    ctk.CTkButton(c, text="▶", width=17, height=25, font=FONT_M, fg_color="transparent",
                  text_color=Colors.TEXT, hover_color=Colors.BLUE, command=lambda: _set(var.get() + step)).pack(side="left")
    def on_enter(e):
        try: _set(float(entry.get()))
        except: entry.delete(0, "end"); entry.insert(0, str(var.get()))
    entry.bind("<Return>", on_enter)
    entry.bind("<FocusOut>", on_enter)
    return c


def check_start_btn(task):
    """动作列表为空时禁用开始按钮"""
    if hasattr(task, '_go_btn'):
        if not task.actions:
            task._go_btn.configure(state="disabled", fg_color=Colors.DIM)
        else:
            task._go_btn.configure(state="normal", fg_color=Colors.GREEN)


def spin_step(task, step):
    """步进调整循环间隔值"""
    v = max(0, min(999, task.loop_interval + step))
    task.loop_interval = v
    if hasattr(task, '_loop_var'):
        task._loop_var.set(v)
    if hasattr(task, '_loop_frame'):
        for child in task._loop_frame.winfo_children():
            if isinstance(child, ctk.CTkEntry):
                child.delete(0, "end")
                child.insert(0, str(v))


def save_preset_dialog(app):
    """保存当前任务为预设"""
    dialog = ctk.CTkToplevel(app)
    dialog.overrideredirect(True)
    dialog.attributes("-topmost", True)
    dialog.configure(fg_color=Colors.ACCENT)
    dialog.geometry(f"260x140+{app.winfo_x()+40}+{app.winfo_y()+100}")
    dialog.attributes("-alpha", app._settings.get("opacity", 1.0))
    ctk.CTkLabel(dialog, text="💾 保存预设", font=FONT_B, text_color=Colors.TEXT).pack(pady=(11, 5))
    entry = ctk.CTkEntry(dialog, font=FONT_M, fg_color=Colors.CARD, text_color=Colors.TEXT,
                         border_width=0, width=200, height=30, placeholder_text="输入预设名称")
    entry.pack(padx=11, pady=5)
    entry.focus_set()
    presets = load_presets()
    entry.insert(0, f"预设{len(presets)+1}")
    bf = ctk.CTkFrame(dialog, fg_color="transparent")
    bf.pack(fill="x", padx=11, pady=(5, 11))

    def do_save():
        name = entry.get().strip()
        if not name: return
        tasks_data = []
        for t in app.keyboard_tasks:
            tasks_data.append({
                "name": t.name,
                "actions": [dict(a) for a in t.actions],  # 深拷贝
                "loop_interval": t.loop_interval,
                "relation_type": t.relation_type,
            })
        presets[name] = tasks_data
        save_presets(presets)
        refresh_preset_menu(app)
        dialog.destroy()

    ctk.CTkButton(bf, text="保存", font=FONT_B, fg_color=Colors.GREEN,
                  text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=30,
                  command=do_save).pack(side="left", expand=True, fill="x", padx=(0, 3))
    ctk.CTkButton(bf, text="取消", font=FONT_B, fg_color=Colors.DIM,
                  text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=30,
                  command=dialog.destroy).pack(side="right", expand=True, fill="x", padx=(3, 0))
    entry.bind("<Return>", lambda e: do_save())


def load_preset(app):
    """加载选中的预设"""
    name = app._preset_var.get()
    if name == "无预设": return
    presets = load_presets()
    if name not in presets: return
    tasks_data = presets[name]
    for td in tasks_data:
        # 兼容旧格式：旧版存的是 key_sequence (List[int])
        if "actions" in td:
            actions = td["actions"]
        elif "key_sequence" in td:
            actions = [{"type": "key", "vk": vk, "delay": 0.5} for vk in td["key_sequence"]]
        else:
            actions = []
        task = KeyboardTask(
            app.next_task_id, td["name"], actions,
            td.get("loop_interval", 80.0),
            relation_type=td.get("relation_type", "独立"),
        )
        app.next_task_id += 1
        app.keyboard_tasks.append(task)
        create_card(app, task)
    app.after(150, app._auto_size)


def delete_preset_cmd(app):
    """删除选中的预设"""
    name = app._preset_var.get()
    if name == "无预设": return
    presets = load_presets()
    if name in presets:
        del presets[name]
        save_presets(presets)
        refresh_preset_menu(app)


def refresh_preset_menu(app):
    """刷新预设下拉菜单"""
    presets = load_presets()
    preset_names = list(presets.keys()) if presets else ["无预设"]
    app._preset_menu.configure(values=preset_names)
    app._preset_var.set(preset_names[0])


def stop_all(app):
    """停止所有键盘任务"""
    for t in app.keyboard_tasks:
        t.stop()
        if hasattr(t, '_go_btn'):
            t._go_btn.configure(text="▶ 开始", fg_color=Colors.GREEN)
        if hasattr(t, '_st_lbl'):
            t._st_lbl.configure(text=f"已完成 {t.done_count} 次", text_color=Colors.DIM)
    app._update_all_btn()


def start_all(app):
    """启动所有可启动的独立任务"""
    update_dependencies(app)
    for t in app.keyboard_tasks:
        if not t._running and t.relation_type == "独立" and t.actions:
            t._callback = lambda: None
            t._countdown_callback = lambda txt, clr: None

            def do_start(task=t):
                time.sleep(3)
                if task._running:
                    task.start(
                        callback=lambda: None,
                        countdown_callback=lambda txt, clr: None
                    )

            t._go_btn.configure(text="■ 停止", fg_color=Colors.RED)


def toggle_all(app):
    """切换全部开始/停止"""
    any_running = any(t._running for t in app.keyboard_tasks)
    if any_running:
        stop_all(app)
    else:
        start_all(app)


def auto_size(app):
    """自动调整窗口高度（基于控件规格计算）
    拖动中 / 手动拖过后，auto_size 不再覆盖
    """
    if not hasattr(app, 'keyboard_frame'): return
    if app._current_mode != "keyboard": return
    if getattr(app, '_manual_resize', False): return
    if getattr(app, '_drag', {}).get('active', False): return
    count = len(app.keyboard_tasks)
    # ┌─────────────────────────────────────────────┐
    # │ 标题栏              40px                     │
    # │ kf padding-top       5px                     │
    # │ 预设栏 (pf)         60px  pady=(5,3)         │
    # │ pf padding-bottom    3px                     │
    # │ ── 任务区 (expand) ──                        │
    # │ 卡片×N             135px/个 (无动作时更矮)    │
    # │   有动作时           +34px (action_frame)     │
    # │ card间距×N          10px/个 (pady=5×2)       │
    # │ ── 底部 ──                                   │
    # │ bf padding-top      11px                     │
    # │ 底部按钮栏 (bf)     65px  height=66          │
    # │ 拖动条 (handle)     12px                     │
    # │ kf padding-bottom    5px                     │
    # └─────────────────────────────────────────────┘
    CARD_BASE = 135       # 卡片基础高度（无动作，action_frame 隐藏）
    ACTION_FRAME = 34     # 有动作时多出的高度（pady=5 + row=29）
    CARD_GAP = 10         # 卡片间距
    FIXED = 40 + 5 + 60 + 3 + 11 + 65 + 12 + 5  # = 201

    if count == 0:
        h = FIXED
    else:
        content = 0
        for t in app.keyboard_tasks:
            content += CARD_BASE + CARD_GAP
            if t.actions:
                content += ACTION_FRAME
        h = FIXED + content
    h = min(h, 600)
    app._tracked_height = h
    app.geometry(f"346x{h}")
