@echo off
cd /d "%~dp0"
echo.
echo ============================================================
echo CODEX USAGE WATCHER - ESTADO
echo ============================================================
echo.
powershell -NoProfile -Command "$t=Get-ScheduledTask -TaskName 'CodexUsageWatcher' -ErrorAction SilentlyContinue; if($t){Write-Host 'Tarea:' $t.TaskName '-' $t.State}else{Write-Host 'Tarea: NO INSTALADA'}"
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import json; from pathlib import Path; p=Path('config.json'); d=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}; print('Navegador:', (d.get('browser') or {}).get('selected') or 'sin seleccionar')"
)
echo.
if exist hidden_last_run.json (
  type hidden_last_run.json
) else (
  echo hidden_last_run.json aun no existe.
)
echo.
pause
