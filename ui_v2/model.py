"""
新 UI 的运行时数据模型 —— 交互全靠它

之前的问题是: 界面全是死的静态控件, 因为没有模型可写。
这里把"任务 / 动作 / 分支"做成纯数据, 界面只读它并按变化重建,
所以增删改查都是真操作, 不是摆设。
"""
import copy


def load_delay():
    """默认后延 —— 走设置里的 default_delay(默认值只在 config.DEFAULTS 一处)"""
    try:
        from config import get_setting
        return float(get_setting("default_delay"))
    except Exception:
        return 0.5


def _vk_name(vk):
    """键码 -> 显示名。

    vk_map 的 VK_NAME 只覆盖到 F12, 录到 F13~F24(或 VK 表外的键)会查不到 ——
    这时给可读的字母形式, 而不是退回 K: 退回 K 会把录到的键写成完全不相干的
    另一个键, 属于录错数据。
    """
    try:
        from core.vk_map import VK_NAME
        name = VK_NAME.get(vk)
        if name:
            return name
    except Exception:
        pass
    if 0x7C <= vk <= 0x87:                  # F13 ~ F24
        return f"F{vk - 0x7C + 13}"
    if 0x41 <= vk <= 0x5A:                  # A ~ Z
        return chr(vk)
    if 0x30 <= vk <= 0x39:                  # 0 ~ 9
        return chr(vk)
    return f"[0x{vk:02X}]"


def combo_name(vks, sep="+"):
    """组合键显示名 —— 全应用唯一拼接处(模型 name / 引擎反解 / 录制回显同源)"""
    return sep.join(_vk_name(v) for v in vks)


# 键位徽章的显示名 -> 内部标识
KEYS = ["K", "Q", "左键", "E", "R", "F", "C"]
PRESS = ["持续", "按住"]      # 键盘类动作的参数名
CLICK = ["按住"]              # 鼠标类动作的参数名


class Model:
    # 全局状态。UI 与执行器都只认这份数据
    def __init__(self):
        self.tasks = []
        self.sel_task = 0      # 左栏选中哪张卡
        self.sel_row = 0       # 中栏选中哪一行(点行右栏跟着换)
        self.running = 0       # 正在运行的任务数
        # 三栏控件由主窗注入: 选中任务/行后对方要跟着换, 得能回调过去
        self._left = self._mid = self._right = None
        self._mini = None        # 迷你窗, 任务数变了要重建 chip
        self.on_toast = lambda text: None   # 提示回调, 由主窗接管
        self.on_run_change = None           # 单卡启停回调, 由主窗接管执行器
        self.preset_name = "深渊"            # 当前预设名, 载入/保存按它落盘
        self._main_win = None               # 主窗引用(录制坐标时要让位, 见 capture)
        self._recording = None   # 键鼠录制会话句柄(键位/坐标), 再点一次可取消
        self._boxing = None      # 框选进行中的标记(模板/读数区) —— 与录制分开:
                                 # 混在一个字段里, 框选取消会永久占住它, 之后点
                                 # 键鼠录制会被误判成"正在录制"而静默取消不录
        # 这两处只是兜底, 真值来源是 settings.json(与旧版同键 default_delay)
        self.default_loop = 80
        self.default_delay = load_delay()
        self.countdown = 3
        self.reset()

    def reset(self):
        self.tasks = [
            self.new_task("任务1", [
                self.new_action("K", "持续", 0.1, load_delay()),
                self.new_action("Q", "持续", 0.1, 0.3),
                self.new_action("左键", "按住", 0.05, 0.2),
                self.new_branch(),
                self.new_action("E", "持续", 0.1, 0.8),
                self.new_action("R", "持续", 1.2, 0.4),
                self.new_action("F", "持续", 0.1, 0.6),
                self.new_action("C", "持续", 0.2, 1.0),
            ]),
            self.new_task("任务2", [self.new_action("K", "持续", 0.1, load_delay())]),
            self.new_task("任务3", [self.new_action("Q", "持续", 0.1, 0.3)]),
        ]

    # ── 构造 ──
    def new_action(self, key, hold, a, b):
        return {"kind": "key", "key": key, "hold": hold, "a": a, "b": b, "run": False}

    def new_branch(self):
        return {"kind": "branch", "name": "分支1", "wait": "图像·按钮",
                "after": "跳过", "delay": 0.5, "timeout": 10, "pick": "next", "run": False}

    def new_task(self, name, actions):
        """新任务默认值全部从 settings 读 —— 写死会让设置页改的
        「新建任务默认值」对新任务无效(设置页在改 default_loop, 这里在读写死值)"""
        from config import get_setting
        return {"name": name, "actions": actions, "rel": "独立",
                "loop": get_setting("default_loop"),
                "runs": get_setting("default_runs"), "run": False}

    # ── 增删 ──
    def add_task(self):
        n = len(self.tasks) + 1
        self.tasks.append(self.new_task(f"任务{n}", [self.new_action("K", "持续", 0.1, load_delay())]))
        self.sel_task = len(self.tasks) - 1
        return self.tasks[-1]

    def del_task(self, i):
        # 至少留一个任务: 删光后 task() 会越界, 后面每一次读取模型都崩
        if len(self.tasks) <= 1:
            return False
        self.tasks.pop(i)
        # 选中项夹回有效范围: 删掉的正好是选中项时, 旧下标会指向越界
        self.sel_task = max(0, min(self.sel_task, len(self.tasks) - 1))
        self.sel_row = 0
        return True

    def add_action(self, key="K", vk=None):
        """加一条键位动作。vk 是录制到的原始键码 —— 存下来, 否则显示名与
        键码对不上时(表外键), 转引擎动作会按显示名反查而录错键。"""
        t = self.tasks[self.sel_task]
        a = self.new_action(key, "持续", 0.1, load_delay())   # 后延读 settings
        if vk is not None:
            a["vk"] = vk
        t["actions"].append(a)
        self.sel_row = len(t["actions"]) - 1
        return a

    def add_combo(self, vks):
        """组合键 —— 录制到的多键, 引擎侧是 type=combo"""
        t = self.tasks[self.sel_task]
        a = {"kind": "combo", "vks": list(vks),
             "name": combo_name(vks),
             "a": 0.1, "b": load_delay()}
        t["actions"].append(a)
        self.sel_row = len(t["actions"]) - 1
        return a

    def add_click(self, x, y, delay=0.5, hold=0, rel=False, sx=None, sy=None):
        """坐标点击 —— 录制时已确定, 坐标与延迟一起存"""
        t = self.tasks[self.sel_task]
        a = {"kind": "key", "key": "左键", "x": x, "y": y,
             "a": hold, "b": delay, "sx": sx, "sy": sy, "rel": rel}
        t["actions"].append(a)
        self.sel_row = len(t["actions"]) - 1
        return a
        self.sel_row = len(t["actions"]) - 1
        return t["actions"][-1]

    def add_branch(self):
        t = self.tasks[self.sel_task]
        b = self.new_branch()
        b["name"] = f"分支{sum(1 for a in t['actions'] if a['kind'] == 'branch') + 1}"
        t["actions"].append(b)
        self.sel_row = len(t["actions"]) - 1
        return b

    def add_image_wait(self, tpl="", delay=0.5):
        """插入「等图像」动作 —— 与分支同属条件等待, 右栏配置等待条件

        tpl 是框选存下的模板相对路径(templates/xxx.png); 没框选时为空串,
        空模板跑起来只会等到超时, 所以 UI 上该行标记为待框选。
        注意: 等图像没有 pick 字段 —— "条件达成后往哪走"(继续/跳过/结束)
        是分支才有的概念, 等图像只表示"等到满足为止"。两者右栏页共用渲染,
        但这一张卡只对分支显示。
        """
        t = self.tasks[self.sel_task]
        w = {"kind": "wait", "name": "等图像1", "tpl": tpl, "wait": "图像·按钮",
             "after": "跳过", "delay": delay, "timeout": 30, "run": False}
        w["name"] = f"等图像{sum(1 for a in t['actions'] if a['kind'] == 'wait') + 1}"
        t["actions"].append(w)
        self.sel_row = len(t["actions"]) - 1
        return w

    def add_jump(self):
        """插入「跳转」动作 —— 跳到指定序号的动作"""
        t = self.tasks[self.sel_task]
        j = {"kind": "jump", "name": "跳转", "to": 1, "run": False}
        t["actions"].append(j)
        self.sel_row = len(t["actions"]) - 1
        return j

    def add_var_read(self, region=None, sx=None, sy=None, rel=False, delay=0.0):
        """读数 —— OCR 把画面数字写入变量

        region=[x,y,w,h] 是框选到的读数区(客户区相对坐标, rel=True 时);
        没框选时给零区域, 引擎读到空就写 0, 不中断任务。
        """
        t = self.tasks[self.sel_task]
        v = self._next_var(t)
        a = {"kind": "read", "name": f"读数 → {v}", "var": v,
             "region": list(region or [0, 0, 0, 0]), "sx": sx, "sy": sy,
             "rel": rel, "b": delay, "src": "数字·计数", "run": False}
        t["actions"].append(a)
        self.sel_row = len(t["actions"]) - 1
        return a

    def add_var_set(self):
        """变量运算 —— 对变量做 + - * / = 的赋值"""
        t = self.tasks[self.sel_task]
        v = self._next_var(t)
        a = {"kind": "varset", "name": f"{v} 运算", "var": v,
             "op": "+", "val": 0, "run": False}
        t["actions"].append(a)
        self.sel_row = len(t["actions"]) - 1
        return a

    def add_cond_branch(self):
        """条件分支 —— 按变量数值走/不走"""
        t = self.tasks[self.sel_task]
        v = self._next_var(t)
        a = {"kind": "cond", "name": f"条件 {v}", "var": v,
             "cmp": ">=", "val": 0, "then": "继续", "else": "跳过", "run": False}
        t["actions"].append(a)
        self.sel_row = len(t["actions"]) - 1
        return a

    def _next_var(self, t):
        """下一个可用变量名(v1 / v2 / ...)"""
        used = {a.get("var") for a in t["actions"] if a.get("var")}
        n = 1
        while f"v{n}" in used:
            n += 1
        return f"v{n}"

    def del_row(self, i):
        t = self.tasks[self.sel_task]
        t["actions"].pop(i)
        self.sel_row = max(0, min(self.sel_row, len(t["actions"]) - 1))

    def clear_rows(self):
        # 清空动作行: 留一条空的, 否则任务里什么都没有没法继续加
        t = self.tasks[self.sel_task]
        t["actions"] = [self.new_action("K", "持续", 0.1, load_delay())]
        self.sel_row = 0

    def row(self, i):
        acts = self.task()["actions"]
        return acts[i] if 0 <= i < len(acts) else None

    def refresh(self, panes=("left", "mid", "right"), mini=True):
        """三栏与迷你窗重建的唯一入口 —— panes 传要刷的栏, mini=False 跳过迷你窗。

        Model 允许在无界面的场景下被操作(测试、批量读预设), 那时各栏都是 None,
        直接写 m._mid.rebuild(m) 会 AttributeError —— 所以调用点一律走这里,
        别再手写 rebuild 组合(手写组合还容易漏栏)。
        """
        for name in panes:
            pane = getattr(self, "_" + name, None)
            if pane is not None and hasattr(pane, "rebuild"):
                pane.rebuild(self)
        if mini and self._mini is not None:
            self._mini.rebuild()

    def task(self):
        # 越界时回退到第一项: 删任务后 sel_task 可能短暂越界,
        # 直接索引会抛 IndexError 把整个界面带崩
        if not self.tasks:
            self.tasks = [self.new_task("任务1", [self.new_action("K", "持续", 0.1, load_delay())])]
        self.sel_task = max(0, min(self.sel_task, len(self.tasks) - 1))
        return self.tasks[self.sel_task]

    # ── 启停 ──
    def toggle_all(self):
        run = (self.running == 0)            # 只要没全停就先全停
        for t in self.tasks:
            t["run"] = run
            for a in t["actions"]:
                a["run"] = run
        self.running = len(self.tasks) if run else 0
        return run

    def toggle_one(self, i):
        t = self.tasks[i]
        t["run"] = not t["run"]
        for a in t["actions"]:
            a["run"] = t["run"]
        self.running = sum(1 for x in self.tasks if x["run"])
        return t["run"]

    def copy_all(self):
        # 供预设存/取用
        return copy.deepcopy({"tasks": self.tasks, "sel": self.sel_task})

    def load_all(self, blob):
        self.tasks = copy.deepcopy(blob["tasks"])
        self.sel_task = max(0, min(blob.get("sel", 0), len(self.tasks) - 1))
        self.running = 0
