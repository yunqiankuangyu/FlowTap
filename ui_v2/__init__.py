"""
新 UI 的配置模块 —— 主题独立副本, 设置/预设归 config 一家

themes.py 独立一份(与旧 config/themes.py 各自演进, 改主题色只改自己这份);
settings.py 与 presets.py 是薄转发, 正源在 config/(与旧UI共用 userdata/ 同一份
settings.json、presets.json), 防止两处各写一遍落盘逻辑而漂:
  themes.py    主题色板与字体(独立副本)
  settings.py  设置读写 -> config.settings(正源 userdata/settings.json)
  presets.py   预设存取 -> config.presets(正源 userdata/presets.json)
"""
from .themes import Colors, THEMES, DEFAULT_THEME, FONT_B, FONT_M
from .settings import load_settings, save_settings
from .presets import load_presets, save_presets, delete_preset

__all__ = ['Colors', 'THEMES', 'DEFAULT_THEME', 'FONT_B', 'FONT_M',
           'load_settings', 'save_settings',
           'load_presets', 'save_presets', 'delete_preset']
