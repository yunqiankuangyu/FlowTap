"""
录制输入层 —— 键盘组合键 / 鼠标坐标的捕获

从 ui/keyboard_mode.py 的 add_key_action / add_click_action 抽出捕获逻辑,
界面侧换掉: 结果经回调写回 Model, 提示走主窗 toast, 不再往旧 UI 的
task._action_layout 插行。

为什么是复制而不是 import: 旧的两个函数把"怎么捕获"(GetAsyncKeyState 轮询、
全屏遮罩、相对坐标换算)和"往哪儿放"(task._action_rows、_refresh_actions)
写在一起, 参数 app/task 是旧窗口对象 —— 想复用必须改旧文件, 那就破隔离。
按既定做法复制功能, 界面绑定按新 UI 重接。

不复制的三样(属共用层, 见隔离口径):
  ctypes.windll.user32      系统 API
  core.window_gate          绑定进程/相对坐标换算
  vk_map                    键码表
"""
import ctypes
import ctypes.wintypes

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QWidget

from config import Colors, FONT_M, load_settings, get_setting
from .widgets import tip_label
from core.vk_map import VK_NAME

_VK_LO, _VK_HI = 0x08, 0x100      # 扫描区间: Backspace ~ 0xFF(与旧版一致)


def _fresh_key_state():
    """清一遍按键缓冲 —— 否则捕获启动瞬间读到上一次的残留按下位"""
    u32 = ctypes.windll.user32
    for vk in range(_VK_LO, _VK_HI):
        u32.GetAsyncKeyState(vk)


def _read_down(vk):
    """单个键是否按下 —— 默认读系统状态。

    抽成独立函数是为了可测: 测试不可能在运行中的桌面上真按键盘,
    所以 capture_keys 接受 _reader 注入, 测试传假读取器即可整段验证,
    真跑不传就用 GetAsyncKeyState。
    """
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def capture_keys(on_update=None, on_done=None, _reader=None):
    """捕获组合键。

    按住的键实时进集合, 全部松开即确认 —— 支持单键与多键组合。
    on_update(vk_list) 每轮回显, UI 据此显示「⏳ W (全部松开完成)」
    on_done(vk_list)   确认后回调
    _reader(vk) -> bool   注入用的读取器(测试), 缺省读系统按键状态
    返回可中断句柄(调 stop 取消), 避免捕获结束后仍写回
    """
    read = _reader or _read_down
    _fresh_key_state()

    state = {"pressed": set(), "combo": [], "stop": False}
    poll = QTimer()

    def stop():
        state["stop"] = True
        poll.stop()

    def tick():
        if state["stop"]:
            poll.stop()
            return
        pressed, combo = state["pressed"], state["combo"]
        for vk in range(_VK_LO, _VK_HI):
            down = bool(read(vk))
            if down and vk not in pressed:
                pressed.add(vk)
                if vk not in combo:
                    combo.append(vk)
                if on_update:
                    on_update(list(combo))
            elif not down and vk in pressed:
                pressed.discard(vk)
        if combo and not pressed:          # 有过按键且现在全松开 = 确认
            poll.stop()
            if on_done:
                on_done(list(combo))

    poll.timeout.connect(tick)
    poll.start(15)
    return stop


def _toast(text):
    """提示走主窗 toast。

    录制层不该依赖具体窗口(它是输入层), 所以用模块级 sink:
    main_v2 在建好主窗后把 toast 函数挂进来, 挂了就发, 没挂就静默。
    """
    if _SINK:
        _SINK(text)


_SINK = None      # main_v2 建窗后挂进来, 见 main_v2.main()


def set_sink(fn):
    global _SINK
    _SINK = fn


def capture_click(win, on_done=None, timeout_ms=15000):
    """录制鼠标坐标: 全屏遮罩 + 50ms 轮询, 点左键确认 / ESC 取消

    主窗会临时移到屏幕外 —— 否则遮罩盖住主窗后, 点到主窗上录的是自己的坐标。
    绑定进程时换算成客户区相对坐标, 窗口拖走后仍点得准(复用 core.window_gate)。
    返回可中断句柄。
    """
    screen = QApplication.primaryScreen().geometry()
    orig = win.frameGeometry().topLeft()

    # 主窗让到屏幕外, 让遮罩之下只剩用户要点击的目标
    win.move(screen.width() + 200, screen.height() + 200)

    ov = QWidget()
    ov.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    ov.setAttribute(Qt.WA_TranslucentBackground, True)
    ov.setAttribute(Qt.WA_ShowWithoutActivating, True)
    ov.setStyleSheet("background: rgba(0,0,0,80);")
    ov.setGeometry(screen)
    ov.closeEvent = lambda e: e.ignore()

    tip = tip_label(ov, "🎯 点击任意位置绑定  |  ESC 取消  |  15秒超时")
    tip.adjustSize()
    tip.move((screen.width() - tip.width()) // 2,
             (screen.height() - tip.height()) // 2)
    ov.show()
    ov.raise_()

    state = {"done": False, "poll": QTimer(), "wait": QTimer(), "safety": QTimer()}

    def restore():
        ov.hide()
        ov.deleteLater()
        win.move(orig.x(), orig.y())

    def finish(act=None, keep=False):
        if state["done"]:
            return
        state["done"] = True
        for t in (state["poll"], state["wait"], state["safety"]):
            t.stop()
        QTimer.singleShot(0, restore)
        if act is not None and on_done:
            on_done(act)
        elif not keep:
            _toast("已取消录制")

    def pick_point(p):
        """点击坐标 -> 动作; 绑定进程时改存客户区相对坐标"""
        delay = float(get_setting("default_delay"))
        act = {"type": "click", "x": p.x, "y": p.y, "delay": delay,
               "hold": 0, "lid": None}
        try:
            from core.window_gate import get_bound_process, window_at_point
            bound = get_bound_process()
            if bound:
                hwnd = window_at_point(p.x, p.y, exclude=int(ov.winId()),
                                       process=bound)
                if hwnd:
                    rect, org = ctypes.wintypes.RECT(), ctypes.wintypes.POINT(0, 0)
                    u32 = ctypes.windll.user32
                    if u32.GetClientRect(hwnd, ctypes.byref(rect)) and \
                       u32.ClientToScreen(hwnd, ctypes.byref(org)):
                        act.update(rel=True, x=p.x - org.x, y=p.y - org.y,
                                   sx=p.x, sy=p.y)
        except Exception:
            pass                       # 换算失败就用屏幕绝对坐标, 不中断录制
        return act

    def poll_input():
        u32 = ctypes.windll.user32
        if u32.GetAsyncKeyState(0x1B) & 0x8000:      # ESC
            finish(None)
            return
        if u32.GetAsyncKeyState(0x01) & 0x8000:      # 左键
            pt = ctypes.wintypes.POINT()
            u32.GetCursorPos(ctypes.byref(pt))
            finish(pick_point(pt))

    def initial_wait():
        if ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000:
            return                                    # 还没松开按钮, 继续等
        state["wait"].stop()
        state["poll"].start(50)

    state["poll"].timeout.connect(poll_input)
    state["wait"].timeout.connect(initial_wait)
    state["wait"].start(50)
    state["safety"].setSingleShot(True)
    state["safety"].timeout.connect(lambda: finish(None))
    state["safety"].start(timeout_ms)

    def stop():
        if not state["done"]:
            finish(None)
    return stop
