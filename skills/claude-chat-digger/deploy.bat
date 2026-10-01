@echo off

set "target=%USERPROFILE%\.claude\skills\claude-chat-digger"

mkdir "%target%" 2>nul
copy /y "%~dp0SKILL.md" "%target%\SKILL.md"

pause
