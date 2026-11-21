param(
    [string]$StateDir = (Join-Path $env:LOCALAPPDATA 'Aurora\state'),
    [switch]$StartNow,
    [switch]$InstallBrowser
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    & py -3.11 -m venv (Join-Path $repo '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 x64 is required.' }
}
& $python -m pip install -r (Join-Path $repo 'requirements-desktop.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if ($InstallBrowser) {
    & $python -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed.' }
}
New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
# The owner token, personal state and local console belong only to this login.
& icacls.exe $StateDir /inheritance:r /grant:r "$($env:USERDOMAIN)\$($env:USERNAME):(OI)(CI)F" /grant:r 'SYSTEM:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the state directory ACL.' }
$config = Join-Path $StateDir 'desktop_config.json'
if (-not (Test-Path $config)) {
    @{AURORA_STRATA_LINK_HOST='127.0.0.1'; AURORA_STRATA_LINK_PORT=8791; AURORA_ACM_BRIDGE='0'} |
        ConvertTo-Json | Set-Content -Encoding UTF8 $config
}
# Retire the earlier competing restart loop before installing one resident task.
$legacy = Get-ScheduledTask -TaskName 'AuroraSubsurface' -ErrorAction SilentlyContinue
if ($legacy) {
    if ($legacy.State -eq 'Running') { throw 'Stop the legacy Subsurface gracefully before installing the resident desktop.' }
    Disable-ScheduledTask -TaskName 'AuroraSubsurface' | Out-Null
}
$resident = Get-ScheduledTask -TaskName 'AuroraDesktop' -ErrorAction SilentlyContinue
if ($resident -and $resident.State -eq 'Running') { throw 'Stop the current resident before updating its scheduled task.' }
$arguments = "-m aurora_internal.desktop serve --state-dir `"$StateDir`" --open"
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'AuroraDesktop' -Action $action -Trigger $trigger -Settings $settings `
    -Description 'Aurora resident organism and primary login interface' -Force | Out-Null
if ($StartNow) { Start-ScheduledTask -TaskName 'AuroraDesktop' }
Write-Host 'AuroraDesktop installed. Existing personal state has not been replaced.'
Write-Host "State: $StateDir"
Write-Host 'Use desktop.ps1 status, open, stop, backup, or uninstall.'
