"""窗口透明度统一关口。

主窗的透明度滑块只作用于主窗自己(setWindowOpacity 只影响调用它的那个窗口),
独立存在的悬浮窗/面板(编辑页、预览面板、模板原图、迷你窗)不会跟着变——
用户拖滑块时只有主窗半透明, 弹出来的面板仍是实色, 看着不是一回事。

这里集中两件事:
  apply_to(widget)  新建窗口时按当前设置设一次
  apply_all(app)    滑块变化时同步所有已存在的窗口

不纳入的窗口: 框选遮罩、预览虚线框。它们的作用就是遮住/框出目标区域,
半透明反而看不清选中哪里; 它们的半透明由 paintEvent 自己画。
"""
from config import load_settings


def current_opacity():
    """设置里的透明度(0.3~1.0), 缺失或非法时按不透明处理。"""
    try:
        v = float(load_settings().get("opacity", 0.9))
    except (TypeError, ValueError):
        return 1.0
    return v if 0.0 < v <= 1.0 else 1.0


def apply_to(widget):
    """给单个窗口套上当前透明度。

    非窗口对象(QApplication 之类)与已析构的窗口都要静默跳过: 调用方是
    "把透明度同步给所有窗口", 少一个不设不该影响其余, 更不该整体崩掉。
    """
    if widget is None:
        return
    setter = getattr(widget, "setWindowOpacity", None)
    if setter is None:
        return              # 不是窗口(如 QApplication)
    try:
        setter(current_opacity())
    except (RuntimeError, TypeError):
        pass                # C++ 侧对象已析构(面板关掉了)


# 独立顶层窗口的查找函数(模块名, 函数名)。统一调 fn(app), 找不到返回 None。
_FINDERS = (
    ("ui.mini_mode", "find_mini"),
    ("ui.action_settings_view", "find_open"),
    ("ui.vision_preview", "find_preview"),
    ("ui.vision_preview", "find_tpl_panel"),
)


def _resolve(module, finder, app):
    """取窗口对象; 模块没导入/窗口没开/查找函数不存在都返回 None, 不抛。"""
    import importlib
    try:
        m = importlib.import_module(module)
    except ImportError:
        return None
    fn = getattr(m, finder, None)
    if fn is None:
        return None
    try:
        return fn(app)
    except TypeError:
        # 查找函数不接受 app(按类名扫顶层窗的那种), 无参再试一次
        try:
            return fn()
        except Exception:
            return None
    except Exception:
        return None


def apply_all(app):
    """同步主窗 + 所有已打开的独立窗口。

    新建窗口不必自己记得设透明度——它们各自 __init__ 里调用 apply_to 即可,
    这里管的是"已经开着的那些"。
    """
    apply_to(app)
    for module, finder in _FINDERS:
        apply_to(_resolve(module, finder, app))
