@echo off
REM
REM MAME Curator clone-and-run bootstrap (Windows).
REM
REM Provisions Python 3.12+ + uv + project deps, runs the interactive
REM setup wizard if config.yaml is missing, then starts the server — which
REM opens a browser itself, once the port is accepting. Idempotent — running
REM twice does the right thing on the second run.

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

for /f %%v in ('python -c "import sys; print(0 if sys.version_info >= (3, 12) else 1)"') do set PY_OK=%%v
if not "!PY_OK!" == "0" (
    for /f %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PY_VERSION=%%v
    echo error: Python !PY_VERSION! is too old; need 3.12+.
    exit /b 1
)

REM ---- 2. uv detection / install ----------------------------------------

where uv >nul 2>nul
if errorlevel 1 (
    REM No parentheses in this echo: inside an if block, a `)` closes it.
    echo uv not found - installing via the official installer from https://astral.sh/uv ...
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
REM --inexact: install what the app needs, but never uninstall anything
REM else, so a developer's own tools survive a launch.
REM --no-dev: end users do not need the test and lint tools.
REM `call` on every uv line: without it, a uv installed as a .cmd or .bat
REM wrapper would end this script instead of returning to it.
call uv sync --inexact --no-dev --quiet

REM ---- 4. config.yaml - interactive setup if missing --------------------

if not exist config.yaml (
    echo.
    echo First run - let's get a starter config.yaml in place.
    echo You will be asked for paths to your MAME DAT, ROMs, etc.
    echo.
    call uv run --no-dev mame-curator setup
    if not exist config.yaml (
        echo error: setup did not produce config.yaml.
        exit /b 1
    )
)

REM ---- 5. serve --------------------------------------------------------

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
REM the port accepts (cli/spec.md § Browser). This script used to `start ""`
REM the URL immediately, which raced the application lifespan — a ~48 MB DAT
REM parse — and greeted a cold start with "Unable to connect". Keeping it
REM alongside the poller would also open two tabs on every bootstrap.
call uv run --no-dev mame-curator serve
