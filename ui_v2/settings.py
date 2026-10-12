"""设置读写 —— 只做转发, 正源在 config.settings(与旧UI同一份文件同一套逻辑)。

原先是 config/settings.py 的独立副本(落 settings_v2.json), 运行时无人用,
谁 `from ui_v2 import load_settings` 就会静默写错文件; 现在路径与逻辑归 config
一家, 本模块只保住包根 re-export 的导入路径(与 presets.py 同款薄转发)。
"""
from config.settings import SETTINGS_FILE, load_settings, save_settings

__all__ = ["SETTINGS_FILE", "load_settings", "save_settings"]
