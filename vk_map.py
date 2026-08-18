"""
虚拟键码映射模块
"""

VK_MAP = {}
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    VK_MAP[c] = 0x41 + i
for i, c in enumerate("0123456789"):
    VK_MAP[c] = 0x30 + i

VK_MAP.update({
    'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B, 'backspace': 0x08,
    'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27
})

for i in range(1, 13):
    VK_MAP[f"f{i}"] = 0x70 + i - 1

# 虚拟键码到名称的映射
VK_NAME = {v: k.upper() for k, v in VK_MAP.items()}
