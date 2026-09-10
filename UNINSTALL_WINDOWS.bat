@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\UNINSTALL_WINDOWS.ps1"
pause
