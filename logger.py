"""
轻量运行时日志 —— 只记录异常，不刷屏
写到 exe 同目录的 runtime.log，单文件上限 1MB，超了自动截断保留后半。
"""
import os
import sys
import traceback
from datetime import datetime

_MAX_SIZE = 1_000_000  # 1 MB


def _log_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))


LOG_FILE = os.path.join(_log_dir(), "runtime.log")


def log_error(tag: str, exc: BaseException = None):
    """写一条带时间戳的异常记录；exc=None 时只记 tag"""
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        tb = traceback.format_exc() if exc else ""
        line = f"[{now}] [{tag}] {exc}\n{tb}\n" if exc else f"[{now}] [{tag}]\n"

        # 超限截断
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > _MAX_SIZE:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            half = len(lines) // 2
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(lines[half:])

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # 日志本身不能再抛异常
