"""预设管理 —— 只做转发, 正源在 config.presets(与旧UI同一份文件同一套逻辑)。

原先这里是 config/presets.py 的逐字拷贝(仅 import 行不同), 换个人配置目录时
两处各改一遍必漂; 现在路径与逻辑都归 config 一家, 本模块只保住包根 re-export 的导入路径。
"""
from config.presets import PRESETS_FILE, load_presets, save_presets, delete_preset

__all__ = ["PRESETS_FILE", "load_presets", "save_presets", "delete_preset"]
