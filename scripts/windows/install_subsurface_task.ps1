# Authors: Sunni (Sir) Morningstar & Cael Devo
# Registers the Aurora Subsurface as a Windows Scheduled Task that starts at
# logon and keeps running with no window open (FIX-A118).  The Windows
# counterpart of deploy/aurora-subsurface.service.
#   Install:  powershell -ExecutionPolicy Bypass -File scripts\windows\install_subsurface_task.ps1
#   Remove:   Unregister-ScheduledTask -TaskName "AuroraSubsurface" -Confirm:$false
# NOT YET RUN ON WINDOWS.
$ErrorActionPreference = "Stop"
$repo   = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runner = Join-Path $repo "scripts\windows\run_subsurface.bat"
$action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$runner`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden
Register-ScheduledTask -TaskName "AuroraSubsurface" -Action $action -Trigger $trigger `
    -Settings $settings -Description "Aurora persistent Subsurface" -Force | Out-Null
Start-ScheduledTask -TaskName "AuroraSubsurface"
Write-Host "AuroraSubsurface task installed and started."
Write-Host "Log: $repo\aurora_state\strata_stack\logs\subsurface.log"
