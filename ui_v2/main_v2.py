"""
新 UI 复刻入口 —— 窗口状态机: 主窗 / 设置窗 / 迷你窗 互斥切换

三个窗不是一起弹出来, 而是各就各位:
  启动        只显示主窗(位置读 win_pos_x/y, 与迷你窗各记各的)
  点「设置」   弹出设置窗(再点一次收回)
  点「MINI」  主窗隐藏, 迷你窗接管(迷你窗显示读 mini_pos_x/y)
  迷你窗 ▣    还原主窗(各记各的位置: hide 不改坐标, 主窗回自己原位, 不跟迷你窗走)
  标题栏 —    主窗收成迷你窗

隔离说明: 本包不 import ui/ 下任何代码, 所有组件都是 ui_v2/ 内的独立副本,
改动这里不会影响旧版主程序。需要 -m 方式启动(相对导入), 所以入口不是
python ui_v2/main_v2.py 而是 python -m ui_v2.main_v2。
启动: 双击 启动新UI.bat
"""
import os
import sys

# 以脚本方式直接跑(ui_v2/main_v2.py)时包上下文不存在, 相对导入会失败。
# 这里把项目根塞进 sys.path 并把本包注册进 sys.modules, 让两种启动方式都能用。
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "ui_v2"
    import importlib
    sys.modules["ui_v2"] = importlib.import_module("ui_v2")
    __spec__ = sys.modules["ui_v2"].__spec__

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QObject, QEvent

from config import Colors, THEMES, DEFAULT_THEME, load_settings
from .widgets import WheelScrollFilter, tooltip_qss

from .win_v2 import WinV2
from .win_set import SetWin
from .win_mini import MiniWin
from .window_gate import apply_round_corners
from .base import screen_rect_at


def _center_in(child, parent):
    """把 child 摆到 parent 区域内居中。

    子窗口的默认位置规则(与 QQ/微信设置弹层一致): 在宿主窗口内居中, 而不是
    甩到宿主外面去自己找位置。后者只在"独立对话框"语义下成立, 而设置窗是主窗
    的从属界面, 摆在外面既会脱离主窗上下文, 也会在主窗贴近屏幕边缘时算出
    屏幕外的坐标。
    """
    child.move(parent.x() + (parent.width() - child.width()) // 2,
               parent.y() + (parent.height() - child.height()) // 2)


def _refresh_hk(setw):
    """把热键当前键名刷到设置窗的两个标签上"""
    fn = getattr(setw, "refresh_hotkeys", None)
    if callable(fn):
        fn()


def _set_topmost(w, on):
    """切换窗口置顶 —— 必须改 Qt 的 flag, 不能只用 SetWindowPos 压:

    实测只用 Win32 清掉 WS_EX_TOPMOST, 立刻读是 False, 但跑一轮事件循环 Qt 会按
    WindowStaysOnTopHint 把它顶回去(置顶是 Qt 认定的状态, Win32 只是它的投影)。
    setWindowFlags 会把可见窗隐藏掉, 所以按原可见性补 show()。"""
    f = w.windowFlags()
    want = (f | Qt.WindowStaysOnTopHint) if on else (f & ~Qt.WindowStaysOnTopHint)
    if want == f:
        return
    was_visible = w.isVisible()
    w.setWindowFlags(want)
    apply_round_corners(w)      # 重建句柄, DWM 圆角属性重挂
    if was_visible:
        w.show()
        # 立刻抬回 Z: 重建的窗不 raise 会落回默认层再被切回来 —— "像重启"的观感
        # 主要来自这个跳变(隐藏/显示本身躲不开, Qt 改可见窗 flag 必然隐藏再显示)
        w.raise_()


class _FollowHost(QObject):
    """挂在主窗/迷你窗上的两个职责(设置窗开着时才生效):

    1. Move/Resize -> 设置窗跟着重摆: 拖动是手搬(attach_drag 里 win.move), 每步都发
       QEvent::Move, 逐帧跟上; 主窗最大化/还原发 Resize, 同一条路重摆。只跟可见窗,
       隐藏窗没有移动/尺寸事件。
    2. WindowActivate -> 把设置窗抬回最上: 顶栏可点、任务栏也能激活主窗,
       激活即抬主窗会盖住设置窗, 这里压回去 —— 置顶位不再用来保这个 Z 序,
       于是「窗口置顶=关」时设置窗能跟着主窗一起回到普通层, 不再浮在别的应用上。
    """
    def __init__(self, setw):
        super().__init__()
        self._setw = setw

    def eventFilter(self, obj, ev):
        t = ev.type()
        # Move = 拖动手搬, 逐帧跟上; Resize = 主窗最大化/还原改几何, 同一条路跟着重摆。
        # 只跟可见窗, 隐藏窗没有移动/尺寸事件。
        if t in (QEvent.Move, QEvent.Resize) and self._setw.isVisible() and obj.isVisible():
            _center_in(self._setw, obj)
        elif t == QEvent.WindowActivate and self._setw.isVisible():
            self._setw.raise_()
        return False


def _apply_on_top(on, *wins):
    """「窗口置顶」开关落到窗口上 —— V2Win 建窗时无条件置顶, 必须按设置改一遍。

    不接这一步, 开关只是把 always_on_top 写进 settings.json 的装饰品:
    主窗/迷你窗/设置窗永远压在别的窗口上面。"""
    from PySide6.QtWidgets import QApplication
    prev = QApplication.activeWindow()
    for w in wins:
        _set_topmost(w, on)
    # 焦点还给原来那个窗(通常是设置窗): 重建会把激活权带走, 不还回去就"闪完还跳焦点"
    if prev is not None and prev.isVisible():
        prev.activateWindow()


def _apply_radius(r, *wins):
    """窗口圆角实时生效 —— 改 V2Win._r 再重绘, paintEvent 实时读它画圆角。

    只碰绘制参数, 不动窗口属性: 与置顶不同, 这条路径零隐藏零重建、零闪烁。"""
    r = int(r)
    for w in wins:
        w._r = r
        w.update()


def _relaunch(app):
    """真重启 FlowTap —— 先拉起新进程, 再像关窗口那样退出本进程(等价"关掉再开")。

    测试时点 dock 的「重启」就等于重开一遍, 不用回文件夹双击 启动新UI.bat。
    启动命令与 启动新UI.bat 同源: pythonw -m ui_v2.main_v2, cwd = 项目根,
    PYTHONPATH 清空(同 bat 里那句 set PYTHONPATH=, 不把宿主环境的 venv 路径带过去)。
    退出用 app.quit —— 与标题栏 ✕ / 迷你窗退出同一条路径, 不另造一套。
    热键是 GetAsyncKeyState 轮询、无单实例锁, 新旧进程短暂重叠不会冲突。
    返回是否成功, 失败时由调用方提示(不退, 否则应用直接消失)。
    """
    import subprocess
    try:
        if getattr(sys, "frozen", False):
            # 打包版: sys.executable 就是 exe 自身
            exe = os.path.abspath(sys.executable)
            cmd = [exe]
            cwd = os.path.dirname(exe)
        else:
            exe = sys.executable
            # 用 python.exe 起的也换 pythonw.exe, 免得重启后多带一个控制台窗口
            if exe.lower().endswith("python.exe"):
                w = exe[:-len("python.exe")] + "pythonw.exe"
                if os.path.exists(w):
                    exe = w
            cmd = [exe, "-m", "ui_v2.main_v2"]
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        subprocess.Popen(cmd, cwd=cwd, env=env)
    except Exception:
        from logger import log_error
        import traceback
        log_error("ui_v2.relaunch", traceback.format_exc())
        return False
    app.quit()
    return True


def wire(win, setw, mini, app):
    # 把三个窗接成状态机。单独抽成函数而不是埋在 main() 里:
    # 验收脚本要复用同一套接线, 照抄一份必然与实现漂移。
    def top(w):
        # show() 不保证在栈顶, 显式抬一次, 否则会压在别的窗口底下看不见
        w.show()
        w.raise_()
        w.activateWindow()

    def _set_panel(on):
        """设置弹层开关态: 开 = 禁内容, 关 = 原样恢复。

        禁的是"内容区(三栏) + 停靠栏", 不是整窗 —— 整窗禁用会把顶栏一起废掉,
        拖动/最小化/关闭就全失效了。顶栏留在可用侧(拖动时设置窗由 _FollowHost
        跟着重摆); 拖动/点击会激活主窗, Z 序由 _FollowHost 抬回设置窗保证, 不再
        碰置顶位 —— 置顶只归「窗口置顶」开关管(_apply_on_top), 两件事不混。
        迷你窗整窗禁用(它不是拖动场景)。
        """
        win.body.setEnabled(not on)
        win.dock.setEnabled(not on)
        mini.setEnabled(not on)

    def show_set():
        if setw.isVisible():
            setw.hide()
            win._unveil()
            _set_panel(False)
            return
        # 设置窗是主窗的子界面, 默认在主窗内居中(与 QQ/微信的设置弹层同一惯例)。
        # 不做"贴到主窗外面去"的定位: 那是独立对话框的做法, 一旦主窗贴近屏幕
        # 边缘就会算出屏幕外的位置, 后面再加 clamp 也只是把错误掩盖掉。
        _center_in(setw, win)
        win._veil()          # 压暗主窗, 表明设置是临时弹层
        # _set_panel 里改 flag 会隐藏再显主窗, 必须放在 top(setw) 之前,
        # 否则最后抬起来的是主窗, 设置窗被压在下面
        _set_panel(True)
        top(setw)

    def show_mini():
        # 位置各记各的: 读上次落盘的 mini_pos_x/y(一次没拖过才按主窗右下角兜底),
        # 不再每次按主窗重摆 —— 否则落盘值永远用不上, 主窗一动迷你窗还跟着跳。
        # 坐标按点查屏再 clamp, 拔屏/换分辨率后不会摆到屏幕外。
        s = load_settings()
        if "mini_pos_x" in s and "mini_pos_y" in s:
            x, y = int(s["mini_pos_x"]), int(s["mini_pos_y"])
        else:
            x = win.x() + win.width() - mini.width()
            y = win.y() + 120
        g = screen_rect_at(x + mini.width() // 2, y + mini.height() // 2)
        x = max(g.left(), min(x, g.right() - mini.width()))
        y = max(g.top(), min(y, g.bottom() - mini.height()))
        mini.move(x, y)
        win._unveil()      # 主窗要隐藏, 遮罩必须先撤, 否则下次显示时还压着
        win.hide()
        setw.hide()
        _set_panel(False)
        top(mini)

    def show_main():
        # 位置各记各的: 主窗 hide 不改坐标, show 出来就在自己原位, 不跟迷你窗走
        # (旧版会 app.move(mx,my) 把主窗搬到迷你窗处, 用户已拍板改掉)
        mini.hide()
        setw.hide()
        win._unveil()
        _set_panel(False)
        top(win)

    def dock_click(i, text):
        if "设置" in text:
            show_set()
        elif "MINI" in text:
            show_mini()
        elif "全部" in text:
            win.toggle_all_tasks()
        elif "重启" in text:
            # 真重启: 起新进程再退本进程, 等价关掉再开(测试不用回文件夹点启动)
            if not _relaunch(app):
                win.toast("重启失败, 详见 runtime.log")

    # 拖主窗时设置窗跟手 + 激活压回 Z 序(见 _FollowHost); 挂成属性防 GC 收走
    win._follow = _FollowHost(setw)
    win.installEventFilter(win._follow)
    mini.installEventFilter(win._follow)

    # 「窗口置顶」开关: 启动按设置落一次, 之后开关一动就实时落到三个窗
    from config import load_settings as _ls_top
    _s_top = _ls_top()
    _apply_on_top(bool(_s_top.get("always_on_top", True)), win, mini, setw)
    setw.on_top_change = lambda on: _apply_on_top(on, win, mini, setw)
    # 「窗口圆角」同理: 启动按设置(没有就保持建窗默认), 拉条一拖就实时重绘
    if "win_radius" in _s_top:
        _apply_radius(_s_top["win_radius"], win, mini, setw)
    setw.on_radius_change = lambda r: _apply_radius(r, win, mini, setw)

    # 「窗口不透明度」同理: 建窗时已按 settings 套过(base.V2Win), 这里接拖动实时。
    # 滑条一发两值: a = 停靠栏玻璃底色(50% 锚线性放大, 不做 1-x 取反),
    # op = v/100 窗体不透明度(与标签、旧 UI 同义) —— 窗体不吃 a 那套映射。
    def _on_opacity(a, op):
        win.dock.set_alpha(a)
        for wgt in (win, setw, mini):
            try:
                wgt.setWindowOpacity(op)
            except Exception:
                pass
    setw.on_alpha_change = _on_opacity
    win.dock.set_alpha(setw.alpha)

    # 设置窗点自己的 x 时也要撤主窗遮罩 + 解禁主窗, 否则关掉后主窗一直压暗且点不动
    def _on_set_close():
        win._unveil()
        _set_panel(False)
    setw.on_close = _on_set_close
    # 主题预览要刷到所有窗 —— 设置窗换肤时把主窗/迷你窗一并整树重刷
    setw.wins = [win, mini]
    win.dock.on_item = dock_click
    win.on_minimize = show_mini
    win.on_quit = app.quit

    # 全局热键: 起停任务与 dock 按钮走同一套逻辑(不另写一份启停),
    # 改绑完成后刷新设置窗的热键标签。
    from .hotkey import start_hotkeys, hk_name, stop_hotkeys
    hk = start_hotkeys(
        win,
        on_start=lambda: (win.toggle_all_tasks(),
                          win.toast(f"▶ 开始 ({hk_name(win._start_hk)})")),
        on_stop=lambda: (win.m.running and win.toggle_all_tasks(),
                         win.toast(f"⏹ 已停止 ({hk_name(win._stop_hk)})")),
        on_changed=lambda which, vk: _refresh_hk(setw),
    )
    win._hk_info = hk
    setw._hk_info = hk            # 设置窗的"修改热键"走它
    _refresh_hk(setw)

    # 窗口销毁时停轮询, 否则 QTimer 还在读全局键盘状态
    win.destroyed.connect(lambda *a: stop_hotkeys(hk))
    mini.on_restore = show_main
    # 迷你窗已按旧版形态裁掉 ⚙ 设置入口(设置回主窗进), 不再挂 on_settings
    mini.on_quit = app.quit
    return top


def _apply_theme(name):
    """只把主题色写进 Colors 类属性, 不碰 QApplication 的样式表。

    不直接用 config.Colors.apply: 它会在内部 import ui.widgets 去给 tooltip
    上色, 那是旧目录, 一旦新 UI 依赖它, 两边就被绑死。tooltip 样式由本包的
    .widgets.tooltip_qss 自行设置(见 main), 与 Colors.apply 无关。
    """
    t = THEMES.get(name) or THEMES[DEFAULT_THEME]
    for k, v in t.items():
        setattr(Colors, k, v)


def main():
    app = QApplication(sys.argv)
    s = load_settings()
    # 注意: Colors.apply 内部会去 import ui.widgets 给 tooltip 上色(config/themes.py
    # 的既有行为), 那会让新 UI 依赖旧目录。这里先把 tooltip 样式挂好, 再让
    # apply 覆盖 —— 它 import 不到 ui 时会抛错, 所以改由 _apply_theme 兜住。
    app.setStyleSheet(tooltip_qss())
    _apply_theme(s["theme"])
    app.installEventFilter(WheelScrollFilter(app))

    win = WinV2()
    setw = SetWin()
    mini = MiniWin(win.m)      # 与主窗共用同一份 Model, 状态天然同步
    setw.hide()
    mini.hide()

    # 任务数变了(主窗增删任务)让迷你窗刷新状态行与按钮计数
    win.m._mini = mini

    # 录制/框选的提示层不持有窗口引用, 经 sink 中转(见 capture.set_sink)
    from . import capture as _cap
    _cap.set_sink(win.toast)

    top = wire(win, setw, mini, app)
    top(win)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
