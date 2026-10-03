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
├── main.py                     # Entry point
├── logger.py                   # Runtime log (errors only, writes runtime.log)
├── vk_map.py                   # Virtual key code mapping
├── core/                       # Low-level capabilities
│   ├── __init__.py             # Key/mouse injection (Win32 SendInput)
│   ├── vision.py               # Screen capture + template matching
│   └── window_gate.py          # Foreground gate (run only while target is focused)
├── tasks/                      # Task execution
│   ├── keyboard/
│   │   └── keyboard_task.py    # Task runner (loop / wait / branch / readout)
│   └── mouse/
│       └── mouse_task.py       # Mouse task
├── ui/                         # Interface
│   ├── app.py                  # Main window, bottom bar, page switching
│   ├── titlebar.py             # Custom titlebar
│   ├── keyboard_mode.py        # Task page (cards, action rows)
│   ├── action_settings_view.py # Action settings page
│   ├── settings_mode.py        # Settings page
│   ├── mini_mode.py            # Mini window
│   ├── vision_capture.py       # Region capture
│   ├── vision_preview.py       # Template preview
│   └── widgets.py              # Shared widgets
├── config/                     # Configuration
│   ├── themes.py               # Color themes
│   ├── settings.py             # Settings
│   └── presets.py              # Preset storage
├── templates/                  # Captured template images
├── packaging/                  # Packaging assets (icon, installer script)
├── tools/ui_editor/            # UI editor (not in git)
├── ARCHITECTURE.md             # Architecture overview
├── FlowTap*.spec               # PyInstaller specs (one-file / one-dir)
├── settings.json               # Settings (generated at runtime)
├── presets.json                # Presets (generated at runtime)
└── 启动.bat                    # One-click launcher
```

## Usage Tutorial

### 1. Create a task

**Purpose:** One card = one kind of idle-farming need; all actions are arranged inside the card, and multiple cards run side by side.

Hit **"＋ 新建任务"** on the bottom bar to generate a task card.

### 2. Add actions

**Purpose:** Actions are the building blocks of a task; the three dropdowns add input actions, flow control, and variable logic.

| Dropdown | Actions | Description |
|----------|---------|-------------|
| **"+ 键鼠"** | ⌨ Keyboard, 🖱 Click | Binds keyboard keys and mouse clicks |
| **"+ 插入"** | 📷 等图像, 🔀 分支, ↳ 跳转 | Inserts screen-related actions: 📷 等图像 (waits until the target screen appears), 🔀 分支 (picks the flow by matching the current screen), ↳ 跳转 (jumps to a chosen action and continues from there) |
| **"+ 变量"** | 🔢 读数, ➕ 变量运算, ⚖ 条件分支 | Inserts numeric actions: 🔢 读数 (OCR reads a region into a variable), ➕ 变量运算 (arithmetic on variables), ⚖ 条件分支 (takes a different path when a condition is met) |

**How to add one:** ⌨ press and hold, release all keys to confirm (W+D combos supported); 🖱 click a spot under the fullscreen overlay — ESC cancels, 15s timeout; for 等图像 / 分支 click **"编辑"** at the end of the row to box-select the screen (section 4), for 读数 use **"框选"** + **"试读"** on the row (section 5), and for 跳转 pick the target step right on the row.

### 3. Arrange actions

**Purpose:** Decide execution order and pacing, plus which task waits for which.

- Drag the **☰** handle on the left of a row to reorder (list order = execution order = branch priority)
- **✕** at the end of a row deletes that action
- Row parameters: **持续** (how long a key is held) and **后延** (pause after the action) — shown depending on the action type
- Card parameters: **循环** (pause before the next round; switch the relation to "在任务N后" and the same box becomes **延迟**, the wait after the previous task), **次数** (run limit, 0 = unlimited, auto-stop when reached)
- **关系:** pick "在任务N后" to run this task after the previous one finishes, or "独立" to run independently

### 4. Image wait / branch (screen recognition)

**Purpose:** Solves "pressing keys before the screen has loaded" — wait until the target screen appears, or follow a different flow depending on what's on screen, so one task handles multiple scenarios.

Click **"编辑"** on an action row to open its settings page:

- **"框选"** to mark the screen region, **"原图"** to view the captured reference, **"预览"** for a live match score
- **阈值** (threshold): higher = stricter; switch **精确 / 多尺度** (multi-scale adapts to 125%/150% display scaling)
- **超时** (timeout): 0 (∞) keeps waiting until the screen matches; on timeout pick **跳过 / 跳卡 / 中止**
- Branch: multiple template options, list order = priority, drag to reorder, **"重拍"** to re-capture

### 5. Numeric readout (OCR)

**Purpose:** Lets the task recognize on-screen numbers — the value goes into a variable, where arithmetic and numeric conditions act on it.

- **"框选"** the number region → **"试读"** shows the raw OCR text and the extracted number immediately
- Change the extraction regex via the "取数方式" dropdown; when a window is bound, the region is stored in client-area coordinates so it stays accurate after the window moves

### 6. Run control

**Purpose:** Start, pause and stop tasks; hotkeys let you control everything without switching back to FlowTap.

- Bottom bar **▶ 全部开始 / ⏸ 全部暂停 / ■ 全部停止** (pause keeps progress and countdowns, stop resets them)
- Per-card **▶ 开始 / ■ 停止**, starts with a countdown (3s default, configurable in Settings, 0 disables)
- Global hotkeys **F7 start / F8 stop** — works anywhere, even in games (rebindable in Settings)
- **◀/▶** on the card title row collapses or expands the card

### 7. Window binding

**Purpose:** Locks a task to its target window — it only acts while that window is focused, so nothing gets pressed into other programs when you switch away.

Settings → 功能设置 → **"捕获窗口"**: once bound, the task only runs while the target window is in the foreground — it waits when you switch away and resumes when you come back. Click **"解除"** to unbind.

### 8. Presets

**Purpose:** Save a whole task setup for reuse — switch setups with one click across games or scenes, and carry them to another machine.

- Use the dropdown at the top of a card to **load / save / delete** presets; loading asks for confirmation so current tasks aren't overwritten
- Settings → 功能设置 → **导出预设 / 导入预设**: back up all presets as JSON and merge them on another machine

### 9. Mini mode & settings

**Purpose:** How FlowTap sits in the background while farming, plus appearance and behavior personalization.

- The **"—"** button on the title bar minimizes to a borderless floating mini window, start/stop stays in sync with the main window
- Settings is split into **外观设置** (window title, opacity, always-on-top, remember window height, theme) and **功能设置** (global hotkeys, new-task defaults, start countdown, image matching, window binding, preset backup); changes apply right away, the theme needs **"✓ 应用主题"** at the bottom to rebuild the interface

## Changelog

Full version history and detailed release notes → **[CHANGELOG.md](CHANGELOG.md)**

## License

Personal project. For learning purposes only.
