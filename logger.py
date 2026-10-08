"""
轻量运行时日志 —— 只记录异常，不刷屏
所有日志统一写到 <程序目录>/logs/ 下：
  - runtime.log       常规运行记录（单文件上限 1MB，超了自动截断保留后半）
  - error.log         致命错误历史（追加）
  - error_latest.log  最近一次致命错误（覆写）
logs/ 目录不存在时自动创建。日志本身任何一步都不能抛异常。
"""
import os
import sys
import traceback
from datetime import datetime

_MAX_SIZE = 1_000_000  # 1 MB


def _root_dir():
    """源码运行=项目根目录；PyInstaller 打包=exe 所在目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))


# 统一日志目录（<root>/logs）
LOG_DIR = os.path.join(_root_dir(), "logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    pass

LOG_FILE = os.path.join(LOG_DIR, "runtime.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")
ERROR_LATEST_LOG = os.path.join(LOG_DIR, "error_latest.log")


def _write(line):
    """追加一行；超限截断保留后半（日志本身不能抛异常）"""
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > _MAX_SIZE:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            half = len(lines) // 2
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[half:])
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def log_info(tag: str, msg: str):
    """写一条带时间戳的信息记录（与 log_error 同文件同 1MB 上限）"""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        _write(f"[{now}] [{tag}] {msg}\n")
    except Exception:
        pass


def log_error(tag: str, exc: BaseException = None):
    """写一条带时间戳的异常记录到 runtime.log；exc=None 时只记 tag"""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        tb = traceback.format_exc() if exc else ""
        line = f"[{now}] [{tag}] {exc}\n{tb}\n" if exc else f"[{now}] [{tag}]\n"
        _write(line)
    except Exception:
        pass  # 日志本身不能再抛异常
