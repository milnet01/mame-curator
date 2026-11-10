# Getting started

MAME Curator turns a full MAME ROM set into a short list of the best
playable arcade games. It then copies those games to a separate folder
for RetroArch. Your original ROM folder is never changed.

## Starting the app

Run `./run.sh` on Linux or macOS, or `run.bat` on Windows. The app
opens in your browser.

## First-time setup

The first time, the app asks three questions, one per screen:

- where your MAME games are (a folder holding a non-merged set);
- where your game list is (a MAME DAT file, ending in `.xml` or `.zip`);
- where the chosen games should be copied to. The folder must already exist.

When you finish, your games load and the guide begins. You do not need to
restart anything. If the app later cannot read your game list, **Start here**
asks these questions again.

Your RetroArch playlist goes in the folder you copy to, as `mame.lpl`. To
put it somewhere else, use **Settings**.

## The guide

The first time the app opens, it shows a guide. It asks one question per
screen, in large text, and takes you from choosing games to a finished
copy. Choose **Look around on my own** to leave it at any time, except
while a copy is paused: resume or stop it first. Choose **Start here** in
the top menu to come back to it. If you leave during a copy, the guide and
the Library both show that copy again when you open them. A copy from the guide
adds to your existing game list. It never changes your cart.

After you choose which games, the guide asks **Hide compilations?**
Compilations are boards that hold several games at once. Your answer is
saved, and you can change it under **Settings → Filters**.

Next it asks **Which languages can you read?** Choose one or more, then
**Done**, or choose **Keep every language**. Games with text only in other
languages are left out. Games with no language listed are kept. You can
change this under **Settings → Filters** too.

## Text size

The **Text size** box at the top of every page makes text larger or
smaller. The app remembers your choice in this browser.

## Finding your way around

- **Start here** — the guide.
- **Library** — every game that passed your filters, one card each.
- **Settings** — your folders, your filters and the app's options.
- **Help** — these pages.
- **More** — Sessions, Activity and Stats.

## Keyboard shortcuts

- `Ctrl-K` (`⌘K` on a Mac) — jump to a page or a help topic.
- `/` — on the Library page, jump to the search box.
- `Esc` — close a drawer or dialog.

On the Library page, press `Tab` until a game has a coloured ring. Then:

- Arrow keys — move between games. `Home` and `End` jump to the first and last.
- `Enter` — open the game, to see its versions.
- `R`, `S` or `?` — mark the game reviewed, skipped or needs decision. The same
  key again clears the mark.

## Your data stays here

The app runs on your own computer. It sends nothing anywhere: no
telemetry, no analytics, no cloud sync.
