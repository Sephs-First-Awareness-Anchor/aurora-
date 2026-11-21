param(
    [ValidateSet('open','status','start','restart','stop','backup','uninstall')][string]$Action = 'status',
    [string]$StateDir = (Join-Path $env:LOCALAPPDATA 'Aurora\state'),
    [string]$BackupDir
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repo '.venv\Scripts\python.exe'
if ($Action -in @('start','restart')) {
    $task = Get-ScheduledTask -TaskName 'AuroraDesktop' -ErrorAction Stop
    $taskAction = @($task.Actions)[0]
    if ($taskAction.Execute -ne $python -or $taskAction.Arguments -notmatch '--state-dir "([^"]+)"' -or
        [IO.Path]::GetFullPath($Matches[1]) -ne [IO.Path]::GetFullPath($StateDir)) {
        throw 'The installed task points to a different checkout or state directory.'
    }
    function Test-ResidentLock {
        $lockPath = Join-Path $StateDir 'desktop_resident.lock'
        try {
            $handle = [IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None')
            $handle.Dispose()
            return $false
        } catch [IO.IOException] { return $true }
    }
    if ($Action -eq 'restart' -and ((Test-ResidentLock) -or $task.State -eq 'Running')) {
        Push-Location $repo
        try {
            & $python -m aurora_internal.desktop stop --state-dir $StateDir
            if ($LASTEXITCODE -ne 0) { throw 'Could not request a graceful stop of this resident.' }
        } finally { Pop-Location }
        $deadline = (Get-Date).AddMinutes(3)
        while ((Test-ResidentLock) -or (Get-ScheduledTask -TaskName 'AuroraDesktop').State -eq 'Running') {
            if ((Get-Date) -ge $deadline) { throw 'Aurora is still stopping. Wait for her save, then run start.' }
            Start-Sleep -Milliseconds 400
        }
    }
    if (-not (Test-ResidentLock) -and (Get-ScheduledTask -TaskName 'AuroraDesktop').State -ne 'Running') {
        Start-ScheduledTask -TaskName 'AuroraDesktop'
    }
    Write-Host 'AuroraDesktop start requested. Use the status action to check the resident.'
    exit
}
if ($Action -in @('open','status','stop')) {
    Push-Location $repo
    try {
        & $python -m aurora_internal.desktop $Action --state-dir $StateDir
        if ($LASTEXITCODE -ne 0) { throw "Aurora $Action failed." }
    } finally { Pop-Location }
    exit
}
if ($Action -eq 'uninstall') {
    Disable-ScheduledTask -TaskName 'AuroraDesktop' -ErrorAction SilentlyContinue | Out-Null
    Write-Host 'Auto-start disabled. Stop Aurora gracefully before removing the task.'
    exit
}
if (-not $BackupDir) {
    $BackupDir = Join-Path (Split-Path $StateDir) ('backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
# Opening the runtime's advisory lock with exclusive sharing fails while it is
# held by the resident, avoiding an inconsistent live backup.
$lock = Join-Path $StateDir 'desktop_resident.lock'
$handle = [System.IO.File]::Open($lock, 'OpenOrCreate', 'ReadWrite', 'None')
try {
    if (Test-Path $BackupDir) { throw 'Backup destination already exists.' }
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
    Get-ChildItem -LiteralPath $StateDir -Force | Where-Object { $_.Name -ne 'desktop_resident.lock' } |
        Copy-Item -Destination $BackupDir -Recurse -Force
} finally { $handle.Dispose() }
Write-Host "Saved backup: $BackupDir"
