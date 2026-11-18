param(
    [ValidateSet('open','status','stop','backup','uninstall')][string]$Action = 'status',
    [string]$StateDir = (Join-Path $env:LOCALAPPDATA 'Aurora\state'),
    [string]$BackupDir
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $repo '.venv\Scripts\python.exe'
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
