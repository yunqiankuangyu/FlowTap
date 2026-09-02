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


def make_combo_action(vks, delay=0.5, hold=0):
    """创建组合键动作（多个键同时按住）"""
    return {"type": "combo", "vks": list(vks), "delay": delay, "hold": hold}


def make_click_action(x, y, delay=0.5, hold=0):
    """创建鼠标点击动作"""
    return {"type": "click", "x": x, "y": y, "delay": delay, "hold": hold}


def fmt_action(action):
    """格式化动作为可读字符串"""
    from vk_map import VK_NAME
    if action["type"] == "key":
        name = VK_NAME.get(action["vk"], f'[{action["vk"]}]')
        return name
    elif action["type"] == "combo":
        return "+".join(VK_NAME.get(vk, f"[{vk}]") for vk in action["vks"])
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
    max_runs: int = 0  # 执行次数限制，0=无限
    _running: bool = False
    _paused: bool = False  # 暂停中（时间计数冻结，随时可继续）
    _pause_cond: threading.Condition = field(default_factory=threading.Condition, repr=False)
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
        self._loop_active = False  # 防止异常后 _loop_active 卡死导致无法重启
        self.resume()  # 唤醒可能挂在暂停等待上的线程

    # 暂停：运行中或倒计时中都可（倒计时中暂停会冻结 3-2-1）
    def pause(self):
        if self._running or getattr(self, '_countdown_active', False):
            self._paused = True

    def resume(self):
        """继续：从冻结的位置接着跑"""
        self._paused = False
        with self._pause_cond:
            self._pause_cond.notify_all()

    def _pause_gate(self):
        """暂停闸门：暂停期间在此阻塞；每次醒来看看是否仍需等待（防惊群）"""
        while self._running and self._paused:
            with self._pause_cond:
                self._pause_cond.wait(timeout=0.2)

    def _pause_aware_delay(self, seconds):
        """可暂停的延迟：暂停时计时冻结，继续后剩余时间接着走"""
        remaining = max(0.0, seconds)
        while self._running and remaining > 1e-9:
            self._pause_gate()
            if not self._running:
                return
            if self._paused:
                time.sleep(0.05)  # 暂停中：不计秒
                continue
            t0 = time.monotonic()
            time.sleep(min(0.2, remaining))
            if not self._running:
                return
            elapsed = 0.0 if self._paused else time.monotonic() - t0
            remaining -= elapsed

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
                elif action["type"] == "combo":
                    vks = action["vks"]
                    if not vks:
                        continue
                    if hold > 0:
                        kb_sim.combo_press(vks)
                        random_delay(hold, 0.05)
                        kb_sim.combo_release(vks)
                    else:
                        kb_sim.combo_press(vks)
                        random_delay(0.05, 0.02)
                        kb_sim.combo_release(vks)
                elif action["type"] == "click":
                    if hold > 0:
                        ms_sim.hold_click(action["x"], action["y"], hold)
                    else:
                        ms_sim.click_mouse(action["x"], action["y"])
            except: pass
            if not self._running: return False
            self._pause_aware_delay(action.get("delay", 0.5))
        return True

    def _loop(self, callback, countdown_callback=None):
        """独立任务的主循环"""
        if getattr(self, '_loop_active', False): return
        self._loop_active = True
        try:
            while self._running:
                self._pause_gate()  # 暂停中：冻结在下一轮开始前
                if not self._running: return
                # 次数限制：跑够自动停
                if self.max_runs > 0 and self.done_count >= self.max_runs:
                    self._finished_by_limit = True
                    self.stop()
                    return
                self.done_count += 1
                if not self._execute_actions(): return
                # 触发依赖此任务的其他任务
                for dep_task in self._dependents:
                    if dep_task._running:
                        threading.Thread(target=dep_task._run_once, daemon=True).start()
                # 循环倒计时显示（暂停时秒数冻结，继续后接着倒数）
                countdown_secs = int(self.loop_interval)
                if countdown_secs >= 1:
                    i = countdown_secs
                    while i >= 1:
                        if not self._running: return
                        self._pause_gate()  # 暂停中：冻结在当前秒
                        if not self._running: return
                        if self._countdown_callback:
                            try:
                                self._countdown_callback(f"● 等待 {i}s...", "#facc15")
                            except Exception as e:
                                from logger import log_error
                                log_error("task_countdown", e)
                        self._pause_aware_delay(1)
                        if not self._running: return
                        if not self._paused:  # 暂停期间秒数不前进
                            i -= 1
                    if not self._running: return
                    try:
                        countdown_callback("● 执行中...", "#4ade80")
                    except Exception as e:
                        from logger import log_error
                        log_error("task_countdown_exec", e)
                    remainder = self.loop_interval - countdown_secs
                    if remainder > 0.05:
                        self._pause_aware_delay(remainder)
                else:
                    self._pause_aware_delay(self.loop_interval)
        except Exception as e:
            from logger import log_error
            log_error("task_loop", e)
        finally:
            self._loop_active = False

    def _run_once(self):
        """被依赖触发时执行一次"""
        if not self._running: return
        try:
            if self.loop_interval > 0:
                i = int(self.loop_interval)
                while i >= 1:
                    if not self._running: return
                    self._pause_gate()  # 暂停中：冻结在当前秒
                    if not self._running: return
                    if self._countdown_callback:
                        try:
                            self._countdown_callback(f"● 等待 {i}s...", "#facc15")
                        except Exception as e:
                            from logger import log_error
                            log_error("run_once_cd", e)
                    self._pause_aware_delay(1)
                    if not self._running: return
                    if not self._paused:  # 暂停期间秒数不前进
                        i -= 1
                if not self._running: return
                if self._countdown_callback:
                    try:
                        self._countdown_callback("● 执行中...", "#4ade80")
                    except Exception as e:
                        from logger import log_error
                        log_error("run_once_exec", e)
            if not self._running: return
            # 次数限制：跑够自动停
            if self.max_runs > 0 and self.done_count >= self.max_runs:
                self._finished_by_limit = True
                self.stop()
                return
            self.done_count += 1
            self._execute_actions()
            if self.max_runs > 0 and self.done_count >= self.max_runs:
                self._finished_by_limit = True
                self.stop()
                return
            if self._callback: self._callback()
        except Exception as e:
            from logger import log_error
            log_error("run_once", e)
