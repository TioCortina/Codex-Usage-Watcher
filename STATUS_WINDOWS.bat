@echo off
cd /d "%~dp0"
echo.
echo ============================================================
echo CODEX USAGE WATCHER - ESTADO
echo ============================================================
echo.
powershell -NoProfile -Command "$t=Get-ScheduledTask -TaskName 'CodexUsageWatcher' -ErrorAction SilentlyContinue; if($t){Write-Host 'Tarea:' $t.TaskName '-' $t.State}else{Write-Host 'Tarea: NO INSTALADA'}"
echo.
if exist hidden_last_run.json (
  type hidden_last_run.json
) else (
  echo hidden_last_run.json aun no existe.
)
echo.
pause
