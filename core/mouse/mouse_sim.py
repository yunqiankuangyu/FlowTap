"""
鼠标模拟模块 - Win32 API底层鼠标输入
"""
import ctypes
import ctypes.wintypes
import time
import random

# Win32 常量
INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.wintypes.LONG), ("dy", ctypes.wintypes.LONG),
                ("mouseData", ctypes.wintypes.DWORD), ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", None), ("mi", MOUSEINPUT)]  # ki 留空，键盘模块会覆盖


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("union", INPUT_UNION)]


def random_delay(base, jitter=0.1):
    """随机延迟，防止检测"""
    time.sleep(max(0.01, base * (1 + random.uniform(-jitter, jitter))))


class MouseSimulator:
    """鼠标输入模拟器"""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        ctypes.windll.kernel32.SetErrorMode(0x0003)

    def _make_mouse_input(self, dx=0, dy=0, flags=0):
        """创建鼠标输入结构"""
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = dx
        inp.union.mi.dy = dy
        inp.union.mi.dwFlags = flags
        inp.union.mi.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
        return inp

    def _send(self, *inputs):
        """发送输入事件"""
        arr = (INPUT * len(inputs))(*inputs)
        self.user32.SendInput(len(inputs), ctypes.byref(arr), ctypes.sizeof(INPUT))

    def click_mouse(self, x, y):
        """在指定位置点击鼠标"""
        self.move_mouse(x, y)
        random_delay(0.02, 0.5)
        sw, sh = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
        ax, ay = int(x * 65535 / sw), int(y * 65535 / sh)
        flags_d = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        flags_u = MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        self._send(
            self._make_mouse_input(ax, ay, flags_d),
            self._make_mouse_input(ax, ay, flags_u)
        )

    def move_mouse(self, x, y):
        """移动鼠标到指定位置"""
        sw, sh = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
        ax, ay = int(x * 65535 / sw), int(y * 65535 / sh)
        self._send(self._make_mouse_input(ax, ay, MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE))

    def get_mouse_pos(self):
        """获取当前鼠标位置"""
        p = ctypes.wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(p))
        return (p.x, p.y)
