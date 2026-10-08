"""
设置管理模块
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.themes import DEFAULT_THEME

# 配置文件路径（与主程序同目录）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _app_dir():
    """exe 或脚本所在目录（PyInstaller 打包后 __file__ 在临时目录，必须用 argv[0]）"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return _BASE_DIR


SETTINGS_FILE = os.path.join(_app_dir(), "settings.json")


# 全部设置项默认值的唯一出处 —— 调用点别再写 0.5 / 80 / 3 这类字面量(改默认值只改这里)
DEFAULTS = {
    "opacity": 0.9,            # 窗口不透明度
    "theme": DEFAULT_THEME,    # 主题名
    "bind_process": "",        # 前台闸门绑定的进程名(空 = 不绑定)
    "default_delay": 0.5,      # 新建动作的后延
    "default_loop": 80,        # 新建任务的循环间隔
    "default_runs": 3,         # 新建任务的次数
    "start_countdown": 3,      # 启动倒计时秒数
}


def load_settings():
    """加载设置(文件里没有的键用 DEFAULTS 补齐)"""
    defaults = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            defaults.update(json.load(f))
    except: pass
    # 防止主题名失效
    from .themes import THEMES
    if defaults["theme"] not in THEMES:
        defaults["theme"] = DEFAULT_THEME
    return defaults


def get_setting(key):
    """读一项设置, 文件没写过就给 DEFAULTS 里的默认值"""
    return load_settings().get(key, DEFAULTS.get(key))


def save_settings(settings):
    """保存设置"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
