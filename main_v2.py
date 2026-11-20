#新UI打包入口, 等价 python -m ui_v2.main_v2
#PyInstaller 的脚本入口只吃绝对导入, 包内相对导入走不了, 所以不直接指 ui_v2/main_v2.py
import os
import sys

#项目根进 sys.path, 源码与打包两种形态都要找得到包
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
if getattr(sys, "frozen", False):
    project_root = os.path.dirname(os.path.abspath(sys.argv[0]))
    sys.path.insert(0, project_root)


#崩溃落盘+弹窗(打包版没有控制台, 全靠这个查), 同 main.py 的致命错误处理
def _die():
    import traceback
    from datetime import datetime
    tb = traceback.format_exc()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        from logger import log_error, ERROR_LOG, ERROR_LATEST_LOG
        log_error("FATAL")
        log_hist, log_latest = ERROR_LOG, ERROR_LATEST_LOG
    except Exception:
        log_hist = os.path.join(project_root, "error.log")
        log_latest = os.path.join(project_root, "error_latest.log")
    try:
        with open(log_hist, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*40}\n[{now}]\n{tb}")
    except Exception:
        pass
    try:
        with open(log_latest, "w", encoding="utf-8") as f:
            f.write(f"[{now}]\n{tb}")
    except Exception:
        pass
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0,
        f"FlowTap启动异常, 错误日志已保存到:\n{log_latest}\n\n{tb}",
        "FlowTap - 错误",
        0x10,
    )


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("仅支持 Windows")
    #提权与DPI自检跟旧入口同款, 直接复用 main.py 里的同一份
    from main import ensure_admin
    ensure_admin()
    from core.coords import ensure_dpi_aware, probe_dpi_report
    ensure_dpi_aware()
    try:
        from logger import log_info
        log_info("dpi", "\n" + probe_dpi_report())
    except Exception:
        pass
    try:
        from ui_v2.main_v2 import main
        main()
    except Exception:
        _die()
        sys.exit(1)
