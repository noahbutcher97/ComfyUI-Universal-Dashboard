@echo off
SETLOCAL EnableDelayedExpansion

TITLE ComfyUI Universal Dashboard
ECHO ========================================================
ECHO    ComfyUI Universal Dashboard (Windows)
ECHO ========================================================

:: 1. Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Python is not installed or not in PATH.
    ECHO Please install Python 3.10+ from python.org and try again.
    ECHO Make sure to check "Add Python to PATH" during installation.
    PAUSE
    EXIT /B 1
)

:: 2. Setup Dashboard Environment
SET DASH_DIR=%USERPROFILE%\.comfy_dashboard
IF NOT EXIST "%DASH_DIR%" MKDIR "%DASH_DIR%"

IF NOT EXIST "%DASH_DIR%\venv" (
    ECHO [INIT] Creating local environment...
    python -m venv "%DASH_DIR%\venv"
)

:: 3. Install Dependencies
ECHO [INIT] Checking dependencies...
"%DASH_DIR%\venv\Scripts\pip.exe" install rich psutil >nul 2>&1

:: 4. Run Dashboard
ECHO [INFO] Launching Dashboard...
"%DASH_DIR%\venv\Scripts\python.exe" dashboard.py

PAUSE
