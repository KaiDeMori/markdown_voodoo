@echo off
setlocal

set "venv_python=%~dp0.venv\Scripts\python.exe"

if not exist "%venv_python%" (
    echo Python venv not found: "%venv_python%"
    echo See docs\Setup.md for the core install.
    pause
    exit /b 1
)

"%venv_python%" -m pip install -U yt-dlp
if errorlevel 1 (
    echo yt-dlp update failed.
    pause
    exit /b 1
)

echo.
echo Installed yt-dlp version:
"%venv_python%" -m yt_dlp --version

pause
endlocal
