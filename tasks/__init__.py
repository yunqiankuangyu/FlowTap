"""
tasks - 任务管理模块
"""
from .keyboard.keyboard_task import KeyboardTask, TaskStatus, make_key_action, make_click_action, fmt_action
from .mouse.mouse_task import MouseTask

__all__ = ['KeyboardTask', 'MouseTask', 'TaskStatus', 'make_key_action', 'make_click_action', 'fmt_action']
