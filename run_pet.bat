@echo off
title Antigravity Desktop Pet
cd /d "%~dp0"

REM 1. Check local virtual environment if bundled
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" main.py %*
    goto :end
)

REM 2. Check user environment
if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe" (
    "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe" main.py %*
    goto :end
)

REM 3. Fallback to system Python or py launcher
where python >nul 2>nul
if %errorlevel% equ 0 (
    python main.py %*
    goto :end
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 main.py %*
    goto :end
)

echo [ERROR] Python not found on this system. Please install Python 3.9+ from python.org!
pause

:end
