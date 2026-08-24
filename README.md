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
| v1 | CustomTkinter | Separate keyboard/mouse modes, basic automation |
| v2 | CustomTkinter | Unified keyboard+mouse task mode |
| v3 | PySide6 | Qt migration, solves CTk rendering flicker |
| v3.1 | PySide6 | Bug fixes & cleanup |
| v3.2 | PySide6 | Hold-to-press for key & mouse bindings |
| v3.3 | PySide6 | Optimized partial font display |
| v3.4 | PySide6 | Global stop hotkey & run-count limit |
| v3.5 | PySide6 | Key combos, settings pages, portable exe |

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

### v3.2 — Hold-to-Press

**New**
- **Hold duration** — Each bound key or mouse click can now set a "持续" (hold) time. The input is pressed down, held for the specified duration, then released — simulating a human hold, NOT rapid repeated clicks
- UI: each action row shows a "持续" spinbox (0–30s, 0.1s step) between the action description and "后延"

**Fixed**
- **Key capture focus** — Clear button focus before capturing keys, so Space/Enter no longer triggers the "添加键位" button click (space key could not be bound and created extra capture rows)

**Changed**
- Main window width increased from 346px to 360px (+5%)
- `hold=0` (default) keeps the original tap/click behavior, fully backward-compatible with existing presets

### v3.1 — Bug Fixes & Cleanup

**Fixed**
- **Start All / Stop All** — Tasks during the 3-second pre-start countdown are now correctly stopped, and the button state syncs properly
- **Mini mode button** — Button text and response now correct across mixed task states (some running, some stopped)
- **Settings button** — Clicking ⚙ toggles between task page and settings page, no longer gets stuck
- **Dependency task status** — No longer shows "已完成n次" after completion; returns directly to "等待下次触发..."

**Changed**
- Dependency task countdown text unified from "延时 Ns" to "等待 Ns" (consistent with independent tasks)
- Task card interval label switches between "循环:" (independent) and "延迟:" (dependency) based on relation type

**Removed**
- Dead code: `core/keyboard/`, `core/mouse/` submodules (duplicated by `core/__init__.py`)
- Dead code: `ui/layer.py`, `ui/mouse_mode.py` (CustomTkinter legacy, unused in v3)
- Added `.gitignore` for `__pycache__/`, `settings.json`, `presets.json`, error logs

### v3 — Qt Migration

- Migrated UI framework from CustomTkinter to PySide6 (Qt6)
- Solved CTk rendering flicker on frameless windows
- Custom titlebar, drag-resize, and mini mode reimplemented in Qt

## License

Personal project. For learning purposes only.
