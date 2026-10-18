@echo off

set "source=%~dp0"
set "target=%USERPROFILE%\.claude\skills\token-counter"

echo Deploying to %target%
mkdir "%target%" 2>nul
call :copy_file SKILL.md
call :copy_file token_counter.py
call :copy_file token_counter.sh
call :copy_file requirements.txt
if exist "%source%hall_key.txt" (
    call :copy_file hall_key.txt
) else (
    echo skipped hall_key.txt - the key file is missing
)

if not exist "%target%\.venv\Scripts\python.exe" (
    echo Creating the venv in %target%\.venv
    "%source%.venv\Scripts\python.exe" -m venv "%target%\.venv"
)
echo Installing requirements
"%target%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r "%target%\requirements.txt"

rem pause
exit /b

:copy_file
copy /y "%source%%~1" "%target%\%~1" >nul && (echo copied  %~1) || (echo FAILED  %~1)
exit /b
