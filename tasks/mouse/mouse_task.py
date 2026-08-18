"""
鼠标任务模块
"""
import threading
from dataclasses import dataclass, field
from typing import Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core import MouseSimulator, random_delay
from tasks.keyboard.keyboard_task import TaskStatus


@dataclass
class MouseTask:
    position: Optional[tuple] = None
    interval: float = 1.0
    status: TaskStatus = TaskStatus.IDLE
    done_count: int = 0
    _running: bool = False
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _safe_radius: int = 300

    def start(self, callback=None):
        """启动任务"""
        if self._running or not self.position: return
        self._running, self.status, self.done_count = True, TaskStatus.RUNNING, 0
        self._thread = threading.Thread(target=self._loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop(self, callback=None, msg="已停止"):
        """停止任务"""
        self._running, self.status = False, TaskStatus.IDLE
        if callback: callback(msg)

    def _loop(self, callback):
        """主循环"""
        sim = MouseSimulator()
        first = True
        while self._running:
            if self.position:
                if not first:
                    cur = sim.get_mouse_pos()
                    dx, dy = cur[0]-self.position[0], cur[1]-self.position[1]
                    if (dx*dx+dy*dy)**0.5 > self._safe_radius:
                        self.stop(callback, "安全停止"); return
                sim.move_mouse(*self.position)
                random_delay(0.05, 0.3)
            try: sim.click_mouse(*self.position); self.done_count += 1
            except: pass
            first = False
            random_delay(self.interval, 0.07)
