# PyInstaller spec shared by all three desktop bundles (mame-curator-1095 §4.4).
#
# The layout is chosen here, not on the command line: PyInstaller refuses
# --onefile / --console beside a .spec file. Windows gets a one-file console
# EXE; Linux and macOS get a one-dir build, which the AppImage and the .app
# wrap into a single file themselves.
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - SPECPATH is injected by PyInstaller

# Every bundled data file comes from this literal, source -> destination
# inside the bundle. tests/tools/test_release_scripts.py checks it against
# an allowlist (INV-14), so config.yaml, data/ and the media cache can never
# be swept in by a widened entry.
DATAS = [
    ("frontend/dist", "frontend/dist"),
    ("docs/help", "docs/help"),
    ("config.example.yaml", "."),
    ("packaging", "packaging"),
]

# uvicorn loads its protocol and loop machinery by import string, which
# static analysis cannot follow; the implementations are listed too.
HIDDENIMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "httptools",
    "websockets",
]
if sys.platform != "win32":
    HIDDENIMPORTS.append("uvloop")  # uvicorn[standard] skips it on Windows

a = Analysis(  # noqa: F821 - PyInstaller spec globals
    [str(ROOT / "packaging" / "entry.py")],
    pathex=[str(ROOT / "src")],
    datas=[(str(ROOT / src), dest) for src, dest in DATAS],
    hiddenimports=HIDDENIMPORTS,
    excludes=[],
)
pyz = PYZ(a.pure)  # noqa: F821

if sys.platform == "win32":
    exe = EXE(  # noqa: F821
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="MAME_Curator",
        console=True,
        icon=str(ROOT / "packaging" / "mame-curator.ico"),
    )
else:
    exe = EXE(  # noqa: F821
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="mame-curator",
        console=True,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="mame-curator")  # noqa: F821
    if sys.platform == "darwin":
        app = BUNDLE(  # noqa: F821
            coll,
            name="MAME Curator.app",
            icon=str(ROOT / "packaging" / "mame-curator.icns"),
            bundle_identifier="io.github.milnet01.mame-curator",
        )
