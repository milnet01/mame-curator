# Getting started

MAME Curator turns a full MAME ROM set into a short list of the best
playable arcade games. It then copies those games to a separate folder
for RetroArch. Your original ROM folder is never changed.

## Starting the app

Run `./run.sh` on Linux or macOS, or `run.bat` on Windows. The first
run asks four questions:

- where your ROMs are (a non-merged set);
- where your MAME DAT file is (`.xml` or `.zip`);
- where the chosen games should be copied to;
- where to write the RetroArch playlist.

After that the app opens in your browser. Running the same script
again later is safe; it skips the questions once `config.yaml` exists.

## Finding your way around

- **Library** — every game that passed your filters, one card each.
- **Settings** — your folders, your filters and the app's options.
- **Help** — these pages.
- **More** — Sessions, Activity and Stats.

## Keyboard shortcuts

- `Ctrl-K` (`⌘K` on a Mac) — search games, settings and actions.
- `/` — jump to the library search box.
- `Esc` — close a drawer or dialog.

## Your data stays here

The app runs on your own computer. It sends nothing anywhere: no
telemetry, no analytics, no cloud sync.
