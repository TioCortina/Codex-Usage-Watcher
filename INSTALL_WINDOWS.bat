@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Codex Usage Watcher v3.1 - Instalador Windows
cd /d "%~dp0"

echo.
echo ============================================================
echo       CODEX USAGE WATCHER v3.1 - WINDOWS
echo              INSTALACION AUTOMATICA
echo ============================================================
echo.
echo Navegadores compatibles:
echo   - Brave
echo   - Google Chrome
echo   - Microsoft Edge
echo.
echo El instalador usa el navegador predeterminado si es compatible.
echo Si hace falta, podras elegir sin salir de este BAT.
echo.

set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PY_CMD=py"
if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [1/8] Python no encontrado. Intentando instalar Python 3.12 con winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo ERROR: instala Python 3.11 o superior.
        pause
        exit /b 1
    )
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo ERROR: winget no pudo instalar Python.
        pause
        exit /b 1
    )
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    where python >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
    where py >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py"
    if not defined PY_CMD (
        echo Python se instalo, pero esta consola aun no lo ve.
        echo Cierra esta ventana y ejecuta INSTALL_WINDOWS.bat nuevamente.
        pause
        exit /b 1
    )
) else (
    echo [1/8] Python encontrado.
)

echo [2/8] Comprobando navegadores compatibles...
set "BROWSER_FOUND=0"
if exist "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BROWSER_FOUND=1"
if exist "%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER_FOUND=1"
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER_FOUND=1"
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER_FOUND=1"
if exist "%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe" set "BROWSER_FOUND=1"

if "%BROWSER_FOUND%"=="0" (
    echo No encontre Brave, Chrome ni Edge. Intentando instalar Microsoft Edge...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo ERROR: instala Brave, Google Chrome o Microsoft Edge.
        pause
        exit /b 1
    )
    winget install -e --id Microsoft.Edge --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo ERROR: instala manualmente Brave, Google Chrome o Microsoft Edge.
        pause
        exit /b 1
    )
)

echo [3/8] Preparando entorno Python...
if not exist ".venv\Scripts\python.exe" (
    %PY_CMD% -m venv ".venv"
    if errorlevel 1 (
        echo ERROR creando el entorno virtual.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet --upgrade pip
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements.txt
if errorlevel 1 (
    echo ERROR instalando dependencias.
    pause
    exit /b 1
)

echo [4/8] Preparando configuracion y ntfy...
".venv\Scripts\python.exe" bootstrap_windows.py
if errorlevel 1 (
    echo ERROR preparando configuracion.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" configure_ntfy.py --ensure
if errorlevel 1 (
    echo ERROR preparando ntfy.
    pause
    exit /b 1
)

echo.
echo [5/8] Seleccionando navegador...
".venv\Scripts\python.exe" configure_browser.py --ensure --interactive
if errorlevel 1 (
    echo ERROR seleccionando navegador.
    pause
    exit /b 1
)

echo.
echo [6/8] Probando captura invisible...
".venv\Scripts\python.exe" installer_test_capture.py
set "TEST_RC=!errorlevel!"

if "!TEST_RC!"=="0" (
    echo       Captura invisible: OK
    goto :INSTALL_TASK
)

if not "!TEST_RC!"=="20" (
    echo ERROR: la prueba fallo. Revisa hidden_last_run.json.
    pause
    exit /b !TEST_RC!
)

echo.
echo El perfil dedicado necesita autenticacion o verificacion.
echo Se abrira UNA SOLA VEZ el navegador seleccionado.
".venv\Scripts\python.exe" open_auth_profile_windows.py
if errorlevel 1 (
    echo ERROR abriendo el perfil dedicado.
    pause
    exit /b 1
)

echo.
echo ------------------------------------------------------------
echo EN EL NAVEGADOR:
echo   1. Inicia sesion en ChatGPT si te lo pide.
echo   2. Espera hasta ver los porcentajes de Codex Usage.
echo   3. CIERRA COMPLETAMENTE esa ventana.
echo ------------------------------------------------------------
echo.
pause

echo [7/8] Repitiendo prueba invisible...
".venv\Scripts\python.exe" installer_test_capture.py
if errorlevel 1 (
    echo ERROR: la captura sigue sin funcionar. Revisa hidden_last_run.json.
    pause
    exit /b 1
)
echo       Captura invisible: OK

:INSTALL_TASK
echo.
echo [8/8] Instalando automatizacion cada 10 minutos...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\install_task_windows.ps1" -AppDir "%CD%"
if errorlevel 1 (
    echo ERROR instalando la tarea de Windows.
    pause
    exit /b 1
)

start "" /b ".venv\Scripts\pythonw.exe" "codex_hidden_capture.py"

echo.
echo ============================================================
echo                    INSTALACION LISTA
echo ============================================================
echo.
echo Tarea: CodexUsageWatcher
echo Frecuencia: cada 10 minutos
echo Navegadores: Brave / Google Chrome / Microsoft Edge
echo En reposo: no queda navegador ni Python ejecutandose
echo.
echo CONFIGURE_BROWSER.bat = cambiar navegador
echo CONFIGURE_NTFY.bat    = configurar/probar notificaciones
echo STATUS_WINDOWS.bat    = revisar estado
echo UNINSTALL_WINDOWS.bat = quitar automatizacion
echo.
pause
exit /b 0
