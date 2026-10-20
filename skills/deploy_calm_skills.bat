@echo off

rem Deploys every calm skill, one after the other.
for /d %%d in ("%~dp0calm-*") do (
  if exist "%%d\deploy.bat" (
    echo.
    call "%%d\deploy.bat"
  )
)

rem The token counter and the glyph renderer carry no calm- name, so they are named here.
echo.
call "%~dp0token-counter\deploy.bat"
echo.
call "%~dp0unicode-glyph-render\deploy.bat"
echo.
call "%~dp0hallmark\deploy.bat"

rem pause
