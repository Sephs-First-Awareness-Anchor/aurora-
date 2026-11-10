@echo off
setlocal
cd /d "%~dp0"
where flutter >nul 2>nul || (echo Install Flutter 3.22.3 and add it to PATH. & exit /b 1)
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv || exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-core.txt Pillow || exit /b 1
set "AURORA_DESKTOP_PYTHON=%CD%\.venv\Scripts\python.exe"
set "AURORA_DESKTOP_HOST=%CD%\flutter_app\desktop\aurora_desktop_host.py"
cd flutter_app
call flutter run -d windows --release
exit /b %ERRORLEVEL%
