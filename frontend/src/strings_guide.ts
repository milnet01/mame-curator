/**
 * mame-curator-1144 — guide text. `strings_internal.ts` is past its size cap,
 * so this has its own module, re-exported as `strings.guide` by `strings.ts`.
 */
import { settingsGuideStrings } from "./strings_guide_settings";

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
    games: {
      heading: "Where are your MAME games?",
      help: "Choose the folder that holds your game files. They are usually .zip files.",
      chosenHeading: "Use this folder for your games?",
      choose: "Choose a folder",
      chooseAnother: "Choose another folder",
      yes: "Yes, use this folder",
    },
    list: {
      heading: "Where is your game list?",
      help: "This is the file that lists every MAME game. It ends in .xml or .zip, and is often called a DAT file.",
      chosenHeading: "Use this game list?",
      choose: "Choose a file",
      chooseAnother: "Choose another file",
      yes: "Yes, use this file",
    },
    dest: {
      heading: "Where should copied games go?",
      help: "Choose the folder your chosen games will be copied to. Your original games are not changed.",
      chosenHeading: "Copy games to this folder?",
      choose: "Choose a folder",
      chooseAnother: "Choose another folder",
      yes: "Yes, finish setup",
    },
    reading: "Reading your game list. This can take a minute.",
    checking: "Checking that this is a game list…",
    notAGameList:
      "That file could not be read as a game list. Please choose another.",
    sameFolder:
      "Please choose a different folder from the one holding your games.",
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
  /** mame-curator-1216: leave out boards that hold several games. */
  compilations: {
    heading: "Hide compilations?",
    help: "Some boards hold several games at once. Hiding them leaves those boards out of your games.",
    yes: "Yes, hide them",
    no: "No, keep them",
  },
  /** mame-curator-1217: keep only games whose text is in a chosen language. */
  languages: {
    heading: "Which languages can you read?",
    help: "Choose one or more, then Done. Games with text only in other languages are left out. Games with no language listed are kept.",
    chosen: "Chosen",
    done: "Done",
    keepAll: "Keep every language",
    none: "No languages are listed, so every language is kept.",
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
    listChanged:
      "The list of games changed while it was being read. Please try again.",
  },
  where: {
    heading: "Copy them here?",
    yes: "Yes, copy here",
    choose: "Choose another folder",
  },
  check: {
    heading: "Ready to copy?",
    loadingHeading: "Checking your folders…",
    nothingNewHeading: "There is nothing new to copy.",
    cannotStartHeading: "This copy can't start yet.",
    newGames: (n: number) => `${games(n)} will be copied.`,
    alreadyCopied: (n: number) =>
      `${count(n)} ${n === 1 ? "is" : "are"} already there and will be left alone.`,
    notInPlaylist: (n: number) =>
      `${games(n)} ${n === 1 ? "is" : "are"} on your drive but not in your game list. Starting the copy adds ${n === 1 ? "it" : "them"}.`,
    missingSource: (n: number) =>
      `${count(n)} could not be found in your ROM folder and will be skipped.`,
    bios: (n: number) =>
      `${count(n)} BIOS file${n === 1 ? "" : "s"} these games need will be included.`,
    biosMissing: (n: number) =>
      `${count(n)} BIOS file${n === 1 ? " these games need is" : "s these games need are"} not in your ROM folder, so some games may not run.`,
    existingPlaylist: "These will be added to your existing game list.",
    notWritable: "This folder cannot be written to.",
    needsSpace: (size: string) => `This needs ${size} more free space.`,
    allCopied: "All of these are already copied.",
    start: "Start copying",
    starting: "Starting the copy…",
  },
  copying: {
    heading: "Copying your games",
    closeHint: "You can close this page. The copy will carry on.",
    pausedHint:
      "The copy is paused. If you leave, open the guide or the Library to come back to it.",
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
  /** mame-curator-1146: choosing a game's version, one question at a time. */
  fix: {
    entry: "Fix this game's picture or version, step by step",
    heading: "Which version would you like?",
    inUse: "In use now",
    savingHeading: "Saving your choice…",
    unchanged: (name: string) => `You are already using ${name}.`,
    failedHeading: "Your choice was not saved.",
    nothingChanged: "Nothing has changed.",
    tryAgain: "Try again",
    toLibrary: "Back to the Library",
    /** mame-curator-1146, picture half: choosing the picture a game shows. */
    picture: {
      whatHeading: "What would you like to fix?",
      whatVersion: "A different version",
      whatPicture: "A different picture",
      heading: "Which picture would you like?",
      looking: "Looking for pictures…",
      thisVersionOnly: "Your choice is for this version only.",
      lookFurther: "Look in more places",
      notAnswered: "Some places did not answer. Try again in a minute.",
      chosenMissing: "The picture you chose cannot be found now.",
      useUsual: "Use the usual picture",
      none: "We found no pictures for this game.",
      alreadyUsing: "You are already using this picture.",
      savedHeading: "Your game now shows this picture.",
      clearedHeading: "Your game shows its usual picture again.",
      kinds: {
        boxart: "Box or flyer",
        title: "Title screen",
        snap: "In-game screen",
      } as Record<string, string>,
      places: {
        esde: "from your ES-DE pictures",
        retroarchThumbnails: "from your RetroArch pictures",
        progettoSnaps: "from your Progetto-SNAPS pack",
        libretro: "from libretro-thumbnails, online",
        arcadeDB: "from ArcadeDB, online",
        wikipediaImage: "from Wikipedia, online",
        mobyGames: "from MobyGames, online",
      } as Record<string, string>,
      /** A source not in `places` shows its own name. */
      label: (kind: string, place: string) => `${kind}, ${place}`,
      unknownPlace: (source: string) => `from ${source}`,
    },
  },
  /** mame-curator-1147: changing a setting, one topic at a time. */
  settings: settingsGuideStrings,
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
