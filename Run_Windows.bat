@echo off
:: Wrapper to make it obvious for Windows Users
SETLOCAL EnableDelayedExpansion
CD /D "%~dp0"
CALL start_dashboard.bat
EXIT /B %ERRORLEVEL%
