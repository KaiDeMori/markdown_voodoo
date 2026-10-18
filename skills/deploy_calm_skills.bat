@echo off

rem Deploys every calm skill, one after the other.
for /d %%d in ("%~dp0calm-*") do (
  if exist "%%d\deploy.bat" (
    echo.
    call "%%d\deploy.bat"
  )
)

rem pause
