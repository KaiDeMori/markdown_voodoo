@echo off

set "target=%USERPROFILE%\.claude\skills\handover-protocol-setup"

mkdir "%target%" 2>nul
copy /y "%~dp0SKILL.md" "%target%\SKILL.md"
copy /y "%~dp0HandOver_Protocol.md" "%target%\HandOver_Protocol.md"

pause
