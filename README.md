<p align="right">
  <a href="README.zh.md">🇨🇳 中文</a> | <b>🇬🇧 English</b>
</p>

# ⚡ FlowTap

Keyboard & mouse automation script — from CustomTkinter to PySide6.

## Features

- **Keyboard Simulation** — Record & replay key sequences with loops, delays, combos
- **Mouse Simulation** — Record & replay clicks/movements with coordinate binding
- **Hybrid Mode** — Mix keyboard and mouse actions in a single task
- **Task Management** — Multi-task list, start all / stop all
- **Preset System** — Save & load key configurations
- **Mini Mode** — Borderless floating window for quick access
- **Settings** — Opacity control, theme switching

## Usage

```
python main.py
```

## Requirements

- Python 3.11+
- PySide6 (v3) / CustomTkinter (v1/v2)
- Windows 10/11

## Project Structure

```
FlowTap/
├── main.py              # Entry point
├── core/                # Keyboard & mouse simulation (Win32 SendInput)
│   └── __init__.py
├── tasks/               # Task logic
│   ├── keyboard/
│   └── mouse/
├── ui/                  # Interface
│   ├── app.py           # Main window
│   ├── titlebar.py      # Custom titlebar
│   ├── keyboard_mode.py # Keyboard mode
│   ├── settings_mode.py # Settings page
│   └── mini_mode.py     # Mini window
├── config/              # Configuration
│   ├── themes.py
│   ├── settings.py
│   └── presets.py
└── vk_map.py            # Virtual key code mapping
```

## Changelog

### Version History

| Version | Framework | Highlights |
|---------|-----------|------------|
| v3.6 | PySide6 | Pause all tasks, collapse task cards |
| v3.5 | PySide6 | Key combos, settings pages, portable exe |
| v3.4 | PySide6 | Global stop hotkey & run-count limit |
| v3.3 | PySide6 | Optimized partial font display |
| v3.2 | PySide6 | Hold-to-press for key & mouse bindings |
| v3.1 | PySide6 | Bug fixes & cleanup |
| v3 | PySide6 | Qt migration, solves CTk rendering flicker |
| v2 | CustomTkinter | Unified keyboard+mouse task mode |
| v1 | CustomTkinter | Separate keyboard/mouse modes, basic automation |

### v3.6 — Pause All & Card Collapse

**New**
- **Pause/resume all tasks** — A new "⏸ 全部暂停" button on the bottom bar freezes all running tasks; click again to resume from where they left off. Progress and countdowns are preserved while paused (unlike "Stop" which resets everything)
- **Collapse/expand task cards** — Each task card has a fold button (◀/▶) on the title row to collapse it down to just the header, or expand it to show the full action list. Collapsed cards save vertical space so you can see more tasks at once

**Changed**
- Collapsed card padding unified with expanded state (11px all sides) for consistent look
- Window height calculation updated to match actual card measurements

### v3.5 — Key Combos, Settings Pages & Portable Build

**New**
- **Arbitrary key combos** — Bind W+D style combinations: press and hold any keys (ESC included), release all to confirm. Playback presses them together, holds for the "持续" duration, releases in reverse. Single keys behave exactly as before; old presets fully compatible
- **Settings split into two pages** — 外观设置 (window title, opacity, theme) and 功能设置 (global start F7 & stop F8 hotkeys, new-task defaults, start countdown, always-on-top, remember window height, preset import/export), switched by a dropdown
- **Global start hotkey** — F7 (customizable) mirrors the stop hotkey
- **Preset import/export** — Back up all presets to a JSON file and merge them back on another machine
- **Portable exe** — Single-file Windows build; settings/presets/logs live next to the exe; auto-elevation and apply-restart work frozen

**Changed**
- Default theme is now 冰川蓝 at 90% opacity for fresh installs
- Bottom bar & drag handle are window-level persistent widgets — pixel-identical geometry across pages, only the buttons swap (新建任务/全部开始 ↔ 应用)
- Settings page gets the same bottom bar and drag handle as the task page
- Window height is governed by one source (task-page auto-size + user drag); switching pages never resizes the window
- Task-area height only grows once content exceeds the initial viewport (~3 collapsed cards), per-task growth halved
- Appearance page order: 窗口标题 → 窗口透明度 → 色彩主题
- Settings fonts slimmed, tighter section spacing, slimmer apply button

**Fixed**
- Opacity label showed 8900% instead of 89% (percent-format multiplied the already-percent value)

### v3.4 — Global Stop Hotkey & Run Limit

**New**
- **Global stop hotkey** — Press F8 (customizable) anywhere, even while gaming, to instantly stop all tasks. Configure it in Settings → "全局停止热键"; click "修改热键" and press any key to rebind (ESC cancels). The choice is saved to `settings.json`
- **Run-count limit** — Each task card has a new "次数" input (0 = unlimited). When the task reaches its limit it stops automatically: the button resets to "▶ 开始", the status shows "✓ 已达上限 N 次", and a floating notification pops up

### v3.3 — Keyboard Task & UI Tweaks
**Changed**
- Optimized keyboard‑task execution logic for better stability
- Adjusted partial UI font sizes for improved readability

## License

Personal project. For learning purposes only.
