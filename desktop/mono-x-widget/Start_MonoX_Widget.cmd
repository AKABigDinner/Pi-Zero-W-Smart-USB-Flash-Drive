@echo off
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Install Python 3 with Tk support and Pillow first: py -m pip install Pillow
  pause
  exit /b 1
)
start "" pythonw "%~dp0mono_x_widget.py"
