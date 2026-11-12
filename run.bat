@echo off
REM
REM MAME Curator clone-and-run bootstrap (Windows).
REM
REM Provisions Python 3.12+ + uv + project deps, then starts the server — which
REM opens a browser itself, once the port is accepting, where a first run is set
REM up. Idempotent — running twice does the right thing on the second run.
REM
REM Every failure goes through :fail, which keeps the window open after a
REM double-click. .gitattributes keeps this file CRLF, as Windows expects.

setlocal

REM Delayed expansion starts after this line: it would eat a "!" in the folder
REM name, and uv would then run in whatever folder this script started in.
cd /d "%~dp0" || goto cd_failed

setlocal enabledelayedexpansion

REM ---- 1. Python 3.12+ detection ----------------------------------------

REM The Microsoft Store shortcut named python satisfies `where`, prints only to
REM stderr and exits 9009, so an empty answer here means no Python, not an old
REM one. 2^>nul hides its Store advice, which contradicts the words below.
set "PY_OK="
where python >nul 2>nul
if errorlevel 1 goto python_missing
for /f %%v in ('python -c "import sys; print(0 if sys.version_info >= (3, 12) else 1)" 2^>nul') do set "PY_OK=%%v"
if not defined PY_OK goto python_missing
if "!PY_OK!"=="0" goto python_ok

set "PY_VERSION="
for /f %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VERSION=%%v"
echo error: Python !PY_VERSION! is too old; need 3.12+.
goto python_install_words

:python_ok

REM ---- 2. uv detection / install ----------------------------------------

REM mame-curator-1179: one uv release, and the SHA-256 its GitHub release
REM publishes for each Windows build. uv's Windows installer checks nothing it
REM downloads, so this script fetches uv itself and checks it. run.sh pins the
REM same version; tests/tools/test_launcher_text.py keeps the two in step. To
REM move to a new uv: copy the two .zip.sha256 values from its release.
set "UV_VERSION=0.13.7"
set "UV_SHA256_X64=0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021"
set "UV_SHA256_ARM64=505d9e65e7692bac3ddf98c66754aa26c5050c409c184af30a881a0a72cc85e3"
set "UV_HOME=%USERPROFILE%\.local\bin"

where uv >nul 2>nul
if not errorlevel 1 goto uv_ready
REM mame-curator-1181: installed by an earlier run, but this window's PATH is
REM older than that.
if exist "%UV_HOME%\uv.exe" goto uv_add_to_path

echo uv not found - downloading uv %UV_VERSION% from its GitHub release ...
REM HTTPS and TLS 1.2 or newer. Windows PowerShell has no equivalent of curl's
REM --proto '=https', so a redirect to plain HTTP is not refused, but a swapped
REM download fails the SHA-256 check. The Stop preference makes any failure a
REM non-zero exit. No exclamation mark below: delayed expansion would eat it.
call powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $arm = $env:PROCESSOR_ARCHITECTURE -eq 'ARM64'; $build = if ($arm) {'aarch64'} else {'x86_64'}; $want = if ($arm) {$env:UV_SHA256_ARM64} else {$env:UV_SHA256_X64}; $zip = Join-Path $env:TEMP ('uv-' + [guid]::NewGuid() + '.zip'); try { Invoke-WebRequest -UseBasicParsing -OutFile $zip -Uri ('https://github.com/astral-sh/uv/releases/download/' + $env:UV_VERSION + '/uv-' + $build + '-pc-windows-msvc.zip'); $got = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLower(); if ($got -ne $want) { throw 'the uv download does not match its pinned SHA-256' }; New-Item -ItemType Directory -Force $env:UV_HOME | Out-Null; Expand-Archive -Force $zip $env:UV_HOME } finally { Remove-Item -ErrorAction SilentlyContinue $zip }"
if errorlevel 1 goto uv_install_failed

:uv_add_to_path
REM For this run only; a new window finds uv through the check above.
set "PATH=%UV_HOME%;%PATH%"
where uv >nul 2>nul
if errorlevel 1 goto uv_not_on_path

:uv_ready

REM ---- 3. uv sync -------------------------------------------------------

echo Syncing Python deps via uv...
REM --inexact: install what the app needs, but never uninstall anything
REM else, so a developer's own tools survive a launch.
REM --no-dev: end users do not need the test and lint tools.
REM `call` on every uv line: without it, a uv installed as a .cmd or .bat
REM wrapper would end this script instead of returning to it.
call uv sync --inexact --no-dev --quiet
if errorlevel 1 goto sync_failed

REM ---- 4. serve --------------------------------------------------------

REM No PORT=8080 default and no --port flag: `serve` reads %PORT% itself,
REM validates it (exit 1 with a named error), and falls back to
REM `server.port` in config.yaml when it is unset (cli/spec.md § "`serve`
REM host, port and browser resolution"). A forwarded --port would skip both.
REM `if defined` and !PORT! keep a value holding quotes or parentheses from
REM breaking the parse.

echo.
if defined PORT (
    echo Starting MAME Curator on http://127.0.0.1:!PORT!/
) else (
    echo Starting MAME Curator - the address will be printed once the server binds
)
echo (Ctrl-C to stop. Re-run run.bat anytime - it's idempotent.)
echo.

REM No browser open here: `_cmd_serve` polls the socket and opens it once
REM this server answers (cli/spec.md § Browser). This script used to `start ""`
REM the URL immediately, which raced the application lifespan — a ~48 MB DAT
REM parse — and greeted a cold start with "Unable to connect". Keeping it
REM alongside the poller would also open two tabs on every bootstrap.
call uv run --no-dev mame-curator serve
set "RC=!errorlevel!"
if "!RC!"=="0" exit /b 0
REM `serve` exits 130 when stopped with Ctrl-C. Nothing failed, so no pause.
if "!RC!"=="130" exit /b 130
goto fail

REM ---- What each failure says -------------------------------------------

:cd_failed
echo error: could not open the folder "%~dp0".
echo Copy MAME Curator to a folder on this computer's own drive and run it there.
set "RC=1"
setlocal enabledelayedexpansion
goto fail

:python_missing
echo error: python not found on PATH.

:python_install_words
echo.
echo Install Python 3.12 or newer from https://www.python.org/downloads/
echo and tick "Add python to PATH" during install.  Then re-run run.bat.
set "RC=1"
goto fail

:uv_install_failed
set "RC=!errorlevel!"
echo.
echo error: could not install uv, the tool that sets up MAME Curator.
echo Check your internet connection, then re-run run.bat. If it keeps failing,
echo install uv yourself: https://docs.astral.sh/uv/
goto fail

:uv_not_on_path
echo.
echo error: uv was unpacked to %UV_HOME% but cannot be run from there.
set "RC=1"
goto fail

:sync_failed
set "RC=!errorlevel!"
echo.
echo error: could not install what MAME Curator needs. The lines above say why.
echo Check your internet connection, then re-run run.bat.
goto fail

REM Keep the message on screen after a double-click: the window closes the moment
REM this script ends. Windows gives a double-clicked script the command line
REM cmd.exe /c ""path\run.bat" " ending in space-quote. An open Command Prompt, a
REM PowerShell prompt and another program do not end that way (measured on Windows
REM 10), and they keep the message or must not hang on a pause. The quote is
REM swapped for Q because a literal one cannot be compared inside an if.
:fail
set "CMD_TAIL=!cmdcmdline:~-2!"
set "CMD_TAIL=!CMD_TAIL:"=Q!"
if "!CMD_TAIL!"==" Q" (
    echo.
    echo Press any key to close this window.
    pause >nul
)
exit /b !RC!
