@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ytx_relay.bat - the relay fetch of the yt-transcript-extractor skill.
rem Fetches a video's listing and caption tracks on this machine and packs them into
rem a bundle for ytx.import_bundle, so Claude's machine never contacts YouTube.
rem Lives next to yt-dlp.exe and needs 7-Zip (7z) on PATH. See docs/Relay_fetch.md.
rem
rem   Round 1:  ytx_relay.bat "URL"
rem   Round 2:  ytx_relay.bat VIDEO_ID TRACK [TRACK ...]    e.g. en.manual fr-orig.auto

set "MAX_TRACKS=8"
set "READING_LANGS=en.*,de.*"
set "YTDLP=%~dp0yt-dlp.exe"
set "RELAY_DIR=%~dp0ytx_relay"

rem Every call carries these. The local yt-dlp.conf keeps applying (JS runtime etc.);
rem these switches override whatever could cause extra YouTube contact or break the
rem bundle. --ignore-errors matters most: without it a failed caption download makes
rem --load-info-json silently re-extract the video - a full extra hit.
set SHARED=--no-playlist --skip-download --ignore-errors --ignore-no-formats-error ^
 --no-download-archive --no-write-comments --no-mark-watched --no-write-thumbnail ^
 --no-write-description --no-write-playlist-metafiles --no-exec --no-embed-subs ^
 --convert-subs none --no-wait-for-video --no-live-from-start

if not exist "%YTDLP%" (
    echo [relay] yt-dlp.exe not found next to this script: "%YTDLP%"
    exit /b 1
)
where 7z >nul 2>nul || (
    echo [relay] 7-Zip is not on PATH - the bundle needs 7z.
    exit /b 1
)
if "%~1"=="" goto usage
if "%~2"=="" goto round1
goto round2


:round1
set "URL=%~1"
set "INCOMING=%RELAY_DIR%\incoming"
if exist "%INCOMING%" rmdir /s /q "%INCOMING%"
mkdir "%INCOMING%" || exit /b 1

echo [relay] round 1: listing !URL!
"%YTDLP%" %SHARED% --no-simulate --sleep-requests 2 --write-info-json --no-write-subs --no-write-auto-subs ^
 -P "home:%INCOMING%" -P "temp:%INCOMING%" -o "%%(id)s.%%(ext)s" -o "infojson:%%(id)s" "%URL%"

set "VID="
for %%F in ("%INCOMING%\*.info.json") do set "VID=%%~nF"
if not defined VID (
    echo [relay] No listing was written - see the yt-dlp message above. Nothing to bundle.
    exit /b 1
)
set "VID=%VID:.info=%"
call :check_vid || exit /b 1
set "WORK=%RELAY_DIR%\%VID%"
set "INFO=%WORK%\%VID%.info.json"
if exist "%WORK%" rmdir /s /q "%WORK%"
move "%INCOMING%" "%WORK%" >nul || exit /b 1

rem Count before fetching anything: yt-dlp prints the languages it would select
rem (--print implies no download), and the cap is checked against that. The output
rem goes through a file because a for /f command line cannot hold these quotes.
set "AUTO_LANGS="
set "MANUAL_LANGS="
set "MANUAL_PATTERNS=%READING_LANGS%"
set /a AUTO_COUNT=0, MANUAL_COUNT=0
set "SELECTION=%WORK%\selection.txt"

"%YTDLP%" %SHARED% --simulate --load-info-json "%INFO%" --write-auto-subs --no-write-subs ^
 --sub-langs ".*-orig" --print "%%(requested_subtitles)#l" > "%SELECTION%" 2>nul
for /f "usebackq delims=" %%L in ("%SELECTION%") do (
    if not "%%L"=="NA" (
        set /a AUTO_COUNT+=1
        if defined AUTO_LANGS (set "AUTO_LANGS=!AUTO_LANGS!,%%L") else (set "AUTO_LANGS=%%L")
        set "ORIG=%%L"
        set "MANUAL_PATTERNS=!MANUAL_PATTERNS!,!ORIG:-orig=!.*"
    )
)

"%YTDLP%" %SHARED% --simulate --load-info-json "%INFO%" --write-subs --no-write-auto-subs ^
 --sub-langs "%MANUAL_PATTERNS%" --print "%%(requested_subtitles)#l" > "%SELECTION%" 2>nul
for /f "usebackq delims=" %%L in ("%SELECTION%") do (
    if not "%%L"=="NA" (
        set /a MANUAL_COUNT+=1
        if defined MANUAL_LANGS (set "MANUAL_LANGS=!MANUAL_LANGS!,%%L") else (set "MANUAL_LANGS=%%L")
    )
)
del "%SELECTION%" 2>nul

set /a TOTAL=AUTO_COUNT+MANUAL_COUNT
echo [relay] selected %TOTAL% tracks - ASR: [%AUTO_LANGS%]  manual: [%MANUAL_LANGS%]
if %TOTAL% GTR %MAX_TRACKS% (
    echo [relay] More than %MAX_TRACKS% tracks - bundling the listing only.
    echo [relay] Claude will name the tracks for round 2.
    goto bundle
)
if defined AUTO_LANGS call :fetch auto "%AUTO_LANGS%"
if defined MANUAL_LANGS call :fetch manual "%MANUAL_LANGS%"
goto bundle


:round2
set "VID=%~1"
call :check_vid || exit /b 1
set "WORK=%RELAY_DIR%\%VID%"
set "INFO=%WORK%\%VID%.info.json"
if not exist "%INFO%" (
    echo [relay] No listing for %VID% at "%INFO%" - run round 1 first.
    exit /b 1
)
set "AUTO_LANGS="
set "MANUAL_LANGS="
set /a TOTAL=0
shift

:next_track
if "%~1"=="" goto round2_fetch
set /a TOTAL+=1
if %TOTAL% GTR %MAX_TRACKS% (
    echo [relay] More than %MAX_TRACKS% tracks requested - at most %MAX_TRACKS% per round.
    exit /b 1
)
set "TRACK_LANG=%~n1"
set "TRACK_KIND=%~x1"
if /i "%TRACK_KIND%"==".auto" (
    if defined AUTO_LANGS (set "AUTO_LANGS=!AUTO_LANGS!,%TRACK_LANG%") else (set "AUTO_LANGS=%TRACK_LANG%")
) else if /i "%TRACK_KIND%"==".manual" (
    if defined MANUAL_LANGS (set "MANUAL_LANGS=!MANUAL_LANGS!,%TRACK_LANG%") else (set "MANUAL_LANGS=%TRACK_LANG%")
) else (
    echo [relay] Invalid track id "%~1" - expected LANG.manual or LANG.auto, e.g. en.manual
    exit /b 1
)
shift
goto next_track

:round2_fetch
echo [relay] round 2 for %VID% - ASR: [%AUTO_LANGS%]  manual: [%MANUAL_LANGS%]
if defined AUTO_LANGS call :fetch auto "%AUTO_LANGS%"
if defined MANUAL_LANGS call :fetch manual "%MANUAL_LANGS%"
goto bundle


:fetch
rem %1 = auto or manual, %2 = the exact languages, comma-separated.
set "KIND=%~1"
set "LANGS=%~2"
if "%KIND%"=="manual" (set "SUB_FLAGS=--write-subs --no-write-auto-subs") else (set "SUB_FLAGS=--write-auto-subs --no-write-subs")
echo [relay] fetching %KIND% captions: %LANGS%
"%YTDLP%" %SHARED% --no-simulate --no-write-info-json --load-info-json "%INFO%" %SUB_FLAGS% ^
 --sub-langs "%LANGS%" --sub-format "json3/best" --sleep-subtitles 2 ^
 -P "home:%WORK%" -P "temp:%WORK%" -o "%KIND%/%%(id)s.%%(ext)s" -o "subtitle:%KIND%/%%(id)s.%%(ext)s"
exit /b 0


:check_vid
rem VID becomes part of every path, including the ones rmdir /s removes. Only plain
rem video ids pass - letters, digits, _ and -. Every allowed character is stripped
rem (case-insensitively); anything left over, such as . \ or :, refuses the id.
rem The # sentinel keeps REST defined, so the replacements never meet an empty variable.
if not defined VID (
    echo [relay] No video id - refusing to continue.
    exit /b 1
)
set "REST=#!VID!"
for %%C in (a b c d e f g h i j k l m n o p q r s t u v w x y z 0 1 2 3 4 5 6 7 8 9 _ -) do set "REST=!REST:%%C=!"
if not "!REST!"=="#" (
    echo [relay] Refusing video id "!VID!" - only letters, digits, _ and - are allowed.
    exit /b 1
)
exit /b 0


:bundle
set "BUNDLE=%RELAY_DIR%\%VID%.ytx.zip"
mkdir "%WORK%\auto" 2>nul
mkdir "%WORK%\manual" 2>nul
if exist "%BUNDLE%" del /q "%BUNDLE%"
pushd "%WORK%"
7z a -tzip "%BUNDLE%" "%VID%.info.json" auto manual >nul
popd
if not exist "%BUNDLE%" (
    echo [relay] 7-Zip did not create the bundle.
    exit /b 1
)
echo.
echo [relay] Bundle: %BUNDLE%
echo [relay] Caption files inside:
dir /b "%WORK%\auto" "%WORK%\manual" 2>nul
echo [relay] Hand the bundle over to Claude.
explorer /select,"%BUNDLE%"
exit /b 0


:usage
echo Usage:
echo   %~nx0 "URL"                        round 1: listing + source tracks, up to %MAX_TRACKS%
echo   %~nx0 VIDEO_ID TRACK [TRACK ...]    round 2: named tracks, e.g. en.manual fr-orig.auto
exit /b 2
