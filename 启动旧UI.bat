@echo off
rem Legacy UI launcher. Runs main.py -> ui.app.App (v1 UI).
rem Uses the same Python as "Start New UI.bat" for consistency.
set "PY=C:\Users\KuangYu\AppData\Local\Programs\Python\Python312\python.exe"
set "PYW=C:\Users\KuangYu\AppData\Local\Programs\Python\Python312\pythonw.exe"
cd /d "%~dp0"
set PYTHONPATH=
if not exist "%PY%" goto nopy
rem pythonw hides console; on failure run python.exe to see the error.
start "" "%PYW%" -m main
exit /b
:nopy
echo Python not found at:
echo   %PY%
echo Install PySide6 there, or edit this bat to point at your Python.
pause
