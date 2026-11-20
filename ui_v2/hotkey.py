"""
全局热键 —— F8/F9 起停任务, 以及"按住新键改绑"

从 ui/app.py 的 _poll_hotkey 抽出(功能部分): 轮询、捕获模式、ESC 取消、
落盘都照搬; 绑定换成新 UI 的启停回调。

照搬的关键细节:
  * 用 GetAsyncKeyState 的 & 0x0001(事件位, "这一拍刚按下过"), 不是 & 0x8000
    (状态位, 按住期间一直为真) —— 用状态位会让按住的那几秒连发触发。
  * 键名与存盘键沿用旧版: settings.json 的 start_hotkey / stop_hotkey。
  * ESC(0x1B) 在捕获模式下是取消, 不写盘。

不复制的: 旧版触发时调 keyboard_mode.toggle_all / show_floating_notification,
那是旧界面的动作; 这里只负责"按了哪个键", 动作交给 on_start/on_stop 回调。
"""
import ctypes

from PySide6.QtCore import QTimer

from config import load_settings, save_settings

_VK_LO, _VK_HI = 0x08, 0x100
_ESC = 0x1B


def start_hotkeys(win, on_start, on_stop, on_changed=None, interval=50):
    """起热键轮询。返回 {poller, ...} 状态字典, 供 stop_hotkeys 收尾。

    win          任意对象, 用来挂捕获状态(与旧版把状态挂 app 上一致)
    on_start()   按下开始键
    on_stop()    按下停止键
    on_changed(which, vk)  改绑完成后回传(which='start'|'stop'), 供刷新标签
    """
    # 默认值照抄旧版 ui/app.py 的常量: stop=0x77(F8)、start=0x76(F7)。
    # 0x70=F1, 所以 0x77=F8 —— 旧版行尾注释没错。
    # settings.json 里有就用文件的 —— 那是旧版写的同一份(该文件里 stop 是 119=0x77)。
    s = load_settings()
    win._stop_hk = int(s.get("stop_hotkey", 0x77))
    win._start_hk = int(s.get("start_hotkey", 0x76))
    win._hk_capturing = False
    win._hk_target = None

    # 设 parent: 窗口销毁时定时器跟着销毁, 否则它会在窗口死后继续 tick,
    # 报 "Internal C++ object already deleted"(实测退出时抛过这个)。
    # win 必须是 QObject 才能当 parent —— 调用方可能传普通对象(测试用的替身)。
    from PySide6.QtCore import QObject
    t = QTimer(win if isinstance(win, QObject) else None)

    def poll():
        try:
            u32 = ctypes.windll.user32
            if getattr(win, "_hk_capturing", False):
                for vk in range(_VK_LO, _VK_HI):
                    if u32.GetAsyncKeyState(vk) & 0x0001:
                        win._hk_capturing = False
                        if vk != _ESC:
                            which = win._hk_target
                            if which == "stop":
                                win._stop_hk = vk
                                save_settings({**load_settings(), "stop_hotkey": vk})
                            else:
                                win._start_hk = vk
                                save_settings({**load_settings(), "start_hotkey": vk})
                        if on_changed:
                            on_changed(win._hk_target, vk)
                        return
                return
            if u32.GetAsyncKeyState(win._stop_hk) & 0x0001:
                on_stop()
            elif u32.GetAsyncKeyState(win._start_hk) & 0x0001:
                on_start()
        except Exception as e:
            try:
                from logger import log_error
                log_error("ui_v2.hotkey_poll", e)
            except Exception:
                pass

    t.timeout.connect(poll)
    t.start(interval)

    def begin_capture(which):
        """进入改绑模式: 下一次按下的键成为该热键, ESC 取消"""
        win._hk_capturing = True
        win._hk_target = which

    def state():
        return {"start": win._start_hk, "stop": win._stop_hk,
                "capturing": win._hk_capturing, "target": win._hk_target}

    return {"timer": t, "begin": begin_capture, "state": state}


def hk_name(vk):
    """键码 -> 显示名。

    用 model._vk_name 而不是旧版的 VK_NAME.get(vk, hex(vk)): 后者对
    F13~F24 和 VK 表外的键会显示 "0x87" 这种键码, 而 _vk_name 会给 "F24"。
    全应用只留一处键名换算。
    """
    from .model import _vk_name
    return _vk_name(vk)


def stop_hotkeys(info):
    """停轮询(退出/重建时用)"""
    if info:
        info["timer"].stop()
