# -*- coding: utf-8 -*-
"""Rust 数值内核的 ctypes 桥接层。

项目约定：重写就是把要改的地方换成 Rust，不留 Python 备份。
因此本模块在 DLL 缺失/损坏时明确抛错，不静默降级、不带 Python 参考实现。
"""
import ctypes
import os
import sys

def _dll_path():
    """源码运行：engine/bin/flowtap_core.dll（与编译垃圾 target 分离，
    target 可随时删除/重建而不影响运行）；
    PyInstaller 打包后：DLL 随包放在 _MEIPASS 根下。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.argv[0]))
        return os.path.join(base, "flowtap_core.dll")
    # DLL 就放在 engine/bin/ 下（本文件同目录的 bin 子目录）
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "bin", "flowtap_core.dll")


_LIB_PATH = _dll_path()

if not os.path.isfile(_LIB_PATH):
    raise RuntimeError(
        f"Rust 内核 DLL 缺失: {_LIB_PATH}\n"
        f"请在 rust_core/ 下执行 cargo build --release，或将 DLL 随程序一起分发。"
    )

_lib = ctypes.CDLL(_LIB_PATH)
_lib.ft_best_in_tolerance.argtypes = [
    ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
]
_lib.ft_best_in_tolerance.restype = None
_lib.ft_score_at.argtypes = [
    ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int,
    ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int,
]
_lib.ft_score_at.restype = ctypes.c_double
_lib.ft_validate_actions.argtypes = [ctypes.c_char_p]
_lib.ft_validate_actions.restype = ctypes.POINTER(ctypes.c_char)
_lib.ft_free_string.argtypes = [ctypes.c_void_p]
_lib.ft_free_string.restype = None


def validate_actions(actions):
    """校验并规范化动作列表。
    返回 (ok, result)：ok=True 时 result 是规范化后的 list；
    ok=False 时 result 是中文错误字符串。
    """
    import json
    raw = json.dumps(actions, ensure_ascii=False).encode("utf-8")
    ptr = _lib.ft_validate_actions(raw)
    if not ptr:
        return False, "校验器返回空指针"
    try:
        s = ctypes.string_at(ptr).decode("utf-8")
    finally:
        _lib.ft_free_string(ptr)
    if s.startswith("ERR:"):
        return False, s[4:]
    return True, json.loads(s)


def available():
    return True  # 加载失败在 import 时已抛错，能走到这里就是可用


def _as_ptr_and_shape(arr):
    """返回 (u8 指针, h, w, 保活对象)。"""
    if isinstance(arr, tuple) and len(arr) == 3 and isinstance(arr[0], bytes):
        raw, h, w = arr
        buf = ctypes.create_string_buffer(raw, len(raw))
        return ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8)), h, w, buf
    h, w = arr.shape[:2]
    flat = arr.ravel()
    ptr = flat.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    return ptr, int(h), int(w), flat


def score_at(screen_gray, tpl_gray, x, y):
    """单点归一化互相关（Rust 实现）。"""
    sp, sh, sw, _ = _as_ptr_and_shape(screen_gray)
    tp, th, tw, _ = _as_ptr_and_shape(tpl_gray)
    return float(_lib.ft_score_at(sp, sh, sw, tp, th, tw, x, y))


def best_in_tolerance(screen_gray, tpl_gray, l, t, tolerance):
    """返回 (best_score, (x, y) 或 None)（Rust 实现）。"""
    sp, sh, sw, _ = _as_ptr_and_shape(screen_gray)
    tp, th, tw, _ = _as_ptr_and_shape(tpl_gray)
    out_score = ctypes.c_double(-1.0)
    out_x = ctypes.c_int(0)
    out_y = ctypes.c_int(0)
    _lib.ft_best_in_tolerance(sp, sh, sw, tp, th, tw, l, t, tolerance,
                              ctypes.byref(out_score),
                              ctypes.byref(out_x), ctypes.byref(out_y))
    if out_score.value < 0:
        return -1.0, None
    return float(out_score.value), (out_x.value, out_y.value)
