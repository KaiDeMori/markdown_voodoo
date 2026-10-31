@echo off

set "source=%~dp0"
set "target=%USERPROFILE%\.claude\skills\screaming-skills"

echo Deploying to %target%

mkdir "%target%" 2>nul

call :copy_file SKILL.md SKILL.md

rem pause
exit /b

:copy_file
copy /y "%source%%~1" "%target%\%~2" >nul && (echo copied  %~2) || (echo FAILED  %~2)
exit /b
