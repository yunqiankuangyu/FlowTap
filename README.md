<p align="right">
  <a href="README.zh.md">🇨🇳 中文</a> | <b>🇬🇧 English</b>
</p>

# ⚡ FlowTap

Keyboard & mouse automation script — from CustomTkinter to PySide6.

## Version History

| Version | Framework | Highlights |
|---------|-----------|------------|
| v1 | CustomTkinter | Separate keyboard/mouse modes, basic automation |
| v2 | CustomTkinter | Unified keyboard+mouse task mode |
| v3 | PySide6 | Qt migration, solves CTk rendering flicker |
| v3.1 | PySide6 | Bug fixes & cleanup |

## Changelog

### v3.1 — Bug Fixes & Cleanup

**Fixed**
- Start All / Stop All button now correctly handles tasks during the 3-second pre-start countdown (previously countdown tasks were treated as idle and could not be stopped)
- Mini mode button text and state now sync correctly across mixed task states (some running, some stopped)
- Settings button (⚙) now toggles between task page and settings page instead of getting stuck on settings
- Dependency task completion status no longer shows "已完成n次"; returns directly to "等待下次触发..."

**Changed**
- Dependency task countdown text unified from "延时 Ns" to "等待 Ns" (consistent with independent tasks)
- Task card interval label switches between "循环:" (independent) and "延迟:" (dependency) based on relation type

**Removed**
- Dead code: `core/keyboard/`, `core/mouse/` submodules (duplicated by `core/__init__.py`)
- Dead code: `ui/layer.py`, `ui/mouse_mode.py` (CustomTkinter legacy, unused in v3)
- Added `.gitignore` for `__pycache__/`, `settings.json`, `presets.json`, error logs

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

## Requirements

- Python 3.11+
- PySide6 (v3) / CustomTkinter (v1/v2)
- Windows 10/11

## License

Personal project. For learning purposes only.
