@echo off
setlocal
cd /d "%~dp0"
set "APP_PYTHON="
if exist "%~dp0.venv\Scripts\python.exe" set "APP_PYTHON=%~dp0.venv\Scripts\python.exe"
if not defined APP_PYTHON if exist "%~dp0.venv-piano-probe\Scripts\python.exe" set "APP_PYTHON=%~dp0.venv-piano-probe\Scripts\python.exe"
if defined APP_PYTHON goto launch
where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0launch.py"
    if errorlevel 1 pause
    exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0launch.py"
    if errorlevel 1 pause
    exit /b
)
echo No local Python runtime found. Nothing was installed or downloaded.
pause
exit /b 1
:launch
"%APP_PYTHON%" "%~dp0launch.py"
if errorlevel 1 pause
endlocal
