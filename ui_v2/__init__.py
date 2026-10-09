"""
新 UI 的配置模块 —— 与旧 config/ 完全隔离

隔离原因: 新旧两套 UI 要能各自演进。共用 config/ 时, 为新 UI 改一个字段就可能
把旧 UI 带崩, 反之亦然。这里复制一份独立的主题与设置存取:
  themes.py    主题色板与字体(内容与旧 config/themes.py 相同, 独立副本)
  settings.py  设置读写, 落到 settings_v2.json, 不与旧 UI 抢同一个文件
  presets.py   预设存取
"""
from .themes import Colors, THEMES, DEFAULT_THEME, FONT_B, FONT_M
from .settings import load_settings, save_settings
from .presets import load_presets, save_presets, delete_preset

__all__ = ['Colors', 'THEMES', 'DEFAULT_THEME', 'FONT_B', 'FONT_M',
           'load_settings', 'save_settings',
           'load_presets', 'save_presets', 'delete_preset']
