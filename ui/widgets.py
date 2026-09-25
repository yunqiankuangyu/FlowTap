"""
通用控件工厂 — 按钮/数字框的共享样式唯一真源
(全app的状态按钮/数字框样式只在这一处定义, 改样式=改这里)
"""
from PySide6.QtWidgets import QPushButton, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from config import Colors, FONT_M


def _make_btn(text, bg=None, fg=None, hover=None, font=None, height=25):
    btn = QPushButton(text)
    btn.setFont(font or FONT_M)
    btn.setFixedHeight(height)
    btn.setCursor(QCursor(Qt.PointingHandCursor))
    bg = bg or Colors.BLUE
    fg = fg or Colors.TEXT
    hover = hover or Colors.ACCENT
    btn.setStyleSheet(f"""
        QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: 4px; }}
        QPushButton:hover {{ background: {hover}; }}
    """)
    return btn

def _tint_btn(btn, bg):
    """动态按钮换底色（与 _make_btn 同款样式）：状态切换按钮专用"""
    btn.setStyleSheet(f"""
        QPushButton {{ background: {bg}; color: {Colors.TEXT}; border: none; border-radius: 4px; }}
        QPushButton:hover {{ background: {Colors.ACCENT}; }}
    """)

def _make_label(text, font=None, color=None):
    lbl = QLabel(text)
    lbl.setFont(font or FONT_M)
    lbl.setStyleSheet(f"color: {color or Colors.TEXT}; background: transparent;")
    return lbl

def state_btn(btn, bg, fg=None, hover=None):
    """17px大状态按钮底色(任务开始/停止、全部控制、暂停条共用)"""
    fg = fg or Colors.TEXT
    if hover:
        btn.setStyleSheet(f"""
            QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: 4px; font: bold 17px 'MiSans'; }}
            QPushButton:hover {{ background: {hover}; }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: 4px; font: bold 17px 'MiSans'; }}
        """)

def flat_btn(btn, bg, fg=None, hover=None):
    """常规按钮底色(迷你窗/设置页等, 字体走setFont不在QSS里)"""
    fg = fg or Colors.TEXT
    if hover:
        btn.setStyleSheet(f"""
            QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background: {hover}; }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: 4px; }}
        """)

def spin_fill(spin):
    """数字框填底样式(任务卡片循环/次数、设置页默认值)"""
    spin.setStyleSheet(f"""
        QDoubleSpinBox {{ background: {Colors.ACCENT}; color: {Colors.TEXT}; border: none; border-radius: 4px; padding: 0px; }}
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}
    """)

def ghost_btn(btn, hover=None, hover_fg=None):
    """透明幽灵按钮底色(画布提示/删除确认钮, 各变体共用)"""
    if hover:
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {Colors.DIM}; border: none; font: bold 17px 'MiSans'; }}
            QPushButton:hover {{ background: {hover}; color: {hover_fg or Colors.TEXT}; }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {Colors.DIM}; border: none; font: bold 17px 'MiSans'; }}
        """)

def style_label(lbl, color=None):
    """标签文字色+透明底(全app状态文字29处共用)"""
    lbl.setStyleSheet(f"color: {color or Colors.TEXT}; background: transparent;")

def spin_flat(spin):
    """数字框透底样式(动作设置页/任务卡片行内输入)"""
    spin.setStyleSheet(f"QDoubleSpinBox {{ background: transparent; color: {Colors.TEXT}; border: none; padding: 0px; }} QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0px; border: none; }}")
