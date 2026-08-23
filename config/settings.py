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


def load_settings():
    """加载设置"""
    defaults = {"opacity": 1.0, "theme": DEFAULT_THEME}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            defaults.update(json.load(f))
    except: pass
    # 防止主题名失效
    from .themes import THEMES
    if defaults["theme"] not in THEMES:
        defaults["theme"] = DEFAULT_THEME
    return defaults


def save_settings(settings):
    """保存设置"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
