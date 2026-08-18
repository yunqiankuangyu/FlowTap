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
├── core/                # Keyboard & mouse simulation
│   ├── keyboard/
│   └── mouse/
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
