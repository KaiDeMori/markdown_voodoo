@echo off

rem Deploys every calm skill, one after the other.
for /d %%d in ("%~dp0calm-*") do (
  if exist "%%d\deploy.bat" (
    echo.
    call "%%d\deploy.bat"
  )
)

echo.
call "%~dp0hallmark\deploy.bat"
echo.
call "%~dp0token-counter\deploy.bat"
echo.
call "%~dp0unicode-glyph-render\deploy.bat"
echo.
call "%~dp0self-flow\deploy.bat"
echo.
call "%~dp0calm-test\deploy.bat"

pause
