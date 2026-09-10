@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta INSTALL_WINDOWS.bat primero.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" configure_ntfy.py
pause
