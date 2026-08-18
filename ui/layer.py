"""
Z-Order 层级管理系统

三层架构：
  - PINNED:  固定层，不随滚动移动（标题栏、底部按钮）
  - NORMAL:  平铺层，正常流式排列（任务卡片列表）
  - FLOATING: 悬浮层，浮在其他内容之上（弹窗、浮动面板）

用法：
  manager = LayerManager(parent_frame)
  manager.add_to_pinned(widget, side='top')     # 固定在顶部
  manager.add_to_pinned(widget, side='bottom')  # 固定在底部
  manager.add_to_normal(widget)                  # 平铺在滚动区
  manager.add_to_floating(widget, x=100, y=50)  # 悬浮在指定位置
"""
import customtkinter as ctk
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Colors


class LayerManager:
    """管理三个z-order层级的容器"""

    # 层级常量
    PINNED = "pinned"      # 置顶/置底，不随滚动移动
    NORMAL = "normal"      # 平铺，正常流式排列
    FLOATING = "floating"  # 悬浮，浮在所有内容之上

    def __init__(self, parent, bg_color="transparent"):
        self.parent = parent
        self.bg_color = bg_color

        # ── Pinned 层（分 top/bottom）──
        self.pinned_top = ctk.CTkFrame(parent, fg_color=bg_color)
        self.pinned_top.pack(side="top", fill="x")

        self.pinned_bottom = ctk.CTkFrame(parent, fg_color=bg_color)
        self.pinned_bottom.pack(side="bottom", fill="x")

        # ── Normal 层（中间 expand 区域）──
        self.normal_frame = ctk.CTkFrame(parent, fg_color=bg_color)
        self.normal_frame.pack(side="top", fill="both", expand=True)

        # ── Floating 层（透明覆盖层）──
        self.floating_frame = ctk.CTkFrame(parent, fg_color="transparent")
        # floating_frame 不 pack，用 place 覆盖

        # 悬浮组件列表
        self._floating_widgets = []

        # 内部引用
        self._all_layers = {
            self.PINNED: {"top": self.pinned_top, "bottom": self.pinned_bottom},
            self.NORMAL: {"main": self.normal_frame},
            self.FLOATING: {"overlay": self.floating_frame},
        }

    def _pack_floating_overlay(self):
        """按需显示悬浮覆盖层"""
        if not self.floating_frame.winfo_ismapped():
            self.floating_frame.place(in_=self.parent, relx=0, rely=0,
                                      relwidth=1, relheight=1)
            self.floating_frame.lift()

    def _unpack_floating_overlay(self):
        """隐藏悬浮覆盖层（如果没有悬浮组件）"""
        if not self._floating_widgets:
            self.floating_frame.place_forget()

    # ══════════════════════════════════════════
    #  公开 API
    # ══════════════════════════════════════════

    def add_pinned(self, widget, side="top", **pack_kwargs):
        """将组件添加到置顶/置底层

        Args:
            widget: 要添加的组件
            side: 'top' 或 'bottom'
            pack_kwargs: 传递给 pack() 的额外参数
        """
        container = self.pinned_top if side == "top" else self.pinned_bottom
        defaults = {"fill": "x"}
        defaults.update(pack_kwargs)
        widget.pack(in_=container, **defaults)

    def add_normal(self, widget, **pack_kwargs):
        """将组件添加到平铺层

        Args:
            widget: 要添加的组件
            pack_kwargs: 传递给 pack() 的额外参数
        """
        defaults = {"fill": "x"}
        defaults.update(pack_kwargs)
        widget.pack(in_=self.normal_frame, **defaults)

    def add_floating(self, widget, x=0, y=0, anchor="nw", **place_kwargs):
        """将组件添加到悬浮层

        Args:
            widget: 要添加的组件
            x, y: 绝对位置
            anchor: 锚点 ('nw', 'center', 'ne' 等)
            place_kwargs: 传递给 place() 的额外参数
        """
        self._floating_widgets.append(widget)
        self._pack_floating_overlay()
        defaults = {"x": x, "y": y, "anchor": anchor}
        defaults.update(place_kwargs)
        widget.place(in_=self.floating_frame, **defaults)
        widget.lift()

    def remove_floating(self, widget):
        """从悬浮层移除组件"""
        if widget in self._floating_widgets:
            self._floating_widgets.remove(widget)
            widget.place_forget()
            self._unpack_floating_overlay()

    def get_container(self, layer, sub="main"):
        """获取指定层级的容器frame

        Args:
            layer: PINNED / NORMAL / FLOATING
            sub: PINNED用 'top'/'bottom'，其他用 'main'/'overlay'
        """
        return self._all_layers[layer][sub]

    # ══════════════════════════════════════════
    #  便捷方法
    # ══════════════════════════════════════════

    def clear_normal(self):
        """清空平铺层所有组件"""
        for w in self.normal_frame.winfo_children():
            w.destroy()

    def clear_floating(self):
        """清空所有悬浮组件"""
        for w in self._floating_widgets[:]:
            w.place_forget()
        self._floating_widgets.clear()
        self._unpack_floating_overlay()

    def lift_floating(self, widget):
        """将悬浮组件提到最上层"""
        widget.lift()

    def lower_floating(self, widget):
        """将悬浮组件降到悬浮层底部"""
        widget.lower()
