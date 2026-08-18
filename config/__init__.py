"""
config - 配置管理模块
"""
from .themes import Colors, THEMES, DEFAULT_THEME, FONT_B, FONT_M
from .settings import load_settings, save_settings
from .presets import load_presets, save_presets, delete_preset

__all__ = [
    'Colors', 'THEMES', 'DEFAULT_THEME', 'FONT_B', 'FONT_M',
    'load_settings', 'save_settings',
    'load_presets', 'save_presets', 'delete_preset'
]
