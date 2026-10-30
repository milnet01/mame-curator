/**
 * mame-curator-1144 — guide text. `strings_internal.ts` is past its size cap,
 * so this has its own module, re-exported as `strings.guide` by `strings.ts`.
 */
const count = (n: number) => n.toLocaleString();
const games = (n: number) => `${count(n)} game${n === 1 ? "" : "s"}`;

export const guideStrings = {
  exit: "Look around on my own",
  back: "Back",
  stepOf: (step: number, of: number | undefined) =>
    of === undefined ? `Step ${step}` : `Step ${step} of ${of}`,
  loading: "Getting things ready…",
  loadFailed: "That could not be loaded.",
  size: (bytes: number) =>
    bytes >= 1024 ** 3
      ? `${(bytes / 1024 ** 3).toFixed(1)} GB`
      : `${Math.ceil(bytes / 1024 ** 2).toLocaleString()} MB`,
  setup: {
    heading: "MAME Curator can't read your game list yet.",
    openSettings: "Open Settings",
  },
  which: {
    heading: "Which games would you like?",
    everything: "The best version of every game",
    group: "A ready-made group",
    type: "A type of game",
  },
  chooseGroup: {
    heading: "Which group?",
  },
  chooseType: {
    heading: "Which type?",
    none: "No game types are available.",
  },
  finds: {
    heading: (n: number, size: string) =>
      n === 0
        ? "This finds no games."
        : `This finds ${games(n)}, about ${size}.`,
    loadingHeading: "Counting the games…",
    copyThese: "Copy these",
    lookThrough: "Look through them first",
    gettingList: (done: number, total: number) =>
      `Getting the list: ${count(done)} of ${count(total)}.`,
  },
  where: {
    heading: "Copy them here?",
    yes: "Yes, copy here",
    choose: "Choose another folder",
  },
  check: {
    heading: "Ready to copy?",
    loadingHeading: "Checking your folders…",
    newGames: (n: number) => `${games(n)} will be copied.`,
    alreadyCopied: (n: number) =>
      `${count(n)} ${n === 1 ? "is" : "are"} already there and will be left alone.`,
    missingSource: (n: number) =>
      `${count(n)} could not be found in your ROM folder and will be skipped.`,
    bios: (n: number) =>
      `${count(n)} BIOS file${n === 1 ? "" : "s"} these games need will be included.`,
    existingPlaylist: "These will be added to your existing game list.",
    notWritable: "This folder cannot be written to.",
    needsSpace: (size: string) => `This needs ${size} more free space.`,
    allCopied: "All of these are already copied.",
    start: "Start copying",
  },
  copying: {
    heading: "Copying your games",
    closeHint: "You can close this page. The copy will carry on.",
    pausedHint:
      "Resume before you close this page. This guide cannot come back to a paused copy.",
    finishedHeading: "Your games are copied.",
    partialHeading: "The copy has finished.",
    partial: "Some games could not be copied.",
    seeWhich: "See what happened in Activity",
    stoppedHeading: "The copy has stopped.",
    stoppingHeading: "Stopping the copy…",
    failedHeading: "The copy did not finish.",
    lostHeading: "The connection to the copy was lost.",
    stop: "Stop",
    warningsLead:
      "Some games may not run, because MAME Curator could not work out which BIOS files they need:",
    copyMore: "Copy more games",
    goToLibrary: "Go to the Library",
  },
  nav: {
    startHere: "Start here",
    goStartHere: "Go to Start here",
  },
  textSize: {
    label: "Text size",
    options: {
      normal: "Normal",
      large: "Large",
      larger: "Larger",
      largest: "Largest",
    },
  },
  simpleLibrary: {
    moreOptions: "More options",
    fewerOptions: "Fewer options",
    startHere: "Start here",
    filtersOn: "Some filters are on.",
    clearFilters: "Clear filters",
    showingFirst: (shown: number, total: number) =>
      `Showing the first ${count(shown)} of ${count(total)}.`,
  },
};
