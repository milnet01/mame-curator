# Command-line use

Some tasks can also be run from a terminal. Run these from the folder
you installed MAME Curator into.

- `uv run mame-curator setup --force` — answer the first-run
  questions again and rewrite `config.yaml`.
- `uv run mame-curator refresh-inis --dest data/ini` — download the
  community reference files the filters use.
- `uv run mame-curator serve` — start the app without the launcher
  script.

## Choosing the port

The app listens on port 8080 unless told otherwise. Three settings
can change it; the first one present wins:

1. `--port` on the `serve` command;
2. the `PORT` environment variable;
3. `server.port` in `config.yaml`.

`PORT` must be a number from 1024 to 65535. An invalid value stops the
app with a message saying so.
