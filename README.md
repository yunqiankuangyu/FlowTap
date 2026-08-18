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

### v3.2 — Hold-to-Press

**New**
- **Hold duration** — Each bound key or mouse click can now set a "持续" (hold) time. The input is pressed down, held for the specified duration, then released — simulating a human hold, NOT rapid repeated clicks
- UI: each action row shows a "持续" spinbox (0–30s, 0.1s step) between the action description and "后延"

**Fixed**
- **Key capture focus** — Clear button focus before capturing keys, so Space/Enter no longer triggers the "添加键位" button click (space key could not be bound and created extra capture rows)
- **Spinbox suffix style** — The "s" unit suffix for both "持续" and "后延" inputs is now an independent DIM-colored label, matching the "持续"/"后延" text style

**Changed**
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
