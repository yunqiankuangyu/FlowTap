"""
键盘模式页面
"""
import ctypes
import threading
import time

import customtkinter as ctk
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Colors, FONT_B, FONT_M, load_presets, save_presets
from tasks import KeyboardTask, TaskStatus
from vk_map import VK_MAP, VK_NAME

def build_keyboard_mode(app):
    """构建键盘模式页面
    
    Args:
        app: App主窗口实例
    """
    # ── 预设管理栏 ──
    pf = ctk.CTkFrame(app.keyboard_frame, fg_color=Colors.CARD, corner_radius=11)
    pf.pack(fill="x", padx=5, pady=(5, 3))
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

    container = ctk.CTkFrame(app.keyboard_frame, fg_color="transparent")
    container.pack(fill="both", expand=True)

    app.task_canvas = ctk.CTkCanvas(container, bg=Colors.ACCENT, highlightthickness=0)
    app.task_scroll = ctk.CTkFrame(app.task_canvas, fg_color="transparent")
    app.task_canvas_window = app.task_canvas.create_window(0, 0, window=app.task_scroll, anchor="nw")
    app.task_canvas.bind("<Configure>", lambda e: app.task_canvas.itemconfig(app.task_canvas_window, width=e.width))
    app.task_canvas.pack(side="left", fill="both", expand=True)

    def _on_mousewheel(event):
        app.task_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    app.task_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    bf = ctk.CTkFrame(app.keyboard_frame, fg_color="transparent", height=66)
    bf.pack(fill="x", pady=(11, 0))
    bf.pack_propagate(False)
    bf.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkButton(bf, text="＋ 新建任务", font=FONT_B, fg_color=Colors.GREEN,
                  text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=43,
                  command=app._add_task).grid(row=0, column=0, sticky="ew", padx=(0, 3))
    app._all_btn = ctk.CTkButton(bf, text="▶ 全部开始", font=FONT_B, fg_color=Colors.GREEN,
                  text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, height=43,
                  command=app._toggle_all)
    app._all_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))


def add_task(app):
    """添加新任务"""
    keys = [0x52, 0x20] if app.next_task_id == 1 else []
    task = KeyboardTask(app.next_task_id, f"任务{app.next_task_id}", keys)
    app.next_task_id += 1
    app.keyboard_tasks.append(task)
    create_card(app, task)


def create_card(app, task):
    """创建任务卡片"""
    card = ctk.CTkFrame(app.task_scroll, fg_color=Colors.CARD, corner_radius=11)
    card.pack(fill="x", pady=5)

    hdr = ctk.CTkFrame(card, fg_color="transparent")
    hdr.pack(fill="x", padx=11, pady=(11, 5))
    name_e = ctk.CTkEntry(hdr, font=FONT_B, fg_color=Colors.ACCENT,
                          text_color=Colors.TEXT, border_width=0, width=79, height=25)
    name_e.insert(0, task.name)
    name_e.pack(side="left")
    name_e.bind("<FocusOut>", lambda e: setattr(task, 'name', name_e.get()))
    keys_lbl = ctk.CTkLabel(hdr, text=f"键位: {fmt_keys(task.key_sequence)}",
                            font=FONT_B, text_color=Colors.BLUE, anchor="w")
    keys_lbl.pack(side="left", padx=(9, 0))

    kf = ctk.CTkFrame(card, fg_color="transparent")
    kf.pack(fill="x", padx=11, pady=7)
    kf.grid_columnconfigure((0, 1, 2), weight=1)
    ctk.CTkButton(kf, text="添加键", font=FONT_B, fg_color=Colors.BLUE,
                  text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                  command=lambda: capture_key(app, task, keys_lbl)).grid(row=0, column=0, sticky="ew", padx=(0, 4))
    ctk.CTkButton(kf, text="删除末位", font=FONT_B, fg_color=Colors.DIM,
                  text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                  command=lambda: rm_key(task, keys_lbl)).grid(row=0, column=1, sticky="ew", padx=(0, 4))
    ctk.CTkButton(kf, text="清空", font=FONT_B, fg_color=Colors.DIM,
                  text_color=Colors.TEXT, hover_color=Colors.ACCENT, height=25,
                  command=lambda: clr_keys(task, keys_lbl)).grid(row=0, column=2, sticky="ew")

    sf = ctk.CTkFrame(card, fg_color="transparent")
    sf.pack(fill="x", padx=11, pady=5)

    ctk.CTkLabel(sf, text="间隔:", font=FONT_M, text_color=Colors.TEXT2).pack(side="left")
    iv_var = ctk.DoubleVar(value=task.key_interval)
    spin1 = make_spinbox(app, sf, iv_var, 0, 30.0, 0.5, task, 'key_interval',
                         on_change=lambda v: check_interval_btn(task))
    spin1.pack(side="left", padx=(5, 18))

    task._loop_label = ctk.CTkLabel(sf, text="循环:", font=FONT_M, text_color=Colors.TEXT2)
    task._loop_label.pack(side="left")
    lv_var = ctk.DoubleVar(value=task.loop_interval)
    spin2 = make_spinbox(app, sf, lv_var, 0, 999, 5, task, 'loop_interval')
    spin2.pack(side="left", padx=6)
    task._loop_var = lv_var
    task._loop_frame = spin2

    rf = ctk.CTkFrame(card, fg_color="transparent")
    rf.pack(fill="x", padx=11, pady=(0, 5))
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

    bf = ctk.CTkFrame(card, fg_color="transparent")
    bf.pack(fill="x", padx=11, pady=(5, 11))
    st_lbl = ctk.CTkLabel(bf, text=task.status.value, font=FONT_M, text_color=Colors.DIM)
    st_lbl.pack(side="left")
    go_btn = ctk.CTkButton(bf, text="▶ 开始", font=FONT_B, fg_color=Colors.GREEN,
                           text_color=Colors.TEXT, hover_color=Colors.HOVER_GREEN, width=79, height=27,
                           command=lambda: toggle_task(app, task, go_btn, st_lbl))
    go_btn.pack(side="right")
    task._go_btn = go_btn
    task._st_lbl = st_lbl
    del_btn = ctk.CTkButton(bf, text="✕", width=22, height=22, fg_color="transparent",
                            text_color=Colors.DIM, hover_color=Colors.RED, font=FONT_B,
                            command=lambda: del_task(app, task, card))
    del_btn.pack(side="right", padx=(0, 5))
    check_interval_btn(task)
    app.after(150, app._auto_size)


def on_rel_change(app, value, task, parent_frame, rel_var):
    """任务关系切换时更新UI"""
    task.relation_type = rel_var.get()
    if hasattr(task, '_loop_label'):
        task._loop_label.configure(text="延时:" if value == "在任务x后" else "循环:")
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
                        cmd = (lambda: spin_step(task, -1)) if txt == "◀" else                               (lambda: spin_step(task, 1)) if txt == "▶" else None
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
                        cmd = (lambda: spin_step(task, -5)) if txt == "◀" else                               (lambda: spin_step(task, 5)) if txt == "▶" else None
                        if cmd: child.configure(command=cmd)


def toggle_task(app, task, btn, lbl):
    """启动/停止任务"""
    import time
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


def check_interval_btn(task):
    """间隔为0时禁用开始按钮"""
    if hasattr(task, '_go_btn'):
        if task.key_interval <= 0:
            task._go_btn.configure(state="disabled", fg_color=Colors.DIM)
        else:
            task._go_btn.configure(state="normal", fg_color=Colors.GREEN)


def spin_step(task, step):
    """步进调整延时/循环值并更新entry显示"""
    v = max(0, min(999, task.loop_interval + step))
    task.loop_interval = v
    if hasattr(task, '_loop_var'):
        task._loop_var.set(v)
    if hasattr(task, '_loop_frame'):
        for child in task._loop_frame.winfo_children():
            if isinstance(child, ctk.CTkEntry):
                child.delete(0, "end")
                child.insert(0, str(v))


def capture_key(app, task, lbl):
    """捕获按键"""
    if getattr(task, '_capturing', False):
        task._capturing = False
        time.sleep(0.05)
    task._capturing = True
    lbl.configure(text="按下任意键...", text_color=Colors.YELLOW)
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
                    task.key_sequence.append(vk)
                    app.after(0, lambda: lbl.configure(
                        text=f"键位: {fmt_keys(task.key_sequence)}"))
                    task._capturing = False
                    return
            time.sleep(0.01)
    threading.Thread(target=listen, daemon=True).start()


def rm_key(task, lbl):
    """删除末位键"""
    if task.key_sequence:
        task.key_sequence.pop()
        lbl.configure(text=f"键位: {fmt_keys(task.key_sequence)}")


def clr_keys(task, lbl):
    """清空键位"""
    task.key_sequence.clear()
    lbl.configure(text="键位: (空)")


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
                "name": t.name, "key_sequence": list(t.key_sequence),
                "key_interval": t.key_interval, "loop_interval": t.loop_interval,
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
        task = KeyboardTask(app.next_task_id, td["name"], list(td["key_sequence"]),
                            td["key_interval"], td["loop_interval"],
                            relation_type=td.get("relation_type", "独立"))
        app.next_task_id += 1
        app.keyboard_tasks.append(task)
        create_card(app, task)
    app.after(150, app._auto_size)


def delete_preset_by_name(app):
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


def fmt_keys(keys):
    """格式化键位显示"""
    from vk_map import VK_NAME
    if not keys: return "(空)"
    return " → ".join(VK_NAME.get(vk, f"[{vk}]") for vk in keys)


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
    import time
    update_dependencies(app)
    for t in app.keyboard_tasks:
        if not t._running and t.relation_type == "独立" and t.key_interval > 0:
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
            t._st_lbl.configure(text="● 准备中...", text_color=Colors.YELLOW)
            t._running = True
            threading.Thread(target=do_start, daemon=True).start()
    app._update_all_btn()


def toggle_all(app):
    """全部开始/全部停止切换"""
    running_count = sum(1 for t in app.keyboard_tasks if t._running)
    if running_count > 0:
        stop_all(app)
    else:
        start_all(app)


def auto_size(app):
    """根据内容自动调整窗口高度"""
    app.update_idletasks()
    for frame in [app.mouse_frame, app.keyboard_frame]:
        if frame.winfo_ismapped():
            # 只计算有固定高度的子控件（pf预设栏 + bf按钮栏），container会自动expand
            h = 0
            for child in frame.winfo_children():
                req_h = child.winfo_reqheight()
                pack = child.pack_info()
                mg = pack.get("pady", 0)
                if isinstance(mg, tuple):
                    margin = mg[0] + mg[1]
                else:
                    margin = mg * 2
                # 跳过container（它会自动fill=both expand）
                if child.winfo_reqheight() > 0 and pack.get("expand") == "true":
                    continue
                h += req_h + margin
            # 加上标题栏40 + 标签栏43 + content_frame上下padding(5+5)
            h += 40 + 43 + 10
            h = min(h, app.winfo_screenheight() - 100)
            if frame is app.mouse_frame:
                h = max(0, h - 8)
            elif frame is app.keyboard_frame:
                h = int(h * 1.10)
            w = 346
            x, y = app.winfo_x(), app.winfo_y()
            app.geometry(f"{w}x{h}+{x}+{y}")
            break
