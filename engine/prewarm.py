# -*- coding: utf-8 -*-
"""按需预热：只在任务真正用到某组件时才后台加载它。

规则（动作 kind -> 需要的组件）：
  wait / branch  -> cv2 + PIL.ImageGrab   （识图：截屏 + 模板匹配）
  read           -> RapidOCR             （读数：OCR 识别画面数字）
  其余            -> 不加载任何重组件

设计：
1. 后台 daemon 线程加载，不阻塞 UI；每个组件只加载一次（幂等）。
2. detect 函数纯扫描数据、零开销，可在任何节点频繁调用。
3. OCR 引擎实例写回 tasks.keyboard.keyboard_task._ocr_engine 全局单例。
4. 全程静默容错，预热失败绝不影响主程序。
"""
import sys
import threading

_lock = threading.Lock()
_loaded = {"vision": False, "ocr": False}       # 已加载标记
_pending = {"vision": False, "ocr": False}      # 已排队标记（防重复起线程）
_errors = []


def _log(tag, msg):
    try:
        from logger import log_info
        log_info("prewarm", f"{tag}: {msg}")
    except Exception:
        pass


def detect(tasks):
    """扫描任务列表，返回需要预热的组件集合 {'vision','ocr'}。
    纯数据遍历，无 import、无 I/O，可高频调用。

    兼容两套 UI 的动作格式：
      新 UI(Model):  kind = wait / branch / read
      旧 UI(引擎):   type = wait_image / branch / ocr_read
    """
    need = set()
    for t in tasks or []:
        # 新 UI 是 dict["actions"]；旧 UI 是 KeyboardTask 对象 .actions
        acts = t.get("actions", []) if isinstance(t, dict) else getattr(t, "actions", [])
        for a in acts or []:
            if not isinstance(a, dict):
                continue
            k = a.get("kind") or a.get("type")
            if k in ("wait", "branch", "wait_image"):
                need.add("vision")
            elif k in ("read", "ocr_read"):
                need.add("ocr")
            # 分支 options 里可能藏模板路径，但组件仍是 vision，已覆盖
    return need


def _load_vision():
    import time
    try:
        t0 = time.perf_counter()
        __import__("numpy")
        __import__("cv2")
        __import__("PIL.ImageGrab", fromlist=["ImageGrab"])
        _log("vision", f"{int((time.perf_counter()-t0)*1000)}ms")
    except Exception as e:
        _errors.append(("vision", repr(e)))
    finally:
        with _lock:
            _loaded["vision"] = True


def _load_ocr():
    import time
    try:
        t0 = time.perf_counter()
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        import tasks.keyboard.keyboard_task as kt
        kt._ocr_engine = engine   # 写回全局单例，首次读数直接复用
        _log("ocr", f"{int((time.perf_counter()-t0)*1000)}ms")
    except Exception as e:
        _errors.append(("ocr", repr(e)))
    finally:
        with _lock:
            _loaded["ocr"] = True


def ensure(tasks):
    """检测任务列表，对尚未加载且确实需要的组件，起后台线程加载。
    在任何"节点变化"处调用：新增动作、载入预设、构建模型后。幂等、无阻塞。"""
    need = detect(tasks)
    for comp in need:
        with _lock:
            if _loaded[comp] or _pending[comp]:
                continue
            _pending[comp] = True
        fn = _load_vision if comp == "vision" else _load_ocr
        threading.Thread(target=fn, name=f"prewarm-{comp}", daemon=True).start()


def status():
    """诊断用：返回 (loaded字典, errors)。"""
    with _lock:
        return dict(_loaded), list(_errors)
