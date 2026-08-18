"""
轻松AI - 键鼠模拟器
依赖: pip install customtkinter
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
        from ui.app import App
        App().mainloop()
    except Exception:
        # 写日志文件
        log_path = os.path.join(project_root, "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{'='*40}\n")
            traceback.print_exc(file=f)
        # 弹窗提示
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"轻松AI启动异常，错误日志已保存到:\n{log_path}\n\n{traceback.format_exc()}",
            "轻松AI - 错误",
            0x10
        )
