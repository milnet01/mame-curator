# Updating

Settings → **Updates** tells you when a newer MAME Curator exists and
updates it for you. The same tab refreshes the reference INI files.

## Checking for a new version

The app asks GitHub for the latest release when you open the Updates tab,
and once when it starts if **Check for app updates on startup** is on.
It sends nothing about you or your library; turn the option off to stop
the startup check. **Check now** asks again straight away. **What's new**
shows the release notes.

The **Update channel** decides what counts as new. **Stable** follows
published releases. **Dev** follows the newest code on the main branch,
and only a copy set up with git (see below) can use it.

## Updating

What the update button does depends on how you installed the app.

- **A copy you cloned with git and start with `run.sh` or `run.bat`.**
  **Update** saves a snapshot of your settings, overrides, sessions,
  notes and review marks, moves the code to the new version and
  refreshes its libraries. Restart MAME Curator to finish: close it, then
  start it again. If anything fails, it goes back to the version you had.
  **Roll back** returns to the version from before the last update; your
  settings are left as they are, and Settings → Snapshots can restore the
  snapshot if you want them back too.
- **A downloaded file** (the `.AppImage`, `.exe` or `.dmg` from the
  Releases page). **Download update** saves the new release file next to
  the one you are running (on a Mac, into Downloads). Its checksum is
  checked before it is kept. Close this window and open the new file; the
  old one stays as a fallback until you delete it.
- **Anything else**, such as a `pip` install. The tab links to the
  release page instead.

An update refuses to run over files in the app's folder that were changed
by hand, and says so; nothing has changed when it does.

## Refreshing the INI files

The reference INI files (`catver.ini`, `languages.ini`, `bestgames.ini`,
`series.ini` and `mature.ini`) decide which games pass your filters.
**Preview** downloads the latest ones and lists the games they would add
to or remove from your library. Nothing changes until you press
**Apply**. Apply keeps a copy of the files it replaces in
`data/ini-snapshots/`.
