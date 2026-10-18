@echo off

set "source=%~dp0"
set "target=%USERPROFILE%\.claude\skills\calm-git"

echo Deploying to %target%
mkdir "%target%" 2>nul
call :copy_file SKILL.md
call :copy_file calm_git.sh

rem pause
exit /b

:copy_file
copy /y "%source%%~1" "%target%\%~1" >nul && (echo copied  %~1) || (echo FAILED  %~1)
exit /b
