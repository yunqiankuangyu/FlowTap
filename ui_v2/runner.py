"""
执行器接线 —— 把 Model 的动作表交给 tasks.keyboard 执行

分工:
  Model    新 UI 的界面数据(kind + 简化字段)
  Runner   一次性把 Model 动作转成引擎动作, 管 KeyboardTask 的启停与状态回写

引擎是旧 UI 同一套(tasks/keyboard/keyboard_task.py), 不复制: 那是业务执行层,
不是 UI 组件。隔离的对象是界面代码(ui/), 改界面不应该动执行逻辑, 反之亦然 ——
两边各自独立演进。

转换里两处必须注意的形状差异:
  1. 引擎跳转用 lid(动作稳定标识)定位目标, 不是下标 —— 所以转换前先给每行发号,
     再按 Model 的序号换算成 lid。
  2. Model 的数值字段叫 a/b/val, 引擎叫 delay/hold/value, 键位叫 key(显示名),
     引擎要 vk(键码)。名字不同, 不能直接塞。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer

from core.vk_map import VK_MAP
from .model import _vk_name, combo_name      # 键名/组合名只在 model 一份(hotkey.hk_name 同源)
from tasks.keyboard.keyboard_task import (
    KeyboardTask, TaskStatus,
    make_key_action, make_combo_action, make_click_action, make_wait_image_action,
    make_branch_action, make_jump_action, make_ocr_read_action,
    make_var_set_action, make_cond_branch_action,
)

# Model 的 kind -> 引擎 action["type"]
_KIND_TYPE = {"key": "key", "wait": "wait_image", "branch": "branch",
              "jump": "jump", "read": "ocr_read", "varset": "var_set",
              "cond": "cond_branch"}

# 超时后 -> 引擎 on_timeout
_AFTER = {"跳过": "skip", "跳卡": "skip_card", "中止": "stop"}


def _new_lid():
    import uuid
    return uuid.uuid4().hex[:6]


def _vk(key):
    """显示名(K/Q/E/左键) -> 键码。认不出的键用 F24 占位, 不让整条任务崩。"""
    return VK_MAP.get(key.lower(), VK_MAP.get(key, 0x87))


def to_engine(actions):
    """Model 动作列表 -> 引擎动作列表(按 Model 下标补 lid, 供跳转定位)"""
    lids = [_new_lid() for _ in actions]
    out = []
    for i, a in enumerate(actions):
        k = a["kind"]
        if k == "combo":
            # 录制到的多键组合, 引擎要 vks(键码列表)与按住/后延
            act = make_combo_action([int(v) for v in a["vks"]],
                                    delay=a.get("b", 0.5), hold=a.get("a", 0))
        elif k == "key":
            # 点击键型(左键)转 click, 其余转 key; Model 的 a=持续 b=后延
            if a.get("key") == "左键":
                # 坐标来自录制(capture_click); 没录过就给 (0,0), 引擎不接受缺字段
                act = make_click_action(a.get("x", 0), a.get("y", 0),
                                        delay=a.get("b", 0.5),
                                        hold=a.get("a", 0))
            else:
                # 优先用录制时存的 vk(表外键显示名反查不到), 再退回按名查
                vk = a.get("vk") or _vk(a["key"])
                act = make_key_action(vk, delay=a.get("b", 0.5),
                                      hold=a.get("a", 0))
        elif k == "wait":
            act = make_wait_image_action(
                a.get("tpl", ""), timeout=a.get("timeout", 30),
                on_timeout=_AFTER.get(a.get("after", "跳过"), "skip"),
                delay=a.get("delay", 0))
        elif k == "branch":
            # 分支的模板选项由预设配置; 这里给空 options = 没有可命中模板,
            # 引擎按 on_timeout 走, 不会崩
            act = make_branch_action([], timeout=a.get("timeout", 30),
                                     on_timeout=_AFTER.get(a.get("after", "跳过"), "skip"),
                                     delay=a.get("delay", 0))
        elif k == "jump":
            # 引擎要 lid, Model 存的是序号 -> 换算(越界退化成"顺序继续")
            tgt = lids[a["to"] - 1] if 1 <= a.get("to", 1) <= len(lids) else None
            act = make_jump_action(tgt, delay=a.get("delay", 0))
        elif k == "read":
            # region 是客户区区域; 尚未录制时给零区域, 引擎读到空 -> 写0不中断
            act = make_ocr_read_action(a.get("region", [0, 0, 0, 0]), a["var"],
                                       delay=a.get("delay", 0))
        elif k == "varset":
            act = make_var_set_action(a["var"], a.get("op", "+"), a.get("val", 0),
                                      delay=a.get("delay", 0))
        else:      # cond
            # Model 的 then/else 是界面占位语义, 引擎要"成立时跳哪的 lid"。
            # 目标没配就传 None(顺序继续), 与旧版 target=None 同义
            act = make_cond_branch_action(a["var"], a.get("cmp", ">="),
                                          a.get("val", 0), None,
                                          delay=a.get("delay", 0))
        act["lid"] = lids[i]          # 用发号替换掉构造函数新发的, 保持表内一致
        out.append(act)
    return out


def from_engine(act, by_lid=None):
    """引擎动作 -> Model 动作 (to_engine 的反向, 用于读旧预设)

    预设存盘用的是引擎格式(旧 UI 的原样), 新 UI 要能直接读那份文件 ——
    所以必须有反向转换。by_lid 是 lid -> 下标映射, jump/cond 的跳转目标是 lid,
    反向要换回 Model 存的序号; 没传就先落 None, 由调用方二次回填。
    """
    t = act.get("type")
    if t in ("key", "click"):
        if t == "click":
            return {"kind": "key", "key": "左键", "x": act.get("x", 0),
                    "y": act.get("y", 0), "a": act.get("hold", 0),
                    "b": act.get("delay", 0.5), "sx": act.get("sx"),
                    "sy": act.get("sy"), "rel": act.get("rel", False)}
        return {"kind": "key", "key": _vk_name(act.get("vk")),
                "vk": act.get("vk"),
                "a": act.get("hold", 0), "b": act.get("delay", 0.5)}
    if t == "combo":
        return {"kind": "combo", "vks": list(act.get("vks", [])),
                "name": combo_name(act.get("vks", [])),
                "a": act.get("hold", 0), "b": act.get("delay", 0.5)}
    if t == "wait_image":
        return {"kind": "wait", "name": "等图像1", "tpl": act.get("tpl", ""),
                "wait": "图像·按钮", "after": _AFTER_REV.get(
                    act.get("on_timeout", "skip"), "跳过"),
                "delay": act.get("delay", 0.0), "timeout": act.get("timeout", 30),
                "run": False}
    if t == "branch":
        return {"kind": "branch", "name": "分支1",
                "options": act.get("options", []),
                "wait": "图像·按钮",
                "after": _AFTER_REV.get(act.get("on_timeout", "next"), "跳过"),
                "delay": act.get("delay", 0.0), "timeout": act.get("timeout", 30),
                "pick": "next", "run": False}
    if t == "jump":
        return {"kind": "jump", "name": "跳转", "to": None,
                "_lid": act.get("target"), "delay": act.get("delay", 0.0),
                "run": False}
    if t == "ocr_read":
        return {"kind": "read", "var": act.get("var", "v1"),
                "name": f"读数 → {act.get('var', 'v1')}",
                "region": list(act.get("region", [0, 0, 0, 0])),
                "src": "数字·数值", "delay": act.get("delay", 0.0), "run": False}
    if t == "var_set":
        return {"kind": "varset", "var": act.get("var", "v1"),
                "name": f"{act.get('var', 'v1')} 运算",
                "op": act.get("op", "+"), "val": act.get("value", 0),
                "delay": act.get("delay", 0.0), "run": False}
    if t == "cond_branch":
        return {"kind": "cond", "var": act.get("var", "v1"),
                "name": f"条件 {act.get('var', 'v1')}",
                "cmp": act.get("cmp", ">="), "val": act.get("value", 0),
                "then": "then", "else": "else", "run": False}
    return {"kind": "key", "key": "K", "a": 0, "b": 0.5}   # 认不出就退化成空键


_AFTER_REV = {"skip": "跳过", "skip_card": "跳卡", "stop": "中止",
              "next": "跳过"}


def from_engine_all(task):
    """引擎任务 -> Model 任务: 先转全部, 再把 lid 目标回填成序号"""
    import copy
    acts = [from_engine(a) for a in task.get("actions", [])]
    lids = [a.get("lid") for a in task.get("actions", [])]
    lid2idx = {l: i + 1 for i, l in enumerate(lids) if l}   # 序号从 1 起
    for m, a in zip(acts, task.get("actions", [])):
        if m["kind"] == "jump":
            m["to"] = lid2idx.get(a.get("target"), 1)
        elif m["kind"] == "cond":
            m["_then_lid"] = a.get("target")
    out = copy.deepcopy(task)
    out["actions"] = acts
    out.setdefault("rel", "独立")
    out.setdefault("loop", 5)
    out.setdefault("runs", 0)
    out["run"] = False
    return out


class Runner:
    """管理一个 Model 的全部 KeyboardTask 实例, 负责启停与状态回写

    每次启停都重建任务: Model 是可变界面数据, 任务跑在另一个线程里,
    用同一份 dict 会让编辑与执行互相踩(引擎会读 self.actions 的实时长度)。
    重建代价是一次序列化, 换来的是"编辑中点停止也不会崩"。
    """

    def __init__(self, m, on_status=None):
        self.m = m
        self.on_status = on_status or (lambda *a: None)
        self._tasks = {}
        self._pending = {}      # 倒计时中的任务: {下标: (计时器, 任务)}

    def _build(self, t, i):
        """Model 任务 -> 引擎任务"""
        rel = t.get("rel", "独立")
        # "在任务N后" -> 前置任务的位置索引(与旧版 dependency_task_id 同语义:
        # 存的是索引不是 task_id, 见 ui/keyboard_mode.py:750 的 text[2:-1]-1)。
        # 格式必须整串匹配: 只抓数字会把 "任务1后"(少个"在"字)当成有效依赖,
        # 于是 dep 有值、relation_type 却是引擎不认识的字面, 行为不可预期。
        dep = None
        if rel != "独立":
            import re as _re
            mm = _re.fullmatch(r"在任务(\d+)后", rel)
            if mm:
                n = int(mm.group(1)) - 1
                # 前置不能是自己, 也不能越界
                if 0 <= n < len(self.m.tasks) and n != i:
                    dep = n
            if dep is None:
                rel = "独立"      # 格式不对/越界/依赖自己 -> 当独立, 别进 WAITING 卡死
        kw = dict(
            task_id=i,
            name=t["name"],
            actions=to_engine(t["actions"]),
            loop_interval=t.get("loop", 5),
            relation_type=rel,
            dependency_task_id=dep,
            max_runs=t.get("runs", 0),
        )
        try:
            return KeyboardTask(**kw)
        except TypeError:
            # 关键字与当前引擎签名对不上(引擎字段有增删)时降级成位置参数
            return KeyboardTask(kw["task_id"], kw["name"], kw["actions"],
                                kw["loop_interval"])

    # 启动倒计时秒数: 与旧版同键(start_countdown), 点开始先倒数再跑
    @staticmethod
    def countdown_seconds():
        try:
            from config import get_setting
            return int(get_setting("start_countdown"))
        except Exception:
            return 3

    def _link_deps(self, idx):
        """给 idx 任务找依赖它的下游, 挂上 _dependents"""
        me = self._tasks.get(idx)
        if me is None:
            return
        for j, t in enumerate(self.m.tasks):
            if j == idx:
                continue
            rel = t.get("rel", "独立")
            if rel == "独立":
                continue
            import re as _re
            mm = _re.fullmatch(r"在任务(\d+)后", rel)
            if mm and int(mm.group(1)) - 1 == idx:
                other = self._tasks.get(j)
                if other is not None and other not in me._dependents:
                    me._dependents.append(other)

    def start(self, i, with_countdown=True):
        """启动单个任务。返回 1=成功 0=失败

        先倒计时再起线程 —— 直接起会让"点开始"的一瞬间键盘就被占用,
        用户来不及移开光标。倒计时的秒数走 settings 的 start_countdown
        (与旧版同一键), 倒数过程经 on_status("cd", ...) 上报给界面。
        """
        self.stop(i)
        t = self.m.tasks[i]
        task = self._build(t, i)
        self._tasks[i] = task
        self._link_deps(i)          # 单启也要接上链(下游已建的话)
        n = self.countdown_seconds() if with_countdown else 0
        if n <= 0:
            return self._really_start(i, task, t)
        return self._cd(i, task, t, n)

    def _cd(self, i, task, t, count):
        """倒计时: 每秒上报一次, 归零才真正起线程"""
        if count > 0:
            _timer = QTimer()
            _timer.setSingleShot(True)
            self._pending[i] = (_timer, task)
            self.on_status("cd", i, f"● 准备中 {count}...")

            def _next():
                # 倒数期间被 stop 或换任务就别再继续, 否则会多起一个线程
                if self._tasks.get(i) is task:
                    self._cd(i, task, t, count - 1)
            _timer.timeout.connect(_next)
            _timer.start(1000)
            return 1
        self._pending.pop(i, None)
        return self._really_start(i, task, t)

    def _really_start(self, i, task, t):
        """真正启动线程, 并把引擎的两个回调接到 on_status 上"""
        try:
            task.start(callback=lambda: self.on_status("round", i),
                       countdown_callback=lambda text, color="":
                       self.on_status("stat", i, text, color))
        except Exception as e:
            self.on_status("error", f"{t['name']} 启动失败: {e}")
            return 0
        return 1

    def stop(self, i):
        """停止单个任务 —— 倒计时中的也一并取消, 否则停不下来"""
        pend = self._pending.pop(i, None)
        if pend:
            pend[0].stop()
        t = self._tasks.pop(i, None)
        if t is not None:
            try:
                t.stop()
            except Exception:
                pass

    def start_all(self, with_countdown=True):
        """按当前 Model 启动所有任务, 返回预计启动条数

        全开统一倒数一次(不是每个任务各倒各的) —— 那样会交错出现
        "任务1准备中3"「任务2准备中2」这种噪声。
        """
        self.stop_all()
        built = []
        for i, t in enumerate(self.m.tasks):
            task = self._build(t, i)
            self._tasks[i] = task
            built.append((i, task, t))
        n = len(built)
        if not n:
            return 0
        # 挂依赖链: 引擎靠 _dependents 通知"我跑完了, 你(依赖我的)可以开始",
        # 不挂的话 relation_type != 独立 的任务停在 WAITING 等不到通知。
        for i, task, t in built:
            dep = getattr(task, "dependency_task_id", None)
            if dep is not None and dep in self._tasks:
                self._tasks[dep]._dependents.append(task)
        secs = self.countdown_seconds() if with_countdown else 0
        if secs <= 0:
            for i, task, t in built:
                self._really_start(i, task, t)
            return n
        self._cd_group(built, secs)
        return n

    def _cd_group(self, built, count):
        """统一倒数: 每秒上报一次, 归零起全部线程

        顺序要紧: 先登记 pending 再上报 —— 界面收到 "cd_all" 会立刻读
        _pending 刷新播放键, 反过来读到空表, 倒计时就不显示在按钮上。
        """
        if count > 0:
            tmr = QTimer()
            tmr.setSingleShot(True)

            def nxt():
                # 倒数期间被 stop_all 清空就不再继续(否则会多起一轮)
                if self._tasks and all(self._tasks.get(i) is task
                                       for i, task, _ in built):
                    self._cd_group(built, count - 1)
                else:
                    self._pending.pop(-1, None)
            tmr.timeout.connect(nxt)
            self._pending[-1] = (tmr, None)   # -1 = 全局倒计时, 非单任务
            tmr.start(1000)
            self.on_status("cd_all", -1, f"● 准备中 {count}...")
            return
        self._pending.pop(-1, None)
        for i, task, t in built:
            self._really_start(i, task, t)

    def stop_all(self):
        for _, (tmr, _t) in list(self._pending.items()):
            tmr.stop()
        self._pending.clear()
        for task in self._tasks.values():
            try:
                task.stop()
            except Exception:
                pass
        self._tasks.clear()

    def _cb(self, *a):
        # 引擎回调形态随状态而变, 只在有参数时透传
        if a:
            self.on_status("tick", a[0])

    @property
    def running(self):
        return sum(1 for t in self._tasks.values() if t._running)
