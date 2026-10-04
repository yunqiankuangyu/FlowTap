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

#模板最低对比度σ, 低于视为纯色。纯色模板让TM_CCOEFF_NORMED分母0/0,
#OpenCV对任意画面恒返回~1.0(全部误报), 故标定端和匹配端双拦截。
#彩图按逐通道σ最大值判(探针实证: 恒色(10,20,30)整体std=8.16能骗过粗闸但匹配恒1.0, 单通道平无害)
MIN_TEMPLATE_STD = 2.0


def template_sigma(img):
    """纯色判定σ, 彩图取逐通道std最大值, 灰图取整体std"""
    if img.ndim == 3:
        return max(float(img[:, :, c].std()) for c in range(img.shape[2]))
    return float(img.std())
#已记过"纯色拒绝"日志的模板路径(防等待循环每0.2s刷屏)
_flat_logged = set()


def new_template_path():
    """生成新模板的相对路径（templates/xxxx.png）"""
    import uuid
    return os.path.join("templates", uuid.uuid4().hex[:12] + ".png")


# 模板配套的坐标文件: templates/xxx.png -> templates/xxx.json, 记框选时的屏幕绝对bbox
# 旧模板没有json, 自动降级为全屏搜索模式(见match_at_position)
TOLERANCE_PX = 3  # 固定位置匹配的容错半径(px): 允许目标有1-3px微偏移而不掉分


def _meta_path(rel_path):
    """模板坐标文件绝对路径(与png同名的.json)"""
    return os.path.splitext(os.path.join(_app_dir(), rel_path))[0] + ".json"


def save_template_bbox(rel_path, bbox, ref_size=None):
    """记录模板框选时的屏幕绝对bbox(左,上,右,下)与当时的画面尺寸, 供固定位置匹配使用。
    ref_size=(宽,高) 用于分辨率变化时按比例换算坐标"""
    import json
    if not rel_path or not bbox:
        return
    try:
        d = {"bbox": [int(v) for v in bbox]}
        if ref_size:
            d["ref_size"] = [int(ref_size[0]), int(ref_size[1])]
        with open(_meta_path(rel_path), "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        from logger import log_error
        import traceback
        log_error("vision_meta", traceback.format_exc())


def load_template_meta(rel_path):
    """读模板的框选元信息, 返回 (bbox, ref_size); 旧模板或损坏返回 (None, None)=走全屏搜索"""
    import json
    if not rel_path:
        return (None, None)
    try:
        p = _meta_path(rel_path)
        if not os.path.isfile(p):
            return (None, None)
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        b = d.get("bbox")
        bbox = tuple(int(v) for v in b) if b and len(b) == 4 else None
        rs = d.get("ref_size")
        ref = (int(rs[0]), int(rs[1])) if rs and len(rs) == 2 else None
        return (bbox, ref)
    except Exception:
        return (None, None)


def load_template_bbox(rel_path):
    """读模板的框选坐标; 旧模板或损坏返回 None(=走全屏搜索)"""
    return load_template_meta(rel_path)[0]


def save_template(pil_img, rel_path):
    """保存 PIL 截图为模板文件（相对 app 目录），返回绝对路径"""
    full = os.path.join(_app_dir(), rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    pil_img.save(full, format="PNG")
    with _tpl_lock:
        _tpl_cache.pop(rel_path, None)
        _purge_scales(rel_path)
    _flat_logged.discard(rel_path)  # 新存/重拍模板, 解除纯色日志抑制
    return full


def qimage_to_rgb(qimg, x, y, w, h):
    """从冻结帧QImage裁剪一块转RGB ndarray(框选取图用, 与grab_rgb同为RGB ndarray)"""
    if qimg is None or w <= 0 or h <= 0:
        return None
    try:
        sub = qimg.copy(x, y, w, h)
    except Exception:
        return None
    if sub.isNull():
        return None
    w2, h2 = sub.width(), sub.height()
    if w2 <= 0 or h2 <= 0:
        return None
    fmt = sub.format()
    fmt_v = getattr(fmt, "value", fmt)
    # QImage.Format: RGB888=13 / ARGB32=4 / ARGB32_Premultiplied=5 / Grayscale8=24
    nch = {13: 3, 3: 3, 4: 4, 5: 4, 6: 4, 24: 1}.get(fmt_v, 4)
    row = sub.bytesPerLine()
    if row < w2 * nch:
        return None
    arr = np.frombuffer(sub.constBits(), dtype=np.uint8,
                        count=row * h2).reshape(h2, row)[:, :w2 * nch]
    arr = arr.reshape(h2, w2, nch)
    if nch == 1:
        return np.repeat(arr, 3, axis=2)
    return np.ascontiguousarray(arr[:, :, :3])  # 取前3通道, RGB顺序(冻结帧本身是RGB888)


def _read_color(full_path):
    """读图转彩色RGB（np.fromfile+imdecode兼容中文路径, 灰PNG自动升3通道, BGR→RGB与截屏侧一致）"""
    import cv2
    data = np.fromfile(full_path, dtype=np.uint8)
    if data.size == 0:
        return None
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


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
    img = _read_color(full)
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
    _flat_logged.discard(rel_path)


def client_area_bbox(hwnd):
    """窗口客户区的屏幕坐标 bbox（左上右下，物理像素）"""
    rect = ctypes.wintypes.RECT()
    if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    pt = ctypes.wintypes.POINT(0, 0)
    if not _user32.ClientToScreen(hwnd, ctypes.byref(pt)):
        return None
    return (pt.x, pt.y, pt.x + rect.right, pt.y + rect.bottom)


def current_screen_size():
    """当前搜索区域的像素尺寸(宽,高); 绑定进程时取前台窗口客户区, 否则取全屏虚拟桌面"""
    bb = search_bbox()
    try:
        from PIL import ImageGrab
        if bb is not None:
            return (bb[2] - bb[0], bb[3] - bb[1])
        im = ImageGrab.grab(all_screens=True)
        return im.size
    except Exception:
        return (0, 0)


def search_bbox():
    """当前搜索区域：绑定进程时=前台窗口客户区，未绑定=全屏"""
    from core.window_gate import get_bound_process
    if get_bound_process():
        hwnd = _user32.GetForegroundWindow()
        if hwnd:
            return client_area_bbox(hwnd)
    return None


def grab_rgb(bbox=None):
    """截取指定区域（bbox=None 为全屏）返回彩色RGB ndarray"""
    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    return np.array(img)


# 全屏搜索的粗筛降采样系数: 1/2 分辨率下匹配快约5倍, 而满分/噪声分数的区分度保持不变
# (实测 1.0分: 满分1.000/噪声0.062; 0.5分: 满分1.000/噪声0.123)
SEARCH_COARSE_SCALE = 0.5


def match_template(screen_gray, tpl_gray, coarse=True):
    """在画面中全屏搜索模板，返回 (最高得分0~1, 位置xy)；模板比画面大时 (-1, None)。

    coarse=True 时先在 1/2 分辨率粗筛定位, 再回到原分辨率对命中邻域精算:
    得分与全分辨率一致, 耗时降到约1/5。给定小区域(<0.6MP)时直接精算, 省去降采样开销。
    """
    import cv2
    H, W = screen_gray.shape[:2]
    th, tw = tpl_gray.shape[:2]
    if H < th or W < tw:
        return -1.0, None
    pad0 = 8  # 粗筛定位误差余量(原分辨率px)
    # 彩色模板走cv2的彩色匹配(通道数需一致), 粗筛同样降采样后回原分辨率精算
    if not coarse or screen_gray.size < 600_000:
        res = cv2.matchTemplate(screen_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        return float(max_val), max_loc
    s = SEARCH_COARSE_SCALE
    if th * s < 4 or tw * s < 4:
        res = cv2.matchTemplate(screen_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        return float(max_val), max_loc
    # 粗筛一律用灰度: 彩色matchTemplate比灰度慢约3倍, 而粗筛只需定位不比分数
    if screen_gray.ndim == 3:
        cscr = cv2.cvtColor(screen_gray, cv2.COLOR_BGR2GRAY)
        ctpl = cv2.cvtColor(tpl_gray, cv2.COLOR_BGR2GRAY) if tpl_gray.ndim == 3 else tpl_gray
    else:
        cscr, ctpl = screen_gray, tpl_gray
    small_scr = cv2.resize(cscr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    small_tpl = cv2.resize(ctpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    if small_scr.shape[0] < small_tpl.shape[0] \
            or small_scr.shape[1] < small_tpl.shape[1]:
        res = cv2.matchTemplate(screen_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        return float(max_val), max_loc
    coarse_res = cv2.matchTemplate(small_scr, small_tpl, cv2.TM_CCOEFF_NORMED)
    _, coarse_val, _, coarse_loc = cv2.minMaxLoc(coarse_res)
    # 粗筛命中位置映射回原分辨率, 只在该位置精算一次(避免全图精算)
    cx = int(round(coarse_loc[0] / s))
    cy = int(round(coarse_loc[1] / s))
    # 邻域要覆盖粗筛的全部定位误差: 粗筛分辨率下1px = 原图 1/s px, 留足余量
    pad = max(int(round(pad0 / s)) + tw, th)
    x0 = max(0, cx - pad)
    y0 = max(0, cy - pad)
    x1 = min(W, cx + tw + pad)
    y1 = min(H, cy + th + pad)
    if x1 - x0 >= tw and y1 - y0 >= th:
        sub = screen_gray[y0:y1, x0:x1]
        fine = cv2.matchTemplate(sub, tpl_gray, cv2.TM_CCOEFF_NORMED)
        _, fv, _, fl = cv2.minMaxLoc(fine)
        return float(fv), (fl[0] + x0, fl[1] + y0)
    return float(coarse_val), (cx, cy)


def _score_at(screen_gray, tpl_gray, x, y):
    """在画面指定位置(x,y左上角)计算模板相似度, 用TM_CCOEFF_NORMED同公式手工算(等价于该位置的matchTemplate值)"""
    h, w = tpl_gray.shape[:2]
    H, W = screen_gray.shape[:2]
    if x < 0 or y < 0 or x + w > W or y + h > H:
        return -1.0
    win = screen_gray[y:y + h, x:x + w].astype(np.float64)
    tpl = tpl_gray.astype(np.float64)
    tw = tpl - tpl.mean()
    iw = win - win.mean()
    den = np.sqrt(float((tw * tw).sum()) * float((iw * iw).sum()))
    if den <= 0:
        return -1.0  # 分母0(纯色区域), 与match_template的"纯色拒绝"语义一致
    return float((tw * iw).sum()) / den


def _best_in_tolerance(screen_gray, tpl_gray, l, t, tolerance):
    """在容错范围内逐px微移, 取最高分(抵消1-3px的渲染抖动/DPI取整误差)"""
    best, best_xy = -1.0, None
    for dy in range(-tolerance, tolerance + 1):
        for dx in range(-tolerance, tolerance + 1):
            sc = _score_at(screen_gray, tpl_gray, l + dx, t + dy)
            if sc > best:
                best, best_xy = sc, (l + dx, t + dy)
    return best, best_xy


def _resolve_bbox(bbox, ref_size, W, H):
    """bbox 按参考分辨率换算到当前画面, 越界返回 None"""
    l, t, r, b = bbox
    tw, th = r - l, b - t
    if tw <= 0 or th <= 0:
        return None
    if ref_size and ref_size[0] > 0 and ref_size[1] > 0:
        sx, sy = W / float(ref_size[0]), H / float(ref_size[1])
        l, t, r, b = int(round(l * sx)), int(round(t * sy)), int(round(r * sx)), int(round(b * sy))
        tw, th = r - l, b - t
        if tw <= 0 or th <= 0:
            return None
    if l < 0 or t < 0 or l + tw > W or t + th > H:
        return None
    return l, t, r, b


def match_fixed_position(screen_rgb, tpl_rgb, bbox, tolerance=TOLERANCE_PX,
                        ref_size=None, mode=None):
    """固定位置比对: 只在框选时的屏幕绝对坐标附近(±tolerance)取最高得分。

    与全屏搜索的本质区别: 不滑动。目标从框内移出时得分立刻下降, 而不是被搜索到新位置继续满分。
    ref_size 为框选时的画面尺寸(宽,高); 当前画面尺寸与之不同时按比例换算bbox坐标,
    这样换分辨率(且元素跟着走)仍能对上。返回 (得分0~1, 命中xy或None)。
    坐标换算后仍越界 -> (-1.0, None)。

    mode 为比对精度档(见 MATCH_MODES): 把原图分与方框模糊分按权重加权。
    模糊通道抹平像素级差异(读秒数字/文字/动画), 保留布局结构, 让这类
    内容持续变动的监测区域分数稳定在阈值之上, 而不必靠压低阈值换取通过
    (压低阈值会让无关画面更容易误触发)。
    """
    if tpl_rgb is None or bbox is None:
        return -1.0, None
    tpl_gray = _to_gray(tpl_rgb)
    screen_gray = _to_gray(screen_rgb)
    H, W = screen_gray.shape[:2]
    bb = _resolve_bbox(bbox, ref_size, W, H)
    if bb is None:
        return -1.0, None
    l, t, r, b = bb

    grant = match_weights(mode)
    if grant <= 0:
        return _best_in_tolerance(screen_gray, tpl_gray, l, t, tolerance)
    k = BLUR_KERNEL

    best_raw, best_xy = _best_in_tolerance(screen_gray, tpl_gray, l, t, tolerance)
    # 模糊通道: 模板与画面同参数。
    # 画面必须先在全图上模糊再裁选区——若先裁后模糊, 选区边缘会混入空白填充,
    # 边缘效应把分数整体压低(实测能把0.98压到0.6上下), 等于白做。
    scr_b = _box_blur(screen_gray, k)
    if scr_b is None:
        return best_raw, best_xy
    scr_blur = scr_b[y_slice(t, b, H), x_slice(l, r, W)]
    tpl_blur = _box_blur(tpl_gray, k)
    if tpl_blur is None or scr_blur.shape != tpl_blur.shape:
        return best_raw, best_xy
    best_blur, blur_xy = _best_in_tolerance(scr_blur, tpl_blur, 0, 0, tolerance)
    if best_blur < 0:
        return best_raw, best_xy
    # 赋分制: 原图分保底不动, 模糊分按折扣加成。封顶 1.0——否则静止帧会算出 1.2,
    # UI 上显示 120% 准确率毫无意义, 且阈值比较也失去意义。
    total = min(1.0, best_raw + best_blur * grant)
    # 命中坐标优先取分数更高的那个通道, 保证虚线框/命中点指示的是真实位置
    xy = blur_xy if (best_blur > best_raw and blur_xy) else best_xy
    if xy:
        xy = (xy[0] + l, xy[1] + t)
    return total, xy


def x_slice(l, r, W):
    return slice(max(0, l), min(W, r))


def y_slice(t, b, H):
    return slice(max(0, t), min(H, b))


def _to_gray(img):
    """RGB ndarray转灰度(与_load_template/match_template的灰度侧保持一致)"""
    if img.ndim == 2:
        return img
    import cv2
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)


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


def _scale_bbox(bbox, scale):
    """按系数缩放选区(以左上角为锚点), 缩到非正数返回 None"""
    if scale == 1.0 or not bbox:
        return bbox
    l, t, r, b = bbox
    w, h = (r - l) * scale, (b - t) * scale
    if w < 1 or h < 1:
        return None
    return (int(round(l)), int(round(t)), int(round(l + w)), int(round(t + h)))


def match_mode_fixed():
    """是否用固定位置比对模式(读设置, 默认True=固定位置)。关掉则走全屏搜索"""
    from config import load_settings
    return bool(load_settings().get("fixed_position_match", True))


# 比对精度档: (原图权重, 模糊权重)
# 数字/文字会变的监测区域(如实时读秒)原始分数会在较窄区间大幅波动, 阈值难定;
# 掺入方框模糊通道后整段被抬到阈值之上(实测模糊通道把"内容已变"的0.77抬到0.98)。
# 原图权重保留下限, 保证真正不相关的画面仍不会被抬到阈值附近。
# 比对精度的赋分档: 原图分占 100%(恒定, 不因档位下降), 模糊分按折扣加成。
# 总准确率 = min(1.0, 原图分 + 模糊分*折扣) —— 赋分不是加权平均, 模糊分不被稀释,
# 是额外加分。折扣值小是因为模糊分本身接近1, 8%折扣约有0.08的实际贡献。
# raw 的折扣为0, 表示根本不计算模糊通道(省掉一次全图模糊)。
MATCH_GRANT = {
    "raw": 0.00,        # 原版: 只算原图, 不掺模糊
    "strict": 0.09,     # 精确: 掺一点模糊, 轻微容忍
    "balanced": 0.15,   # 平衡: 适合数字/文字会变的区域
    "loose": 0.21,      # 粗略: 容忍度最高
}
MATCH_MODE_ORDER = ["raw", "strict", "balanced", "loose"]
MATCH_MODE_LABEL = {"raw": "原版", "strict": "精确",
                    "balanced": "平衡", "loose": "粗略"}
# 高斯模糊: ksize 是主参数, 直接决定观感。45 是实测下来糊得最舒服的一档。
# sigma 传 0 让引擎按 ksize 自动推(0.3*((k-1)*0.5-1)+0.8 = 7.10):
# 手动指定 sigma 反而会脱离您认可的观感, 且 sigma 大于自动值时 ksize=45
# 装不下(需要 ksize >= 2*ceil(2*sigma)+1), 尾部被截断反而退化成带旁瓣的方框效果。
BLUR_KERNEL = 45


def match_weights(mode=None):
    """取模糊分折扣系数。mode 省略则读设置; 未知档名退回"原版"。

    保留 match_weights 这个名字是因为设置页/预览/执行器都在用它,
    语义已从"权重对"变成"折扣率"。
    """
    if mode is None:
        from config import load_settings
        mode = load_settings().get("match_mode", "raw")
    return MATCH_GRANT.get(mode, MATCH_GRANT["raw"])


def set_match_mode(mode):
    """切换比对精度档(写设置), 返回是否成功"""
    if mode not in MATCH_GRANT:
        return False
    from config import load_settings, save_settings
    s = load_settings()
    s["match_mode"] = mode
    save_settings(s)
    return True


def _box_blur(img, k=BLUR_KERNEL):
    """高斯模糊: 抹平像素级差异(文字/数字/动画), 保留布局结构。

    名字沿用 _box_blur 是历史遗留, 实际是 GaussianBlur。
    sigma 传 0 由引擎按 ksize 自动推, ksize 太小(如 1)直接跳过。
    模板与画面必须同参数处理, 否则原图匹配自身就会掉分。"""
    if img is None or k is None or k <= 1:
        return img
    k = int(k)
    if k % 2 == 0:
        k += 1
    try:
        import cv2
        return cv2.GaussianBlur(img, (k, k), 0)
    except Exception:
        return img


def match_tolerance():
    """固定位置匹配的容错半径(px), 来自设置页"位置容错"""
    from config import load_settings
    return int(load_settings().get("match_tolerance", TOLERANCE_PX))


def match_once(rel_path, threshold=0.85, scales=(1.0,), mode=None):
    """截屏并匹配一次，返回 (是否命中, 最高得分)。
    scales 为模板缩放系数序列，按序尝试，命中即停（列表顺序=优先级）。
    mode 为比对精度档（见 MATCH_MODES），None=读全局设置；动作级可单独指定。
    截屏/匹配异常向上抛，由调用方处理"""
    tpl = _load_template(rel_path)
    if tpl is None:
        return False, 0.0
    # 固定位置模式: 模板有框选坐标且开关打开时, 只在原坐标比对(不滑动)
    if match_mode_fixed():
        bbox, ref_size = load_template_meta(rel_path)
        if bbox is not None:
            screen_rgb = grab_rgb(search_bbox())
            tol = match_tolerance()
            # 只用尺度 1.0: 框选坐标与模板是一一对应的"这块内容长这样"。
            # 缩放模板只会拿放大后的模板去比对原尺寸内容, 分数必然暴跌;
            # 换分辨率由 ref_size 按比例换算坐标, 与尺度无关。
            # 多尺度是全屏搜索的需求(不知道目标多大时才需要挨个试)。
            best, _ = match_fixed_position(screen_rgb, tpl, bbox, tol, ref_size, mode=mode)
            if best >= 0:
                return best >= threshold, best
    if template_sigma(tpl) < MIN_TEMPLATE_STD:
        # 纯色模板: σ≈0→分母0/0→CCOEFF对任意画面恒1.0, 判不命中(-1与"模板过大"同语义)
        if rel_path not in _flat_logged:
            _flat_logged.add(rel_path)
            from logger import log_info
            log_info("tpl_flat", f"{rel_path} σ<{MIN_TEMPLATE_STD} 纯色模板, 拒绝匹配")
        return False, -1.0
    screen = grab_rgb(search_bbox())
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
