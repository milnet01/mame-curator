# Command-line use

Some tasks can also be run from a terminal. Run these from the folder
you installed MAME Curator into.

- `uv run mame-curator setup --force` — answer the setup questions in
  the terminal instead of the browser. This replaces your settings file.
- `uv run mame-curator refresh-inis --dest data/ini` — download the
  community reference files the filters use, and tell the app where they
  are. It says so if it could not. Restart the app afterwards.
- `uv run mame-curator serve` — start the app without the launcher
  script.

## Where your settings are

The app and these commands use the same settings file, `config.yaml`. If
the folder you run from holds one, that one is used. Otherwise it is in
your own settings folder:

- Linux: `~/.config/mame-curator/`
- Windows: `%LOCALAPPDATA%\mame-curator\`
- macOS: `~/Library/Application Support/mame-curator/`

The first start creates it there. `--config` on a command names a
different file; on `setup`, that flag is `--out`.

## Choosing the port

The app listens on port 8080 unless told otherwise. Three settings
can change it; the first one present wins:

1. `--port` on the `serve` command;
2. the `PORT` environment variable;
3. `server.port` in `config.yaml`.

`PORT` must be a number from 1024 to 65535. An invalid value stops the
app with a message saying so.
