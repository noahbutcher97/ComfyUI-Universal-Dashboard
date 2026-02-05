@echo off
setlocal enabledelayedexpansion

:: Import Claude Code plans to docs/plans/
:: Usage: import-plan.bat [latest|all|any|filename]
::   latest  - Import most recent plan for THIS PROJECT (default)
::   all     - Import all plans for this project
::   any     - Import most recent plan regardless of project
::   <name>  - Import specific plan by filename
::
:: Project detection: Searches plan content for "AI Universal Suite"
:: Output format: claude-plan_MM-DD-YY.md

set "CLAUDE_PLANS=%USERPROFILE%\.claude\plans"
set "TARGET_DIR=%~dp0..\..\docs\plans"
set "PROJECT_NAME=AI Universal Suite"
set "FILE_PREFIX=claude-plan"
set "MODE=%~1"

if "%MODE%"=="" set "MODE=latest"

:: Ensure target directory exists
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

:: Check if source directory exists
if not exist "%CLAUDE_PLANS%" (
    echo Error: Claude plans directory not found at %CLAUDE_PLANS%
    exit /b 1
)

if /i "%MODE%"=="latest" (
    call :import_latest_project
) else if /i "%MODE%"=="all" (
    call :import_all_project
) else if /i "%MODE%"=="any" (
    call :import_latest_any
) else (
    call :import_specific "%MODE%"
)

exit /b 0

:import_latest_project
echo Searching for most recent "%PROJECT_NAME%" plan...
set "LATEST="

:: Find plans containing project name, get most recent
for /f "delims=" %%F in ('dir /b /o-d "%CLAUDE_PLANS%\*.md" 2^>nul') do (
    set "FILEPATH=%CLAUDE_PLANS%\%%F"
    findstr /i /c:"%PROJECT_NAME%" "!FILEPATH!" >nul 2>&1
    if !errorlevel! equ 0 (
        if not defined LATEST (
            set "LATEST=!FILEPATH!"
            echo Found: %%F
        )
    )
)

if not defined LATEST (
    echo No plans found for "%PROJECT_NAME%"
    echo.
    echo Available plans:
    dir /b "%CLAUDE_PLANS%\*.md" 2>nul
    echo.
    echo Use "import-plan.bat any" to import any plan regardless of project
    exit /b 1
)

call :process_file "%LATEST%"
goto :eof

:import_latest_any
echo Importing most recent Claude plan (any project)...
set "LATEST="

for /f "delims=" %%F in ('dir /b /o-d "%CLAUDE_PLANS%\*.md" 2^>nul') do (
    if not defined LATEST set "LATEST=%CLAUDE_PLANS%\%%F"
)

if not defined LATEST (
    echo No plans found in %CLAUDE_PLANS%
    exit /b 1
)

call :process_file "%LATEST%"
goto :eof

:import_all_project
echo Importing all "%PROJECT_NAME%" plans...
set "COUNT=0"

for /f "delims=" %%F in ('dir /b /o-d "%CLAUDE_PLANS%\*.md" 2^>nul') do (
    set "FILEPATH=%CLAUDE_PLANS%\%%F"
    findstr /i /c:"%PROJECT_NAME%" "!FILEPATH!" >nul 2>&1
    if !errorlevel! equ 0 (
        call :process_file "!FILEPATH!"
        set /a COUNT+=1
    )
)

echo Imported !COUNT! plan(s) for "%PROJECT_NAME%"
goto :eof

:import_specific
set "FILENAME=%~1"
set "FILEPATH=%CLAUDE_PLANS%\%FILENAME%"

if not exist "%FILEPATH%" (
    :: Try with .md extension
    set "FILEPATH=%CLAUDE_PLANS%\%FILENAME%.md"
)

if not exist "%FILEPATH%" (
    echo Error: Plan not found: %FILENAME%
    echo.
    echo Available plans:
    dir /b "%CLAUDE_PLANS%\*.md" 2>nul
    exit /b 1
)

call :process_file "%FILEPATH%"
goto :eof

:process_file
set "SRCFILE=%~1"
set "SRCNAME=%~nx1"

:: Get file date for suffix
for %%A in ("%SRCFILE%") do set "FILEDATE=%%~tA"

:: Extract date (format: MM/DD/YYYY -> MM-DD-YY)
for /f "tokens=1-3 delims=/ " %%a in ("%FILEDATE%") do (
    set "MONTH=%%a"
    set "DAY=%%b"
    set "YEAR=%%c"
)

:: Ensure 2-digit month/day
if "!MONTH:~1,1!"=="" set "MONTH=0!MONTH!"
if "!DAY:~1,1!"=="" set "DAY=0!DAY!"

:: Get last 2 digits of year
set "YEAR=!YEAR:~-2!"

set "DATESUFFIX=!MONTH!-!DAY!-!YEAR!"

:: Format: PROJECTNAME_DATE.md
set "DESTNAME=%FILE_PREFIX%_!DATESUFFIX!.md"
set "DESTPATH=%TARGET_DIR%\!DESTNAME!"

:: Check if destination already exists - add counter if so
set "COUNTER=0"
:check_exists
if exist "!DESTPATH!" (
    set /a COUNTER+=1
    set "DESTNAME=%FILE_PREFIX%_!DATESUFFIX!_!COUNTER!.md"
    set "DESTPATH=%TARGET_DIR%\!DESTNAME!"
    goto :check_exists
)

copy "%SRCFILE%" "!DESTPATH!" >nul
echo Imported: %SRCNAME% -^> !DESTNAME!
goto :eof
