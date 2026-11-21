param([Parameter(Mandatory=$true)][string]$Image, [int]$Port = 4567, [switch]$Uefi, [string]$Firmware)
$ErrorActionPreference = 'Stop'
$imagePath = (Resolve-Path -LiteralPath $Image).Path
$qemu = Get-Command 'qemu-system-x86_64.exe' -ErrorAction Stop
$argsList = @('-drive', "format=raw,file=$imagePath", '-serial', "tcp:127.0.0.1:$Port,server,nowait", '-m', '64M', '-no-reboot')
if ($Uefi) {
    if (-not $Firmware) { throw 'UEFI mode requires the firmware path.' }
    $argsList += @('-bios', (Resolve-Path -LiteralPath $Firmware).Path)
}
# The resident owns the Python bridge. This launches only the existing ACM body.
& $qemu.Source @argsList
exit $LASTEXITCODE
