<p align="right">
  <b>🇨🇳 中文</b> | <a href="README.md">🇬🇧 English</a>
</p>

# ⚡ FlowTap（溯流叩击）

键鼠自动化挂机脚本，从 CustomTkinter 到 PySide6 的演进之路。

## 版本演进

| 版本 | 框架 | 特点 |
|------|------|------|
| v1 | CustomTkinter | 键盘/鼠标分离模式，基础挂机 |
| v2 | CustomTkinter | 键鼠混合任务，统一操作流 |
| v3 | PySide6 | 迁移 Qt，解决 CTk 渲染闪烁 |
| v3.1 | PySide6 | Bug 修复与代码清理 |

## 更新日志

### v3.1 — Bug 修复与代码清理

**修复**
- 全部开始/全部停止按钮现在正确处理 3 秒预启动倒计时中的任务（此前倒计时中的任务被误判为空闲，无法停止）
- 迷你模式按钮文本和状态在任务混合状态下（部分运行、部分停止）正确同步
- 设置按钮（⚙）现在可在任务页和设置页之间切换，不再卡在设置页
- 依赖任务完成后不再显示"已完成n次"，直接回到"等待下次触发..."

**变更**
- 依赖任务倒计时文案从"延时 Ns"统一为"等待 Ns"（与独立任务一致）
- 任务卡片间隔标签根据关系类型切换：独立任务显示"循环:"，依赖任务显示"延迟:"

**移除**
- 死代码：`core/keyboard/`、`core/mouse/` 子模块（与 `core/__init__.py` 重复）
- 死代码：`ui/layer.py`、`ui/mouse_mode.py`（CustomTkinter 遗留代码，v3 未使用）
- 新增 `.gitignore`，排除 `__pycache__/`、`settings.json`、`presets.json`、错误日志

## 功能

- **键盘模拟**：按键序列录制与回放，支持循环、延迟、组合键
- **鼠标模拟**：点击/移动录制与回放，支持坐标绑定
- **混合模式**：键鼠动作自由组合，同一任务内混合执行
- **任务管理**：多任务列表，一键全部开始/停止
- **预设系统**：保存/加载常用键位配置
- **迷你模式**：无边框悬浮窗，快速操作
- **设置**：透明度调节、主题切换

## 使用

```
python main.py
```

## 项目结构

```
FlowTap/
├── main.py              # 入口
├── core/                # 键鼠模拟核心 (Win32 SendInput)
│   └── __init__.py
├── tasks/               # 任务逻辑
│   ├── keyboard/
│   └── mouse/
├── ui/                  # 界面
│   ├── app.py           # 主窗口
│   ├── titlebar.py      # 自绘标题栏
│   ├── keyboard_mode.py # 键盘模式
│   ├── settings_mode.py # 设置页
│   └── mini_mode.py     # 迷你窗口
├── config/              # 配置
│   ├── themes.py
│   ├── settings.py
│   └── presets.py
└── vk_map.py            # 虚拟键码映射
```

## 环境

- Python 3.11+
- PySide6 (v3) / CustomTkinter (v1/v2)
- Windows 10/11

## 许可

个人项目，仅供学习交流。
