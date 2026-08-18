"""
键盘任务模块（支持键鼠混合动作）
"""
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core import KeyboardSimulator, MouseSimulator, random_delay


class TaskStatus(Enum):
    IDLE, RUNNING, WAITING = "● 就绪", "● 运行中", "● 等待触发"


def make_key_action(vk, delay=0.5, hold=0):
    """创建键盘动作"""
    return {"type": "key", "vk": vk, "delay": delay, "hold": hold}


def make_click_action(x, y, delay=0.5, hold=0):
    """创建鼠标点击动作"""
    return {"type": "click", "x": x, "y": y, "delay": delay, "hold": hold}


def fmt_action(action):
    """格式化动作为可读字符串"""
    from vk_map import VK_NAME
    if action["type"] == "key":
        name = VK_NAME.get(action["vk"], f'[{action["vk"]}]')
        return name
    elif action["type"] == "click":
        return f"({action['x']}, {action['y']})"
    return "?"


@dataclass
class KeyboardTask:
    task_id: int
    name: str
    actions: List[dict] = field(default_factory=list)
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

    def _execute_actions(self):
        """执行一轮动作序列"""
        kb_sim = KeyboardSimulator()
        ms_sim = MouseSimulator()
        for action in self.actions:
            if not self._running: return False
            try:
                hold = action.get("hold", 0)
                if action["type"] == "key":
                    if hold > 0:
                        kb_sim.hold_key(action["vk"], hold)
                    else:
                        kb_sim.tap_key(action["vk"])
                elif action["type"] == "click":
                    if hold > 0:
                        ms_sim.hold_click(action["x"], action["y"], hold)
                    else:
                        ms_sim.click_mouse(action["x"], action["y"])
            except: pass
            random_delay(action.get("delay", 0.5), 0.05)
        return True

    def _loop(self, callback, countdown_callback=None):
        """独立任务的主循环"""
        if getattr(self, '_loop_active', False): return
        self._loop_active = True
        try:
            while self._running:
                self.done_count += 1
                if not self._execute_actions(): return
                # 触发依赖此任务的其他任务
                for dep_task in self._dependents:
                    if dep_task._running:
                        threading.Thread(target=dep_task._run_once, daemon=True).start()
                # 循环倒计时显示
                countdown_secs = int(self.loop_interval)
                if countdown_secs >= 1:
                    for i in range(countdown_secs, 0, -1):
                        if not self._running: return
                        if self._countdown_callback:
                            self._countdown_callback(f"● 等待 {i}s...", "#facc15")
                        time.sleep(1)
                    if not self._running: return
                    countdown_callback("● 执行中...", "#4ade80")
                    remainder = self.loop_interval - countdown_secs
                    if remainder > 0.05:
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
                    self._countdown_callback(f"● 等待 {i}s...", "#facc15")
                time.sleep(1)
            if self._countdown_callback:
                self._countdown_callback("● 执行中...", "#4ade80")
        if not self._running: return
        self.done_count += 1
        self._execute_actions()
        if self._callback: self._callback()
