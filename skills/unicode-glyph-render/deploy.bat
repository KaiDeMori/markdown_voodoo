@echo off

set "target=%USERPROFILE%\.claude\skills\unicode-glyph-render"

mkdir "%target%\fonts\BYOF" 2>nul
copy /y "%~dp0SKILL.md" "%target%\SKILL.md"
copy /y "%~dp0render_glyph.py" "%target%\render_glyph.py"
copy /y "%~dp0requirements.txt" "%target%\requirements.txt"

copy /y "%~dp0fonts\GoNotoCurrent-Regular.ttf" "%target%\fonts\GoNotoCurrent-Regular.ttf"
copy /y "%~dp0fonts\GoNotoEuropeAmericas.ttf" "%target%\fonts\GoNotoEuropeAmericas.ttf"
copy /y "%~dp0fonts\GoNotoAfricaMiddleEast.ttf" "%target%\fonts\GoNotoAfricaMiddleEast.ttf"
copy /y "%~dp0fonts\GoNotoSouthAsia.ttf" "%target%\fonts\GoNotoSouthAsia.ttf"
copy /y "%~dp0fonts\GoNotoEastAsia.ttf" "%target%\fonts\GoNotoEastAsia.ttf"
copy /y "%~dp0fonts\GoNotoCJKCore.ttf" "%target%\fonts\GoNotoCJKCore.ttf"
copy /y "%~dp0fonts\GoNotoAsiaHistorical.ttf" "%target%\fonts\GoNotoAsiaHistorical.ttf"
copy /y "%~dp0fonts\GoNotoAncient.ttf" "%target%\fonts\GoNotoAncient.ttf"
copy /y "%~dp0fonts\NotoColorEmoji.ttf" "%target%\fonts\NotoColorEmoji.ttf"
copy /y "%~dp0fonts\LastResort-Regular.ttf" "%target%\fonts\LastResort-Regular.ttf"
copy /y "%~dp0fonts\FiraCode-Retina.ttf" "%target%\fonts\FiraCode-Retina.ttf"
if exist "%~dp0fonts\BYOF\seguiemj.ttf" (
    copy /y "%~dp0fonts\BYOF\seguiemj.ttf" "%target%\fonts\BYOF\seguiemj.ttf"
) else (
    echo Segoe UI Emoji is a BYOF font: seguiemj.ttf is missing in fonts\BYOF, skipped
)

if not exist "%target%\.venv\Scripts\python.exe" (
    echo Creating the venv in %target%\.venv
    "%~dp0.venv\Scripts\python.exe" -m venv "%target%\.venv"
)
echo Installing requirements
"%target%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r "%target%\requirements.txt"

pause
