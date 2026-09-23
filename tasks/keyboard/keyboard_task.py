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


def _new_lid():
    """动作稳定标识：预设序列化往返保留；branch/jump 按 lid 定位跳转目标"""
    import uuid
    return uuid.uuid4().hex[:6]


def make_key_action(vk, delay=0.5, hold=0):
    """创建键盘动作"""
    return {"type": "key", "vk": vk, "delay": delay, "hold": hold, "lid": _new_lid()}


def make_combo_action(vks, delay=0.5, hold=0):
    """创建组合键动作（多个键同时按住）"""
    return {"type": "combo", "vks": list(vks), "delay": delay, "hold": hold, "lid": _new_lid()}


def make_click_action(x, y, delay=0.5, hold=0):
    """创建鼠标点击动作"""
    return {"type": "click", "x": x, "y": y, "delay": delay, "hold": hold, "lid": _new_lid()}


def make_wait_image_action(tpl, threshold=0.85, timeout=30, on_timeout="skip", delay=0.0,
                           min_hits=2, scales=(1.0, 1.25, 1.5)):
    """创建等待图像动作（画面稳定出现目标模板才继续）
    tpl 模板相对路径，threshold 匹配阈值，timeout 超时秒(0=无限等)
    on_timeout 超时行为 skip=跳过继续 stop=中止本轮
    min_hits 防抖帧数（连续命中这么多次才判定出现，防闪烁误判）
    scales 模板缩放系数序列（多尺度匹配，按序尝试命中即停）
    """
    return {"type": "wait_image", "tpl": tpl, "threshold": threshold,
            "timeout": timeout, "on_timeout": on_timeout, "delay": delay,
            "min_hits": min_hits, "scales": list(scales), "lid": _new_lid()}


def _ensure_lids(actions):
    """为缺 lid 的旧动作补发（幂等：已有 lid 不动）；返回原列表"""
    for a in actions:
        if isinstance(a, dict) and not a.get("lid"):
            a["lid"] = _new_lid()
    return actions


def make_branch_action(options, timeout=30, on_timeout="next", delay=0.0):
    """创建多模板分支动作：options 列表顺序=优先级，逐项稳定命中即跳其 target
    option 字段 {tpl, threshold, scales, min_hits, target}；target=目标lid，None=顺序继续
    on_timeout: next=顺序继续 / stop=中止本轮"""
    return {"type": "branch", "options": list(options), "timeout": timeout,
            "on_timeout": on_timeout, "delay": delay, "lid": _new_lid()}


def make_jump_action(target=None, delay=0.0):
    """创建跳转动作：target=目标动作lid；None 或目标不存在=顺序继续"""
    return {"type": "jump", "target": target, "delay": delay, "lid": _new_lid()}


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
    elif action["type"] == "wait_image":
        return f"📷 等图像≥{action.get('threshold', 0.85):.2f}"
    elif action["type"] == "branch":
        return f"🔀 分支×{len(action.get('options') or [])}"
    elif action["type"] == "jump":
        return "→ 跳转"
    return "?"


def _foreground_hwnd():
    """当前前台窗口句柄（测试可替换）"""
    import ctypes
    return ctypes.windll.user32.GetForegroundWindow()


def resolve_click_pos(action):
    """得出点击动作执行时的绝对屏幕坐标。
    rel=True（绑定时录制的客户区坐标）→ 换算到当前目标窗口，窗口拖走仍点得准；
    运行时未绑定或取不到窗口 → 用录制瞬间的绝对快照 sx/sy 兜底；
    非 rel 动作原坐标直通（旧预设零影响）"""
    if not action.get("rel"):
        return action["x"], action["y"]
    try:
        from core.window_gate import get_bound_process
        from core import vision
        if get_bound_process():
            bbox = vision.client_area_bbox(_foreground_hwnd())
            if bbox:
                return bbox[0] + action["x"], bbox[1] + action["y"]
        from logger import log_info
        log_info("click_rel_fallback",
                 f"bound={get_bound_process()!r} snap=({action.get('sx')}, {action.get('sy')})")
        return action.get("sx", action["x"]), action.get("sy", action["y"])
    except Exception:
        return action.get("sx", action["x"]), action.get("sy", action["y"])


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
    _collapsed: bool = False  # 卡片是否收起
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

    def _window_gate(self):
        """窗口绑定闸门：绑定进程不在前台则原地等待（不注入不计数）；未绑定恒放行
        返回 False=任务已停止"""
        from core.window_gate import get_bound_process, is_target_foreground
        name = get_bound_process()
        if not name:
            return True
        shown = None
        while self._running:
            if is_target_foreground():
                if shown and self._countdown_callback:
                    try: self._countdown_callback("● 执行中...", "#4ade80")
                    except Exception: pass
                return True
            if shown != name and self._countdown_callback:
                shown = name
                try: self._countdown_callback("● 等待窗口...", "#facc15")
                except Exception: pass
            time.sleep(0.2)
        return False

    def _wait_for_image(self, action):
        """等待目标图像稳定出现在画面中（防抖、可暂停、受窗口闸门约束）
        返回 True=已出现/超时跳过，False=任务停止或超时中止本轮"""
        from core import vision
        from logger import log_info
        rel = action.get("tpl", "")
        threshold = float(action.get("threshold", 0.85))
        timeout = float(action.get("timeout", 30))
        min_hits = max(1, int(action.get("min_hits", 2)))
        # 旧预设无 scales 字段 → 多尺度默认开
        scales = tuple(action.get("scales") or (1.0, 1.25, 1.5))
        waited = 0.0  # 只累计真实等待秒，暂停/等窗口时间不计入
        streak = 0        # 连续命中帧数（防抖计数）
        best = -1.0       # 本次等待见过的最高分（超时回查用）
        last_sample = 0.0 # 上次采样结束时刻（断层检测）
        while self._running:
            self._pause_gate()
            if not self._running: return False
            if not self._window_gate(): return False
            # 采样断层检测：距上次采样结束 >1s（暂停/等窗口阻塞过），streak 作废重计
            t_start = time.monotonic()
            if t_start - last_sample > 1.0:
                streak = 0
            try:
                found, score = vision.match_once(rel, threshold, scales=scales)
            except Exception as e:
                from logger import log_error
                log_error("wait_image_match", e)
                found, score = False, -1.0
            last_sample = time.monotonic()
            if score > best:
                best = score
            if found:
                streak += 1
                if streak >= min_hits:
                    log_info("wait_image_hit",
                             f"score={score:.3f} th={threshold} hits={streak} tpl={rel}")
                    if self._countdown_callback:
                        try: self._countdown_callback("● 执行中...", "#4ade80")
                        except Exception: pass
                    return True
            else:
                streak = 0
            if timeout > 0 and waited >= timeout:
                log_info("wait_image_timeout",
                         f"best={best:.3f} th={threshold} min_hits={min_hits} tpl={rel}")
                if self._countdown_callback:
                    try: self._countdown_callback("● 等待图像超时，跳过...", "#facc15")
                    except Exception: pass
                return action.get("on_timeout", "skip") != "stop"
            if self._countdown_callback:
                # 每拍回显置信度：调阈值时状态行直接看得见分数
                try:
                    self._countdown_callback(
                        f"● 等待图像... {max(score, 0.0):.2f}", "#facc15")
                except Exception: pass
            t0 = time.monotonic()
            time.sleep(0.2)
            waited += time.monotonic() - t0
        return False

    def _run_branch(self, action):
        """执行多模板分支：按 options 列表顺序找首个稳定命中项，返回其 target lid。
        返回 "STOP"=中止本轮（超时stop/任务停止）；None=超时顺序继续。
        每选项独立防抖计数，采样断层(>1s)全部作废——语义与 _wait_for_image 一致"""
        from core import vision
        from logger import log_info, log_error
        options = action.get("options") or []
        if not options:
            return None
        timeout = float(action.get("timeout", 30))
        waited = 0.0
        n = len(options)
        streak = [0] * n
        best = [-1.0] * n
        last_sample = 0.0
        while self._running:
            self._pause_gate()
            if not self._running:
                return "STOP"
            if not self._window_gate():
                return "STOP"
            t_start = time.monotonic()
            if t_start - last_sample > 1.0:
                streak = [0] * n
            # 优先级=列表顺序：k0 先判，同帧多命中取最靠前者
            for k, opt in enumerate(options):
                try:
                    found, score = vision.match_once(
                        opt.get("tpl", ""),
                        float(opt.get("threshold", 0.85)),
                        scales=tuple(opt.get("scales") or (1.0, 1.25, 1.5)))
                except Exception as e:
                    log_error("branch_match", e)
                    found, score = False, -1.0
                if score > best[k]:
                    best[k] = score
                if found:
                    streak[k] += 1
                    if streak[k] >= max(1, int(opt.get("min_hits", 2))):
                        tgt = opt.get("target")
                        log_info("branch_hit",
                                 f"opt={k} score={score:.3f} hits={streak[k]} -> {tgt or 'next'}")
                        if self._countdown_callback:
                            try: self._countdown_callback("● 执行中...", "#4ade80")
                            except Exception: pass
                        return tgt
                else:
                    streak[k] = 0
            last_sample = time.monotonic()
            if timeout > 0 and waited >= timeout:
                log_info("branch_timeout", f"best={max(best):.3f} n={n}")
                if action.get("on_timeout", "next") == "stop":
                    return "STOP"
                return None
            if self._countdown_callback:
                try:
                    self._countdown_callback(
                        f"● 分支判断... {max(max(best), 0.0):.2f}", "#facc15")
                except Exception: pass
            t0 = time.monotonic()
            time.sleep(0.2)
            waited += time.monotonic() - t0
        return "STOP"

    def _index_of(self, lid):
        """按 lid 找动作下标；lid 缺失或不存在返回 None（调用方顺序继续）"""
        if not lid:
            return None
        for i, a in enumerate(self.actions):
            if a.get("lid") == lid:
                return i
        return None

    def _execute_actions(self):
        """执行一轮动作序列（索引循环：branch/jump 改写 i 实现条件跳转）"""
        from logger import log_error, log_info
        kb_sim = KeyboardSimulator()
        ms_sim = MouseSimulator()
        i = 0
        jumps = 0  # 跳转计数（每轮清零）：掐死零延迟死循环
        while i < len(self.actions):  # 每轮重取长度：运行中增删动作也能正确收尾
            if not self._running: return False
            if not self._window_gate(): return False
            action = self.actions[i]
            try:
                hold = action.get("hold", 0)
                if action["type"] == "jump":
                    tgt_i = self._index_of(action.get("target"))
                    if tgt_i is None:
                        pass  # 目标缺失/未设置 → 落到底部顺序推进
                    else:
                        jumps += 1
                        if jumps > 200:
                            log_error("jump_guard", "跳转>200次/轮，疑似死循环，中止本轮")
                            return False
                        i = tgt_i
                        continue  # 跳转不消耗 delay
                elif action["type"] == "branch":
                    r = self._run_branch(action)
                    if r == "STOP":
                        return False
                    tgt_i = self._index_of(r) if r else None
                    i = tgt_i if tgt_i is not None else i + 1
                    self._pause_aware_delay(action.get("delay", 0.0))
                    continue
                elif action["type"] == "wait_image":
                    if not self._wait_for_image(action): return False
                    if not self._running: return False
                    self._pause_aware_delay(action.get("delay", 0))
                    i += 1
                    continue
                elif action["type"] == "key":
                    if hold > 0:
                        kb_sim.hold_key(action["vk"], hold)
                    else:
                        kb_sim.tap_key(action["vk"])
                elif action["type"] == "combo":
                    vks = action["vks"]
                    if not vks:
                        i += 1
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
                    cx, cy = resolve_click_pos(action)
                    if hold > 0:
                        ms_sim.hold_click(cx, cy, hold)
                    else:
                        ms_sim.click_mouse(cx, cy)
                else:
                    # 未知类型：不抛异常也会走到这，必须显式记日志再跳过（回查要求）
                    log_info(f"action_{action.get('type', '?')}", "未知类型，跳过")
            except Exception as e:
                # 未知类型/执行异常：记日志继续（替换原裸 except: pass，回查是二期要求）
                log_error(f"action_{action.get('type', '?')}", e)
            if not self._running: return False
            self._pause_aware_delay(action.get("delay", 0.5))
            i += 1
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
                if not self._window_gate(): return  # 窗口不在前台：本轮不计数
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
            if not self._window_gate(): return  # 窗口不在前台：本轮不计数
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
