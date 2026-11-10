param([Parameter(Mandatory)][string]$Destination)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$release = Join-Path $repo 'flutter_app/build/windows/x64/runner/Release'
$pythonHome = python -c 'import sys; print(sys.base_prefix)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 x64 is required to package Aurora' }

$python = Join-Path $Destination 'runtime/python'
$engine = Join-Path $Destination 'runtime/engine'
$app = Join-Path $engine 'flutter_app'
$android = Join-Path $app 'android/app/src/main'
New-Item -ItemType Directory -Force -Path $Destination, "$python/Lib/site-packages", "$app/desktop", "$android/python", "$android/assets" | Out-Null
Copy-Item "$release/*" $Destination -Recurse
Get-ChildItem $pythonHome -File |
  Where-Object Name -Match '^(python\.exe|python\d*\.dll|vcruntime.*\.dll|LICENSE\.txt)$' |
  Copy-Item -Destination $python
Copy-Item "$pythonHome/DLLs" $python -Recurse
Get-ChildItem "$pythonHome/Lib" -Exclude 'site-packages', '__pycache__', 'test' |
  Copy-Item -Destination "$python/Lib" -Recurse
& "$pythonHome/python.exe" -m pip install --only-binary=:all: --target "$python/Lib/site-packages" -r "$repo/requirements-core.txt" Pillow
if ($LASTEXITCODE -ne 0) { throw 'Installing Aurora runtime dependencies failed' }

Get-ChildItem $repo -File -Filter '*.py' -Exclude 'test_*.py', 'conftest.py' |
  Copy-Item -Destination $engine
foreach ($directory in 'aurora_internal', 'aurora_manifold_directory', 'aurora_genealogy') {
  Copy-Item "$repo/$directory" $engine -Recurse
}
Copy-Item "$repo/flutter_app/desktop/aurora_desktop_host.py" "$app/desktop"
$bridge = "$repo/flutter_app/android/app/src/main"
Copy-Item "$bridge/python/aurora_bridge.py", "$bridge/python/aurora_historical_experience_environment.py" "$android/python"
Copy-Item "$bridge/assets/aurora_experiential_baseline_v1.zip" "$android/assets"

# App-local Visual C++ redistributables from the same Visual Studio toolchain.
$vswhere = "${env:ProgramFiles(x86)}/Microsoft Visual Studio/Installer/vswhere.exe"
$visualStudio = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$crt = Get-ChildItem "$visualStudio/VC/Redist/MSVC/*/x64/Microsoft.VC143.CRT" -Directory |
  Sort-Object { [version]$_.Parent.Parent.Name } -Descending | Select-Object -First 1
if (!$crt) { throw 'Visual C++ x64 redistributables were not found' }
Copy-Item "$($crt.FullName)/*.dll" $Destination
