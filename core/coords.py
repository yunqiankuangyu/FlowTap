"""
坐标统一关口 —— 全项目做屏幕坐标换算的唯一入口。

FlowTap 里同时存在三套坐标系，任何跨体系操作都必须经过本模块，不要在各处自己算：

  1. Qt 逻辑坐标    Qt 鼠标事件 / globalPosition() / 控件 geometry 给出的值
                    （150% 缩放下 逻辑 = 物理 / 1.5）
  2. Win32 物理坐标 GetCursorPos / GetSystemMetrics / ClientToScreen / SetCursorPos 给出的值
  3. 图像像素坐标    ImageGrab 截图 / cv2.matchTemplate 用的值 —— 与物理坐标同一体系

换算关系（本机实测 150% 缩放：物理 2560x1440，逻辑 1707x960，dpr=1.5）：
    物理 = 逻辑 x dpr

新增功能若需要"框选区域 → 截屏匹配/OCR"，一律走 qt_rect_to_phys_bbox()；
不要在业务代码里再写 devicePixelRatio() 转换（历史遗留点见文件末尾"待重构"，只增不改）。
"""
import ctypes

# ── 进程 DPI 感知 ──
# 未声明 DPI 感知时 Windows 会给出被系统缩放过的假分辨率，所有坐标全废。
# 产品由 main.py 启动时调用一次；测试脚本需自行调用本函数。
_aware_set = False


def ensure_dpi_aware():
    """声明进程 DPI 感知（幂等）。产品主程序与独立测试脚本都应在最早期调用一次"""
    global _aware_set
    if _aware_set:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    _aware_set = True


# ── 物理屏尺寸 ──
def phys_screen_size():
    """物理分辨率 (宽, 高)。GetSystemMetrics 在本进程 DPI 感知后返回物理像素"""
    u32 = ctypes.windll.user32
    return u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)


def system_dpr():
    """系统缩放比（物理 / 逻辑）。150% 缩放返回 1.5。
    用于没有 QWidget 可问设备像素比的场合（如纯 Win32 路径的换算）"""
    u32 = ctypes.windll.user32
    return u32.GetDpiForSystem() / 96.0


# ── Qt 逻辑 → 物理 ──
def qt_rect_to_phys_bbox(rect, dpr):
    """Qt 逻辑矩形 → ImageGrab 可用的物理 bbox=(x0, y0, x1, y1)。

    ImageGrab 按物理像素取景，Qt 鼠标矩形是逻辑坐标，必须 x dpr；
    不换算会截到左上方错位且偏小的区域（150% 缩放下尤其明显）。

    rect: QRect（逻辑坐标）；dpr: 该矩形所在屏的设备像素比
    dpr 应由调用方在窗口隐藏前取得（窗口隐藏后 screen() 可能回落到主屏）。
    """
    return (int(round(rect.left() * dpr)), int(round(rect.top() * dpr)),
            int(round((rect.left() + rect.width()) * dpr)),
            int(round((rect.top() + rect.height()) * dpr)))


def qt_to_phys_point(x, y, dpr):
    """Qt 逻辑点 → 物理点"""
    return int(round(x * dpr)), int(round(y * dpr))


def phys_to_qt_point(x, y, dpr):
    """物理点 → Qt 逻辑点"""
    return int(round(x / dpr)), int(round(y / dpr))


# ── 界面宽度约束 ──
# 无边框窗口用 setFixedSize 锁死宽度, 但 QScrollArea.setWidgetResizable(True) 会把内部widget
# 撑到视口宽; 反过来内部内容的最小宽度需求(不换行的 QLabel、过宽的输入框/按钮)会把滚动区一起
# 撑宽, 表现为内容溢出窗口右边界、圆角被撑成方角。
# 关口只设在 QScrollArea 这一层: 视口收窄后 Qt 自动重排内部内容, 已足够防溢出。
# 不要再去限内部容器(会凭空扣掉一段宽度, 右侧多出空白), 更不能用 setFixedWidth(锁死尺寸策略)。

def clamp_scroll_area(scroll, window_width):
    """给 QScrollArea 设宽度上限, 防止内容把滚动区撑宽并溢出窗口。

    这是界面防超宽的唯一关口: QScrollArea.setWidgetResizable(True) 下滚动区宽度跟随内部widget,
    内部内容宽度需求偏大时滚动区会被一起撑宽(实测可到640px), 表现为内容溢出窗口右边界。

    **只限滚动区这一层, 不要再去限内部容器**: 视口收窄后 Qt 会自动重排内部内容(长文字自己换行),
    已足够防溢出。反过来给内部容器设上限会凭空扣掉一段(容器自身的布局边距本就在其内部计算),
    表现为右侧多出一条空白。setFixedWidth 更不能用——它锁死尺寸策略会让内部卡片高度自适应失效。
    """
    if scroll is None:
        return None
    w = max(80, int(window_width))
    try:
        scroll.setMaximumWidth(w)
        viewport = scroll.viewport()
        if viewport is not None:
            viewport.setMaximumWidth(w)
    except Exception:
        return None
    return w


# ── 启动自检 ──
def probe_dpi_report():
    """采集当前坐标体系实况，返回可直接打印的字符串。
    产品启动时写一次 runtime.log，缩放相关问题一眼可见，不必现场排查"""
    ensure_dpi_aware()
    sw, sh = phys_screen_size()
    dpr = system_dpr()
    lines = [
        "── 坐标体系自检 ──",
        f"  进程 DPI 感知: {'已声明' if _aware_set else '未声明'}",
        f"  物理分辨率  : {sw} x {sh}",
        f"  系统缩放比  : {dpr:g}  ({dpr * 100:.0f}%)",
        f"  逻辑分辨率  : {int(sw / dpr)} x {int(sh / dpr)} (估算值)",
    ]
    return "\n".join(lines)
