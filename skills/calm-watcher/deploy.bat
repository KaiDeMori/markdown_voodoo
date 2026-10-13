@echo off

set "source=%~dp0"
set "target=%USERPROFILE%\.claude\skills\calm-watcher"

echo Deploying to %target%
call :copy_file SKILL.md

if not exist "%target%\.venv\Scripts\python.exe" (
    echo Creating the venv in %target%\.venv
    "%source%.venv\Scripts\python.exe" -m venv "%target%\.venv"
)
echo Installing requirements
"%target%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r "%target%\requirements.txt"

pause
exit /b

:copy_file
copy /y "%source%%~1" "%target%\%~1" >nul && (echo copied  %~1) || (echo FAILED  %~1)
exit /b
