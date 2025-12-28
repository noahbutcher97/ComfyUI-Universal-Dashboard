@echo off
SETLOCAL EnableDelayedExpansion

TITLE ComfyUI Universal Dashboard
ECHO ========================================================
ECHO    ComfyUI Universal Dashboard (Windows)
ECHO ========================================================

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Python is not installed or not in PATH.
    ECHO Please install Python 3.10+ from python.org.
    PAUSE
    EXIT /B 1
)

:: Setup in .dashboard_env folder in root
SET DASH_ROOT=%~dp0..
SET DASH_ENV=%DASH_ROOT%\.dashboard_env

IF NOT EXIST "%DASH_ENV%" MKDIR "%DASH_ENV%"

IF NOT EXIST "%DASH_ENV%\venv" (
    ECHO [INIT] Creating local environment...
    python -m venv "%DASH_ENV%\venv"
)

ECHO [INIT] Checking dependencies...
"%DASH_ENV%\venv\Scripts\pip.exe" install customtkinter psutil requests keyring >nul 2>&1

ECHO [INFO] Launching Dashboard...
"%DASH_ENV%\venv\Scripts\python.exe" "%DASH_ROOT%\src\main.py"

IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO [ERROR] Dashboard exited with error code %ERRORLEVEL%.
    PAUSE
)
