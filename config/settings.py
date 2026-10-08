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


# 个人配置统一住这里: settings.json / presets.json 都在 userdata/ 下,
# 不跟代码、日志混在根目录(README 目录树同步)
USER_DIR = os.path.join(_app_dir(), "userdata")
SETTINGS_FILE = os.path.join(USER_DIR, "settings.json")


def ensure_user_dir():
    """个人配置目录不存在就建(新装机器第一次保存前调)"""
    try:
        os.makedirs(USER_DIR, exist_ok=True)
    except Exception:
        pass


def migrate_legacy(filename):
    """旧版把配置放根目录, 首次读取时一次性搬进 userdata/。

    新家已有同名文件就不动(用户已在新位置改过 = 新数据优先);
    搬不动/权限问题静默放弃, 不影响读旧文件。
    """
    try:
        old = os.path.join(_app_dir(), filename)
        new = os.path.join(USER_DIR, filename)
        if os.path.exists(old) and not os.path.exists(new):
            ensure_user_dir()
            os.replace(old, new)
    except Exception:
        pass


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
    migrate_legacy("settings.json")   # 旧根目录文件一次性搬进 userdata/
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
    ensure_user_dir()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
