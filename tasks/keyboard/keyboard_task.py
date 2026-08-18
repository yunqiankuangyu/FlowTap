"""
键盘任务模块
"""
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core import KeyboardSimulator, random_delay


class TaskStatus(Enum):
    IDLE, RUNNING, WAITING = "● 就绪", "● 运行中", "● 等待触发"


@dataclass
class KeyboardTask:
    task_id: int
    name: str
    key_sequence: List[int] = field(default_factory=list)
    key_interval: float = 0.5
    loop_interval: float = 80.0
    status: TaskStatus = TaskStatus.IDLE
    done_count: int = 0
    relation_type: str = "独立"  # "独立" 或 "在任务x后"
    dependency_task_id: Optional[int] = None  # 前置任务ID
    _running: bool = False
    _thread: Optional[threading.Thread] = field(default=None, repr=False)
    _dependents: List['KeyboardTask'] = field(default_factory=list, repr=False)
    _callback: object = field(default=None, repr=False)
    _countdown_callback: object = field(default=None, repr=False)

    def start(self, callback=None, countdown_callback=None):
        """启动任务"""
        if self._running: return
        self._running, self.status, self.done_count = True, TaskStatus.RUNNING, 0
        if self.relation_type == "独立":
            self._thread = threading.Thread(target=self._loop, args=(callback, countdown_callback), daemon=True)
            self._thread.start()
        else:
            self.status = TaskStatus.WAITING

    def stop(self):
        """停止任务"""
        self._running, self.status = False, TaskStatus.IDLE
        self._countdown_callback = None

    def _loop(self, callback, countdown_callback=None):
        """独立任务的主循环"""
        if getattr(self, '_loop_active', False): return
        self._loop_active = True
        try:
            sim = KeyboardSimulator()
            while self._running:
                self.done_count += 1
                for vk in self.key_sequence:
                    if not self._running: return
                    try: sim.tap_key(vk)
                    except: pass
                    random_delay(self.key_interval, 0.05)
                if callback: callback()
                # 触发依赖此任务的其他任务
                for dep_task in self._dependents:
                    if dep_task._running:
                        threading.Thread(target=dep_task._run_once, daemon=True).start()
                # 循环倒计时显示
                countdown_secs = int(self.loop_interval) - 1
                if countdown_callback and countdown_secs >= 1:
                    for i in range(countdown_secs, 0, -1):
                        if not self._running: return
                        countdown_callback(f"● 等待 {i}s...", "#facc15")
                        time.sleep(1)
                    if not self._running: return
                    countdown_callback("● 执行中...", "#4ade80")
                    remainder = self.loop_interval - countdown_secs
                    random_delay(remainder, 0.01)
                else:
                    random_delay(self.loop_interval, 0.01)
        finally:
            self._loop_active = False

    def _run_once(self):
        """被依赖触发时执行一次"""
        if not self._running: return
        if self.loop_interval > 0:
            remaining = int(self.loop_interval)
            for i in range(remaining, 0, -1):
                if not self._running: return
                if self._countdown_callback:
                    self._countdown_callback(f"● 延时 {i}s...", "#facc15")
                time.sleep(1)
            if self._countdown_callback:
                self._countdown_callback("● 执行中...", "#4ade80")
        if not self._running: return
        sim = KeyboardSimulator()
        self.done_count += 1
        for vk in self.key_sequence:
            if not self._running: return
            try: sim.tap_key(vk)
            except: pass
            random_delay(self.key_interval, 0.05)
        if self._callback: self._callback()
