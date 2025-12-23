@echo off
SETLOCAL EnableDelayedExpansion
CD /D "%~dp0"
CALL bin\boot_windows.bat
EXIT /B %ERRORLEVEL%
