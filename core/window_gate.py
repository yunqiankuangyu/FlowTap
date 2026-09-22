"""
目标窗口前台闸门
绑定进程名后，仅当该进程的窗口位于前台才放行注入；未绑定恒放行
"""
import os
import ctypes
import ctypes.wintypes

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


def is_target_foreground():
    """未绑定恒为 True；绑定后仅当前台窗口属于目标进程才 True"""
    if not _bound_process:
        return True
    return get_foreground_process() == _bound_process

# ══════════ 无边框窗口圆角（DWM，Win11 build 22000+）══════════

_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_ROUND = 2  # Win11 标准圆角（约8px，与卡片 11px 接近）


def apply_round_corners(widget):
    """给无边框窗口加 DWM 圆角。

    样式表 border-radius 对顶层窗口无效，必须走 DwmSetWindowAttribute。
    注意：setWindowFlags() 会重建 native 句柄、圆角失效，之后需重调本函数。
    Win10 / 旧版 Win11 不支持时静默失败，保持直角，不抛异常。
    """
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = int(widget.winId())
        if not hwnd:
            return False
        pref = ctypes.c_int(_DWMWCP_ROUND)
        hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), _DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(pref), ctypes.sizeof(pref))
        return hr == 0
    except Exception:
        return False
