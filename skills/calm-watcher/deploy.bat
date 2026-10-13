@echo off

set "source=%~dp0"
set "target=%USERPROFILE%\.claude\skills\calm-watcher"

echo Deploying to %target%

mkdir "%target%\calm-watcher" 2>nul
call :copy_file SKILL.md
call :copy_file calm_watcher.sh

pause
exit /b

:copy_file
copy /y "%source%%~1" "%target%\%~1" >nul && (echo copied  %~1) || (echo FAILED  %~1)
exit /b
