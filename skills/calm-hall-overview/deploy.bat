@echo off

set "source=%~dp0"
set "target=%USERPROFILE%\.claude\skills\calm-hall-overview"

echo Deploying to %target%

mkdir "%target%" 2>nul

call :copy_file SKILL.md
call :copy_file calm_hall_overview.sh
call :copy_file read_haven_location.py
call :copy_file calm_hall_overview_settings.json
call :copy_file hall_overview_visibility.txt

rem pause
exit /b

:copy_file
copy /y "%source%%~1" "%target%\%~1" >nul && (echo copied  %~1) || (echo FAILED  %~1)
exit /b
