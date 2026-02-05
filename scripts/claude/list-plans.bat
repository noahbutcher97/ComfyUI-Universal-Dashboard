@echo off
setlocal

:: List available Claude Code plans
:: Usage: list-plans.bat [claude|local|both]
::   claude - Show plans in ~/.claude/plans (default)
::   local  - Show plans in docs/plans
::   both   - Show both locations

set "CLAUDE_PLANS=%USERPROFILE%\.claude\plans"
set "LOCAL_PLANS=%~dp0..\..\docs\plans"
set "MODE=%~1"

if "%MODE%"=="" set "MODE=claude"

if /i "%MODE%"=="claude" (
    call :list_claude
) else if /i "%MODE%"=="local" (
    call :list_local
) else if /i "%MODE%"=="both" (
    call :list_claude
    echo.
    call :list_local
) else (
    echo Usage: list-plans.bat [claude^|local^|both]
    exit /b 1
)

exit /b 0

:list_claude
echo === Claude Code Plans (%CLAUDE_PLANS%) ===
if exist "%CLAUDE_PLANS%" (
    for %%F in ("%CLAUDE_PLANS%\*.md") do (
        echo   %%~nxF
    )
) else (
    echo   (directory not found)
)
goto :eof

:list_local
echo === Local Plans (%LOCAL_PLANS%) ===
if exist "%LOCAL_PLANS%" (
    for %%F in ("%LOCAL_PLANS%\*.md") do (
        echo   %%~nxF
    )
) else (
    echo   (directory not found)
)
goto :eof
