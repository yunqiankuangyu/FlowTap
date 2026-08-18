"""
轻松AI - 键鼠模拟器
依赖: pip install PySide6
"""
import sys
import os

# 将项目根目录添加到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置环境变量，让Python知道这是一个包
os.environ['QINGSONG_AI_ROOT'] = project_root


def ensure_admin():
    """如果不是管理员权限，自动以管理员身份重启"""
    import ctypes
    if sys.platform != "win32": return
    if ctypes.windll.shell32.IsUserAnAdmin(): return
    script = os.path.abspath(sys.argv[0])
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    ctypes.windll.shell32.ShellExecuteW(None, "runas", pythonw, f'"{script}"', None, 0)
    sys.exit(0)


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("仅支持 Windows")

    ensure_admin()

    # DPI 感知：确保坐标系统一致
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    import traceback

    try:
        from PySide6.QtWidgets import QApplication
        from ui.app import App

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # 遮罩关闭时不退出
        window = App()
        window.show()
        sys.exit(app.exec())
    except Exception:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tb = traceback.format_exc()
        # 1. 历史日志（追加，带时间戳）
        log_hist = os.path.join(project_root, "error.log")
        with open(log_hist, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*40}\n[{now}]\n{tb}")
        # 2. 最新日志（覆写，只保留最近一次）
        log_latest = os.path.join(project_root, "error_latest.log")
        with open(log_latest, "w", encoding="utf-8") as f:
            f.write(f"[{now}]\n{tb}")
        # 弹窗提示
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"轻松AI启动异常，错误日志已保存到:\n{log_latest}\n\n{tb}",
            "轻松AI - 错误",
            0x10
        )
