"""
键盘模拟模块 - Win32 API底层键盘输入
"""
import ctypes
import ctypes.wintypes
import time
import random

# Win32 常量
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.wintypes.WORD), ("wScan", ctypes.wintypes.WORD),
                ("dwFlags", ctypes.wintypes.DWORD), ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", None)]  # mi 留空，鼠标模块会覆盖


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("union", INPUT_UNION)]


def random_delay(base, jitter=0.1):
    """随机延迟，防止检测"""
    time.sleep(max(0.01, base * (1 + random.uniform(-jitter, jitter))))


class KeyboardSimulator:
    """键盘输入模拟器"""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        ctypes.windll.kernel32.SetErrorMode(0x0003)

    def _make_keyboard_input(self, vk, scan=0, flags=0):
        """创建键盘输入结构"""
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki.wVk = vk
        inp.union.ki.wScan = scan
        inp.union.ki.dwFlags = flags
        inp.union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
        return inp

    def _send(self, *inputs):
        """发送输入事件"""
        arr = (INPUT * len(inputs))(*inputs)
        self.user32.SendInput(len(inputs), ctypes.byref(arr), ctypes.sizeof(INPUT))

    def tap_key(self, vk):
        """按下并释放一个键"""
        scan = self.user32.MapVirtualKeyW(vk, 0)
        self._send(
            self._make_keyboard_input(vk, scan),
            self._make_keyboard_input(vk, scan, KEYEVENTF_KEYUP)
        )
        random_delay(0.05, 0.3)
