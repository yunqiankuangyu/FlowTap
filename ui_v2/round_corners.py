"""
无边框窗口圆角 —— 与旧 core/window_gate 隔离

只取新 UI 需要的那一个函数(接口与旧同名 apply_round_corners), 不带入 core/ 里的
前台闸门/进程绑定等注入安全逻辑: 那是任务执行层的职责, 与界面无关。
"""
import ctypes

# DWM 圆角偏好常量
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_DONOTROUND = 0      # 不让 DWM 参与圆角: 形状与描边全部由 paintEvent 自绘说了算


def apply_round_corners(widget):
    """关闭 DWM 自带圆角(名字保留, 调用点不用改)。

    为什么必须关: DWM 的圆角封顶 8px 且**自带一圈官方描边**。我们是
    WA_TranslucentBackground + paintEvent 按 _r 自绘任意半径 —— 自绘半径一大,
    DWM 按它自己小圆角画的那圈描边就落在角部透明区里, 成为一圈"旧圆角虚影"
    (实测 A/B: ROUND 时窗口边缘有 1px 描边线, DONOTROUND 即消失)。
    setWindowFlags 会重建句柄, 改完 flag 要重调本函数(DWM 状态会丢)。
    Win10 不支持该属性时静默失败, 不抛异常。
    """
    try:
        import ctypes
        from ctypes import wintypes
        hwnd = int(widget.winId())
        if not hwnd:
            return False
        pref = ctypes.c_int(_DWMWCP_DONOTROUND)
        hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), _DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(pref), ctypes.sizeof(pref))
        return hr == 0
    except Exception:
        return False
