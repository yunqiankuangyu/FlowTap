"""
预设管理模块
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import USER_DIR, ensure_user_dir, migrate_legacy

PRESETS_FILE = os.path.join(USER_DIR, "presets.json")   # 与 settings.json 同居 userdata/


def load_presets():
    """加载预设"""
    migrate_legacy("presets.json")   # 旧根目录文件一次性搬进 userdata/
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}


def save_presets(presets):
    """保存预设"""
    ensure_user_dir()
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)


def delete_preset(name):
    """删除预设"""
    presets = load_presets()
    if name in presets:
        del presets[name]
        save_presets(presets)
    return presets
