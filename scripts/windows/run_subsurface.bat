@echo off
rem Authors: Sunni (Sir) Morningstar & Cael Devo
rem Aurora Subsurface on Windows (FIX-A118).  Mirrors scripts/run_subsurface_daemon.sh.
rem NOT YET RUN ON WINDOWS: the daemon was developed on Linux.  The first run
rem here is the test; send the log (aurora_state\strata_stack\logs\subsurface.log).
setlocal
cd /d "%~dp0..\.."
set AURORA_SKIP_DEP_INSTALL=1
set AURORA_DAEMON_LOCK_NAME=aurora_subsurface_daemon
set AURORA_DAEMON_LABEL=aurora-subsurface
set AURORA_ALLOW_X_CLIENTS=0
set AURORA_ENABLE_ROOM_OPERATOR=0
set AURORA_ENABLE_QUIET_WINDOW=0
set PYTHONUNBUFFERED=1
set PYTHONUTF8=1
if not exist "aurora_state\strata_stack\logs" mkdir "aurora_state\strata_stack\logs"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
:loop
"%PY%" aurora_subsurface_daemon.py >> "aurora_state\strata_stack\logs\subsurface.log" 2>&1
rem Restart after an unexpected exit, like systemd Restart=always / RestartSec=10.
timeout /t 10 /nobreak >nul
goto loop
