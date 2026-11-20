"""
目标窗口前台闸门
绑定进程名后，仅当该进程的窗口位于前台才放行注入；未绑定恒放行
"""
import os
import ctypes
import ctypes.wintypes

# 圆角实现只有一份(round_corners), 这里转出以保住 base 的既有导入路径
from .round_corners import apply_round_corners

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_bound_process = ""


def set_bound_process(name):
    """设置绑定的进程名（小写 exe 文件名），空串=不绑定"""
    global _bound_process
    _bound_process = (name or "").strip().lower()


def get_bound_process():
    return _bound_process


def get_process_name(hwnd):
    """取窗口所属进程的 exe 文件名（小写），失败返回空串"""
    if not hwnd:
        return ""
    pid = ctypes.wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    h = _kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        n = ctypes.wintypes.DWORD(32768)
        if _kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return os.path.basename(buf.value).lower()
    finally:
        _kernel32.CloseHandle(h)
    return ""


def get_foreground_process():
    """当前前台窗口的进程名（小写）"""
    return get_process_name(_user32.GetForegroundWindow())


def window_at_point(x, y, exclude=0, process=""):
    """Z 序从顶往下找包含 (x,y) 的可见顶层窗口，找到返回 hwnd 否则 0。
    exclude 排除指定句柄（录制遮罩）；process 非空时只认该进程的窗口
    （遮罩/他窗自动跳过继续下钻，绑定录制时用于确认点位属于目标窗口）"""
    found = [0]
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def _cb(hwnd, _l):
        if not hwnd or hwnd == exclude or not _user32.IsWindowVisible(hwnd):
            return True
        r = ctypes.wintypes.RECT()
        if not _user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        if not (r.left <= x < r.right and r.top <= y < r.bottom):
            return True
        if process and get_process_name(hwnd) != process:
            return True
        found[0] = hwnd
        return False
    _user32.EnumWindows(_cb, 0)
    return found[0]


def is_target_foreground():
    """未绑定恒为 True；绑定后仅当前台窗口属于目标进程才 True"""
    if not _bound_process:
        return True
    return get_foreground_process() == _bound_process

