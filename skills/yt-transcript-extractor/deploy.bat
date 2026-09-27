@echo off
rem Only what Claude reads is deployed. The code, the venv and the toolchain stay in
rem this folder: SKILL.md sends every run here.

set "target=%USERPROFILE%\.claude\skills\yt-transcript-extractor"

mkdir "%target%" 2>nul
copy /y "%~dp0SKILL.md" "%target%\SKILL.md"
xcopy /e /i /y "%~dp0docs" "%target%\docs"

pause
