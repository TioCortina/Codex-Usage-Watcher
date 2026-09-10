@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Codex Usage Watcher v3.0 - Instalador Windows
cd /d "%~dp0"

echo.
echo ============================================================
echo       CODEX USAGE WATCHER v3.0 - WINDOWS
echo              INSTALACION AUTOMATICA
echo ============================================================
echo.
echo Este instalador:
echo   - prepara Python y dependencias
echo   - conserva/migra tu config y ntfy
echo   - reutiliza tu perfil dedicado de Brave
echo   - prueba la captura invisible
echo   - instala la tarea automatica cada 10 minutos
echo.
echo No instala nada de macOS.
echo.

REM ------------------------------------------------------------
REM 1) Encontrar Python. Si falta, intentar instalarlo con winget.
REM ------------------------------------------------------------
set "PY_CMD="

where py >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py"
)

if not defined PY_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo [1/7] Python no encontrado. Intentando instalar Python 3 con winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ERROR: Python no esta instalado y winget no esta disponible.
        echo Instala Python 3.11 o superior y vuelve a ejecutar este BAT.
        echo.
        pause
        exit /b 1
    )

    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo ERROR: winget no pudo instalar Python.
        pause
        exit /b 1
    )

    REM Refrescar PATH de la sesion actual de forma simple.
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

    where python >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
    where py >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py"

    if not defined PY_CMD (
        echo Python se instalo, pero esta consola aun no lo ve.
        echo Cierra esta ventana y vuelve a ejecutar INSTALL_WINDOWS.bat.
        pause
        exit /b 1
    )
) else (
    echo [1/7] Python encontrado.
)

REM ------------------------------------------------------------
REM 2) Brave
REM ------------------------------------------------------------
echo [2/7] Comprobando Brave...
set "BRAVE_FOUND=0"
if exist "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE_FOUND=1"
if exist "%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE_FOUND=1"
if exist "%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE_FOUND=1"

if "%BRAVE_FOUND%"=="0" (
    echo Brave no encontrado. Intentando instalarlo con winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Brave no esta instalado y winget no esta disponible.
        pause
        exit /b 1
    )
    winget install -e --id Brave.Brave --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo ERROR: No pude instalar Brave automaticamente.
        pause
        exit /b 1
    )
) else (
    echo       Brave encontrado.
)

REM ------------------------------------------------------------
REM 3) venv
REM ------------------------------------------------------------
echo [3/7] Preparando entorno Python...
if not exist ".venv\Scripts\python.exe" (
    %PY_CMD% -m venv ".venv"
    if errorlevel 1 (
        echo ERROR creando el entorno virtual.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet --upgrade pip
if errorlevel 1 (
    echo ERROR actualizando pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements.txt
if errorlevel 1 (
    echo ERROR instalando dependencias.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM 4) Config + profile migration
REM ------------------------------------------------------------
echo [4/7] Preparando configuracion, ntfy y perfil dedicado...
".venv\Scripts\python.exe" bootstrap_windows.py
if errorlevel 1 (
    echo ERROR preparando configuracion.
    pause
    exit /b 1
)

echo.
echo Configurando notificaciones ntfy...
".venv\Scripts\python.exe" configure_ntfy.py --ensure
if errorlevel 1 (
    echo ERROR preparando ntfy.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM 5) First invisible test
REM ------------------------------------------------------------
echo.
echo [5/7] Probando captura invisible...
".venv\Scripts\python.exe" installer_test_capture.py
set "TEST_RC=!errorlevel!"

if "!TEST_RC!"=="0" (
    echo       Captura invisible: OK
    goto :INSTALL_TASK
)

if not "!TEST_RC!"=="20" (
    echo.
    echo ERROR: la prueba fallo por un problema tecnico.
    echo Revisa hidden_last_run.json.
    echo.
    pause
    exit /b !TEST_RC!
)

REM ------------------------------------------------------------
REM Authentication only if needed
REM ------------------------------------------------------------
echo.
echo La captura necesita autenticar/verificar el perfil dedicado.
echo Se abrira Brave UNA SOLA VEZ de forma visible.
echo.
".venv\Scripts\python.exe" open_auth_profile_windows.py
if errorlevel 1 (
    echo ERROR abriendo el perfil dedicado.
    pause
    exit /b 1
)

echo.
echo ------------------------------------------------------------
echo EN BRAVE:
echo   1. Inicia sesion en ChatGPT si te lo pide.
echo   2. Espera a ver los porcentajes de Codex Usage.
echo   3. CIERRA COMPLETAMENTE esa ventana de Brave.
echo ------------------------------------------------------------
echo.
pause

echo.
echo [6/7] Repitiendo prueba invisible...
".venv\Scripts\python.exe" installer_test_capture.py
if errorlevel 1 (
    echo.
    echo ERROR: la captura invisible sigue sin funcionar.
    echo Revisa hidden_last_run.json.
    echo.
    pause
    exit /b 1
)

echo       Captura invisible: OK

:INSTALL_TASK
REM ------------------------------------------------------------
REM 7) Scheduled task
REM ------------------------------------------------------------
echo.
echo [7/7] Instalando automatizacion cada 10 minutos...
powershell -NoProfile -ExecutionPolicy Bypass -File ".\install_task_windows.ps1" -AppDir "%CD%"
if errorlevel 1 (
    echo.
    echo ERROR instalando la tarea de Windows.
    pause
    exit /b 1
)

REM Launch final background sample with pythonw.
start "" /b ".venv\Scripts\pythonw.exe" "codex_hidden_capture.py"

echo.
echo ============================================================
echo                    INSTALACION LISTA
echo ============================================================
echo.
echo Tarea: CodexUsageWatcher
echo Frecuencia: cada 10 minutos
echo Navegador: Brave normal oculto
echo En reposo: no queda Brave ni Python ejecutandose
echo ntfy: topic local creado o conservado automaticamente
echo Para cambiarlo o probarlo: CONFIGURE_NTFY.bat
echo.
echo Puedes usar STATUS_WINDOWS.bat para revisar el estado.
echo.
pause
exit /b 0
