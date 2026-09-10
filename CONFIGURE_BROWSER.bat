@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta INSTALL_WINDOWS.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" configure_browser.py
echo.
echo Si cambiaste de navegador, ejecuta INSTALL_WINDOWS.bat para autenticar
echo el perfil dedicado y validar la captura.
echo.
pause
