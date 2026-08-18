"""
主题系统模块
"""
from PySide6.QtGui import QFont

DEFAULT_THEME = "🔵 默认蓝"

# ─── 主题系统 ───
THEMES = {
    # ── 暗色系（高饱和，各有性格）──
    "🔵 默认蓝":   {"CARD": "#1a2a4a", "ACCENT": "#121e38", "BLUE": "#4d9cff", "GREEN": "#4ade80", "RED": "#f87171", "YELLOW": "#facc15", "TEXT": "#e2e8f0", "TEXT2": "#94a3b8", "DIM": "#64748b", "HOVER_GREEN": "#22c55e", "HOVER_RED": "#ef4444"},
    "🟣 猫布丁":   {"CARD": "#382a50", "ACCENT": "#2a1e40", "BLUE": "#b4a0f0", "GREEN": "#a0e8a0", "RED": "#ff8090", "YELLOW": "#ffe080", "TEXT": "#e0d8f0", "TEXT2": "#c0b0e0", "DIM": "#8878b0", "HOVER_GREEN": "#60e0c0", "HOVER_RED": "#ff6080"},
    "🔥 炭火":     {"CARD": "#382818", "ACCENT": "#2a1e10", "BLUE": "#68c8e8", "GREEN": "#b8e060", "RED": "#ff6848", "YELLOW": "#ffb830", "TEXT": "#f0e8d8", "TEXT2": "#d0c0a0", "DIM": "#a08860", "HOVER_GREEN": "#98d040", "HOVER_RED": "#ff5030"},
    "🌲 北欧森林": {"CARD": "#1e3030", "ACCENT": "#162828", "BLUE": "#60c8d8", "GREEN": "#80e090", "RED": "#e07070", "YELLOW": "#e0d070", "TEXT": "#d8f0e0", "TEXT2": "#a0d0b8", "DIM": "#508878", "HOVER_GREEN": "#40d8a0", "HOVER_RED": "#d06060"},
    "🍇 葡萄冻":   {"CARD": "#302048", "ACCENT": "#241838", "BLUE": "#c8a0ff", "GREEN": "#90e0b0", "RED": "#ff80a0", "YELLOW": "#ffe090", "TEXT": "#e8d8f8", "TEXT2": "#c8b0e0", "DIM": "#9070c0", "HOVER_GREEN": "#60d8a0", "HOVER_RED": "#ff6090"},
    # ── 亮色系（柔和亮，不刺眼）──
    "🌿 清新绿":   {"CARD": "#d8edd8", "ACCENT": "#c8e0c8", "BLUE": "#3a9850", "GREEN": "#60c060", "RED": "#d04848", "YELLOW": "#e0a830", "TEXT": "#1a4020", "TEXT2": "#306840", "DIM": "#4a7a5a", "HOVER_GREEN": "#2a8840", "HOVER_RED": "#b83838"},
    "☀️ 暖阳金":   {"CARD": "#f8e8d0", "ACCENT": "#f0dcc0", "BLUE": "#d88830", "GREEN": "#90b848", "RED": "#d06050", "YELLOW": "#d89820", "TEXT": "#503820", "TEXT2": "#785838", "DIM": "#806840", "HOVER_GREEN": "#78a838", "HOVER_RED": "#b84838"},
    "🧊 冰川蓝":   {"CARD": "#d8e8f0", "ACCENT": "#c8dce8", "BLUE": "#3880c0", "GREEN": "#40a878", "RED": "#c85050", "YELLOW": "#c89830", "TEXT": "#182838", "TEXT2": "#385870", "DIM": "#507088", "HOVER_GREEN": "#308860", "HOVER_RED": "#a84040"},
    "🌸 樱花粉":   {"CARD": "#f0d8e0", "ACCENT": "#e8c8d8", "BLUE": "#b060a0", "GREEN": "#60a870", "RED": "#d06068", "YELLOW": "#d0a040", "TEXT": "#402030", "TEXT2": "#704860", "DIM": "#806070", "HOVER_GREEN": "#509060", "HOVER_RED": "#b85058"},
    "⚪ 极简白":   {"CARD": "#f0f0f0", "ACCENT": "#e4e4e4", "BLUE": "#3878c0", "GREEN": "#309848", "RED": "#c84040", "YELLOW": "#b89028", "TEXT": "#181820", "TEXT2": "#505060", "DIM": "#606068", "HOVER_GREEN": "#288038", "HOVER_RED": "#a83030"},
}


class Colors:
    """全局颜色，通过 apply() 整体替换"""
    CARD = "#2b3a5c"
    ACCENT = "#222e4a"
    BLUE = "#5b9cf5"
    GREEN = "#5ec28a"
    RED = "#e8787f"
    YELLOW = "#e8c55a"
    TEXT = "#dce4f0"
    TEXT2 = "#a0b4d0"
    DIM = "#6a80a0"
    HOVER_GREEN = "#48b078"
    HOVER_RED = "#d06068"

    @classmethod
    def apply(cls, theme_name):
        """应用主题颜色"""
        t = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
        for k, v in t.items():
            setattr(cls, k, v)


# 字体
FONT_B = QFont("MiSans", 13, QFont.Bold)
FONT_M = QFont("MiSans", 13, QFont.Bold)
