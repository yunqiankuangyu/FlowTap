@echo off
rem 新 UI 独立版 —— 与 ui/ 完全隔离, 不引用旧目录任何代码
rem 用 -m 方式启动: ui_v2 内部是相对导入, 以脚本方式直接跑会找不到同包模块
set "PY=C:\Users\KuangYu\AppData\Local\Programs\Python\Python312\python.exe"
set "PYW=C:\Users\KuangYu\AppData\Local\Programs\Python\Python312\pythonw.exe"
cd /d "%~dp0"
set PYTHONPATH=
if not exist "%PY%" goto nopy
rem pythonw 无控制台; 失败时回落到 python.exe 看报错
start "" "%PYW%" -m ui_v2.main_v2
exit /b
:nopy
echo Python not found at:
echo   %PY%
echo Install PySide6 there, or edit this bat to point at your Python.
pause
