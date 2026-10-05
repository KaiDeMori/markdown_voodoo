@echo off

set "source=%~dp0"
set "target=%USERPROFILE%\.claude\skills\unicode-glyph-render"

echo Deploying to %target%
mkdir "%target%\fonts\BYOF" 2>nul
call :copy_file SKILL.md
call :copy_file render_glyph.py
call :copy_file requirements.txt

call :copy_file fonts\GoNotoCurrent-Regular.ttf
call :copy_file fonts\GoNotoEuropeAmericas.ttf
call :copy_file fonts\GoNotoEastAsia.ttf
call :copy_file fonts\GoNotoCJKCore.ttf
call :copy_file fonts\GoNotoAsiaHistorical.ttf
call :copy_file fonts\GoNotoAncient.ttf
call :copy_file fonts\NotoColorEmoji.ttf
call :copy_file fonts\LastResort-Regular.ttf
call :copy_file fonts\FiraCode-Retina.ttf
if exist "%source%fonts\BYOF\seguiemj.ttf" (
    call :copy_file fonts\BYOF\seguiemj.ttf
) else (
    echo skipped fonts\BYOF\seguiemj.ttf - Segoe UI Emoji is a BYOF font and the file is missing
)

if not exist "%target%\.venv\Scripts\python.exe" (
    echo Creating the venv in %target%\.venv
    "%source%.venv\Scripts\python.exe" -m venv "%target%\.venv"
)
echo Installing requirements
"%target%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r "%target%\requirements.txt"

pause
exit /b

:copy_file
copy /y "%source%%~1" "%target%\%~1" >nul && (echo copied  %~1) || (echo FAILED  %~1)
exit /b
