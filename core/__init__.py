"""
核心输入模拟模块
"""
import ctypes
import ctypes.wintypes


# Win32 常量
INPUT_KEYBOARD = 1
INPUT_MOUSE = 0
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.wintypes.WORD), ("wScan", ctypes.wintypes.WORD),
                ("dwFlags", ctypes.wintypes.DWORD), ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.wintypes.LONG), ("dy", ctypes.wintypes.LONG),
                ("mouseData", ctypes.wintypes.DWORD), ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("union", INPUT_UNION)]


def random_delay(base, jitter=0.1):
    """随机延迟，防止检测
    base: 基础延迟(秒)
    jitter: 相对抖动比例(0~1)
    """
    import time, random
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
        random_delay(0.05, 0.1)

    def hold_key(self, vk, duration):
        """按住一个键持续 duration 秒后释放（模拟真人按住，非连点）"""
        scan = self.user32.MapVirtualKeyW(vk, 0)
        self._send(self._make_keyboard_input(vk, scan))
        if duration > 0:
            random_delay(duration, 0.05)
        self._send(self._make_keyboard_input(vk, scan, KEYEVENTF_KEYUP))

    def combo_press(self, vks):
        """依次按下多个键（组合键按下阶段，不释放）"""
        for vk in vks:
            scan = self.user32.MapVirtualKeyW(vk, 0)
            self._send(self._make_keyboard_input(vk, scan))
            random_delay(0.03, 0.02)

    def combo_release(self, vks):
        """逆序释放组合键"""
        for vk in reversed(vks):
            scan = self.user32.MapVirtualKeyW(vk, 0)
            self._send(self._make_keyboard_input(vk, scan, KEYEVENTF_KEYUP))
            random_delay(0.03, 0.02)


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
        random_delay(0.02, 0.17)
        sw, sh = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
        ax, ay = int(x * 65535 / sw), int(y * 65535 / sh)
        flags_d = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        flags_u = MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        self._send(
            self._make_mouse_input(ax, ay, flags_d),
            self._make_mouse_input(ax, ay, flags_u)
        )

    def hold_click(self, x, y, duration):
        """在指定位置按住鼠标左键持续 duration 秒后释放（模拟真人按住，非连点）"""
        self.move_mouse(x, y)
        random_delay(0.02, 0.17)
        sw, sh = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
        ax, ay = int(x * 65535 / sw), int(y * 65535 / sh)
        flags_d = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        flags_u = MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        self._send(self._make_mouse_input(ax, ay, flags_d))
        if duration > 0:
            random_delay(duration, 0.05)
        self._send(self._make_mouse_input(ax, ay, flags_u))

    def move_mouse(self, x, y):
        #拟人化移动，弧线轨迹+钟形速度+落点微偏+概率过冲修正
        import time, random, math
        sw, sh = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)

        def to_abs(px, py):
            return int(px * 65535 / sw), int(py * 65535 / sh)

        move_flags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE
        sx, sy = self.get_mouse_pos()
        dist = math.hypot(x - sx, y - sy)
        #距离过近直接归位
        if dist < 3:
            self._send(self._make_mouse_input(*to_abs(x, y), move_flags))
            return

        #时长随距离增长，80ms~400ms，±15%抖动
        dur = min(0.4, max(0.08, 0.08 + dist * 0.0006)) * random.uniform(0.85, 1.15)

        #真实终点先做±2px微偏，40%概率再沿运动方向过冲3~8px
        tx = x + random.uniform(-2, 2)
        ty = y + random.uniform(-2, 2)
        ux, uy = (tx - sx) / dist, (ty - sy) / dist
        gx, gy = tx, ty
        overshoot = random.random() < 0.4
        if overshoot:
            gx += ux * random.uniform(3, 8)
            gy += uy * random.uniform(3, 8)

        #二次贝塞尔控制点，垂直偏移距离的5~15%
        cx, cy = (sx + gx) / 2, (sy + gy) / 2
        px, py = -(gy - sy), (gx - sx)
        plen = math.hypot(px, py) or 1.0
        off = dist * random.uniform(0.05, 0.15) * random.choice((-1, 1))
        cx += px / plen * off
        cy += py / plen * off

        #钟形速度曲线，慢起快中收
        def ease(t):
            return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2

        #主轨迹采样，每约8ms发一个绝对坐标点
        steps = max(6, min(50, int(dur / 0.008)))
        step_sleep = dur / steps
        for i in range(1, steps + 1):
            t = ease(i / steps)
            bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * cx + t * t * gx
            by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * cy + t * t * gy
            self._send(self._make_mouse_input(*to_abs(bx, by), move_flags))
            time.sleep(step_sleep)

        #过冲后小弧拉回微偏终点
        if overshoot:
            for i in range(1, 6):
                t = 1 - (1 - i / 5) ** 2
                fx = gx + (tx - gx) * t
                fy = gy + (ty - gy) * t
                self._send(self._make_mouse_input(*to_abs(fx, fy), move_flags))
                time.sleep(0.008)

        #精确归位到目标点，保证点击落点与安全半径判断准确
        self._send(self._make_mouse_input(*to_abs(x, y), move_flags))

    def get_mouse_pos(self):
        """获取当前鼠标位置"""
        p = ctypes.wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(p))
        return (p.x, p.y)
