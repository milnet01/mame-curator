@echo off
REM
REM MAME Curator clone-and-run bootstrap (Windows).
REM
REM Provisions Python 3.12+ + uv + project deps, runs the interactive
REM setup wizard if config.yaml is missing, then starts the server and
REM opens a browser. Idempotent — running twice does the right thing on
REM the second run.

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ---- 1. Python 3.12+ detection ----------------------------------------

where python >nul 2>nul
if errorlevel 1 (
    echo error: python not found on PATH.
    echo.
    echo Install Python 3.12 or newer from https://www.python.org/downloads/
    echo and tick "Add python to PATH" during install.  Then re-run run.bat.
    exit /b 1
)

for /f %%v in ('python -c "import sys; print(0 if sys.version_info ^>= (3, 12) else 1)"') do set PY_OK=%%v
if not "!PY_OK!" == "0" (
    for /f %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VERSION=%%v
    echo error: Python !PY_VERSION! is too old; need 3.12+.
    exit /b 1
)

REM ---- 2. uv detection / install ----------------------------------------

where uv >nul 2>nul
if errorlevel 1 (
    echo uv not found - installing via the official installer (https://astral.sh/uv)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    REM cmd.exe inherits PATH at start, so a fresh terminal is needed to pick up uv.
    where uv >nul 2>nul
    if errorlevel 1 (
        echo.
        echo error: uv install completed but the binary isn't on PATH.
        echo Open a new Command Prompt or PowerShell window and re-run run.bat.
        exit /b 1
    )
)

REM ---- 3. uv sync -------------------------------------------------------

echo Syncing Python deps via uv...
uv sync --quiet

REM ---- 4. config.yaml - interactive setup if missing --------------------

if not exist config.yaml (
    echo.
    echo First run - let's get a starter config.yaml in place.
    echo You will be asked for paths to your MAME DAT, ROMs, etc.
    echo.
    uv run mame-curator setup
    if not exist config.yaml (
        echo error: setup did not produce config.yaml.
        exit /b 1
    )
)

REM ---- 5. serve --------------------------------------------------------

if "%PORT%"=="" set PORT=8080
set URL=http://127.0.0.1:%PORT%/

echo.
echo Starting MAME Curator on %URL%
echo (Ctrl-C to stop. Re-run run.bat anytime - it's idempotent.)
echo.

REM Open the browser. `start ""` returns immediately; the serve call below
REM blocks until Ctrl-C.
start "" "%URL%"

uv run mame-curator serve --port %PORT%
