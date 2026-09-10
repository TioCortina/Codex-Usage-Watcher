param(
    [string]$AppDir
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AppDir)) {
    $AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$PythonW = Join-Path $AppDir ".venv\Scripts\pythonw.exe"
$Capture = Join-Path $AppDir "codex_hidden_capture.py"
$TaskName = "CodexUsageWatcher"

if (-not (Test-Path $PythonW)) {
    throw "No existe pythonw.exe en .venv"
}

function Remove-TaskSafe {
    param([string]$Name)
    try {
        $task = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
        if ($null -ne $task) {
            Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction Stop
            Write-Host "  Eliminada tarea antigua: $Name"
        }
    }
    catch {
        Write-Warning "No pude eliminar '$Name': $($_.Exception.Message)"
    }
}

$OldTasks = @(
    "CodexUsageWatcher",
    "CodexUsageHiddenV27",
    "CodexUsageHeadlessV26",
    "CodexUsageWatcherV2",
    "CodexUsageHelperV24",
    "CodexUsageCaptureV24",
    "CodexUsageHelperV25",
    "CodexUsageCaptureV25"
)

foreach ($name in $OldTasks) {
    Remove-TaskSafe -Name $name
}

$Action = New-ScheduledTaskAction `
    -Execute $PythonW `
    -Argument "`"$Capture`"" `
    -WorkingDirectory $AppDir

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 10)

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Codex Usage Watcher v3.0 Windows - Brave oculto cada 10 minutos" `
    -Force | Out-Null

Write-Host "OK: tarea '$TaskName' instalada cada 10 minutos."
