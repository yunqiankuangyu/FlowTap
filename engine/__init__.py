# -*- coding: utf-8 -*-
"""运行时引擎层：Rust 数值内核桥接 + 按需预热。

- native_bridge: ctypes 加载 rust_core 编译出的 DLL，供 core.vision / ui_v2.runner 调用
- prewarm: 按任务实际用到的节点，后台加载 cv2/PIL/OCR，消除首次点击卡顿
"""
