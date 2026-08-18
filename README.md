# 溯流叩击 (SJ)

键鼠自动化挂机脚本，从 CTk 到 PySide6 的演进之路。

## 版本演进

| 版本 | 框架 | 特点 |
|------|------|------|
| v1 | CustomTkinter | 键盘/鼠标分离模式，基础挂机 |
| v2 | CustomTkinter | 键鼠混合任务，统一操作流 |
| v3 | PySide6 | 迁移 Qt，解决 CTk 渲染闪烁 |

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
# v3 (当前版本)
python main.py

# 或双击启动
启动.bat
```

## 项目结构

```
溯流叩击/
├── main.py              # 入口
├── core/                # 键鼠模拟核心
│   ├── keyboard/
│   └── mouse/
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
