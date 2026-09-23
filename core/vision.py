"""
视觉识别引擎：屏幕截取 + 模板匹配
截取目标窗口客户区（绑定进程时）或全屏，在画面中搜索模板图像
"""
import ctypes
import ctypes.wintypes
import os
import sys
import threading

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _app_dir():
    """exe 或脚本所在目录（打包后 __file__ 在临时目录，必须用 argv[0]）"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return _BASE_DIR


TEMPLATE_DIR = os.path.join(_app_dir(), "templates")

_user32 = ctypes.windll.user32

#模板缓存 path -> 灰度图
_tpl_cache = {}
#多尺度缩放缓存 (rel_path, scale) -> 缩放后灰度模板
_scale_cache = {}
_tpl_lock = threading.Lock()


def new_template_path():
    """生成新模板的相对路径（templates/xxxx.png）"""
    import uuid
    return os.path.join("templates", uuid.uuid4().hex[:12] + ".png")


def save_template(pil_img, rel_path):
    """保存 PIL 截图为模板文件（相对 app 目录），返回绝对路径"""
    full = os.path.join(_app_dir(), rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    pil_img.save(full, format="PNG")
    with _tpl_lock:
        _tpl_cache.pop(rel_path, None)
        _purge_scales(rel_path)
    return full


def _read_gray(full_path):
    """读图转灰度（np.fromfile+imdecode，兼容中文路径）"""
    import cv2
    data = np.fromfile(full_path, dtype=np.uint8)
    if data.size == 0:
        return None
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    return img


def _load_template(rel_path):
    """加载模板（带缓存），失败返回 None"""
    if not rel_path:
        return None
    with _tpl_lock:
        cached = _tpl_cache.get(rel_path)
    if cached is not None:
        return cached
    full = os.path.join(_app_dir(), rel_path)
    if not os.path.isfile(full):
        return None
    img = _read_gray(full)
    if img is None:
        return None
    with _tpl_lock:
        _tpl_cache[rel_path] = img
    return img


def _purge_scales(rel_path):
    """清掉某个模板的全部缩放缓存（须持锁调用）"""
    for k in [k for k in _scale_cache if k[0] == rel_path]:
        _scale_cache.pop(k, None)


def invalidate_template(rel_path):
    """丢弃缓存（模板重新标定时调用）"""
    with _tpl_lock:
        _tpl_cache.pop(rel_path, None)
        _purge_scales(rel_path)


def client_area_bbox(hwnd):
    """窗口客户区的屏幕坐标 bbox（左上右下，物理像素）"""
    rect = ctypes.wintypes.RECT()
    if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    pt = ctypes.wintypes.POINT(0, 0)
    if not _user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    return (pt.x, pt.y, pt.x + rect.right, pt.y + rect.bottom)


def search_bbox():
    """当前搜索区域：绑定进程时=前台窗口客户区，未绑定=全屏"""
    from core.window_gate import get_bound_process
    if get_bound_process():
        hwnd = _user32.GetForegroundWindow()
        if hwnd:
            return client_area_bbox(hwnd)
    return None


def grab_gray(bbox=None):
    """截取指定区域（bbox=None 为全屏）返回灰度 ndarray"""
    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    return np.array(img.convert("L"))


def match_template(screen_gray, tpl_gray):
    """在画面中搜索模板，返回 (最高得分0~1, 位置xy)；模板比画面大时 (-1, None)"""
    import cv2
    if (screen_gray.shape[0] < tpl_gray.shape[0]
            or screen_gray.shape[1] < tpl_gray.shape[1]):
        return -1.0, None
    res = cv2.matchTemplate(screen_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    return float(max_val), max_loc


def _scaled_template(rel_path, tpl, scale):
    """按系数缩放模板并缓存（scale=1.0 原样返回）"""
    if scale == 1.0:
        return tpl
    key = (rel_path, scale)
    with _tpl_lock:
        cached = _scale_cache.get(key)
    if cached is None:
        import cv2
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        cached = cv2.resize(tpl, None, fx=scale, fy=scale, interpolation=interp)
        with _tpl_lock:
            _scale_cache[key] = cached
    return cached


def match_once(rel_path, threshold=0.85, scales=(1.0,)):
    """截屏并匹配一次，返回 (是否命中, 最高得分)。
    scales 为模板缩放系数序列，按序尝试，命中即停（列表顺序=优先级）。
    截屏/匹配异常向上抛，由调用方处理"""
    tpl = _load_template(rel_path)
    if tpl is None:
        return False, 0.0
    screen = grab_gray(search_bbox())
    best = -1.0
    for s in (scales or (1.0,)):
        t = _scaled_template(rel_path, tpl, s)
        if (screen.shape[0] < t.shape[0]
                or screen.shape[1] < t.shape[1]):
            continue  # 该尺度模板比画面大，跳过
        score, _ = match_template(screen, t)
        if score > best:
            best = score
        if score >= threshold:
            return True, score  # 首个达标尺度即返回
    return (best >= threshold and best >= 0), best
