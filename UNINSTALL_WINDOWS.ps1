$ErrorActionPreference = "Continue"

$names = @(
    "CodexUsageWatcher",
    "CodexUsageHiddenV27",
    "CodexUsageHeadlessV26",
    "CodexUsageWatcherV2",
    "CodexUsageHelperV24",
    "CodexUsageCaptureV24",
    "CodexUsageHelperV25",
    "CodexUsageCaptureV25"
)

foreach ($name in $names) {
    try {
        $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        if ($null -ne $task) {
            Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction Stop
            Write-Host "Eliminada: $name"
        }
    } catch {}
}

Write-Host ""
Write-Host "Automatización eliminada."
Write-Host "Los datos, config.json y perfil dedicado NO fueron borrados."
