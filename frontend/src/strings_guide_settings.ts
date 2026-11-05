/**
 * mame-curator-1147 — the Settings guide's text, re-exported as
 * `strings.guide.settings` by `strings_guide.ts`.
 */
type CartPolicy = "always" | "on_success" | "never";

export const settingsGuideStrings = {
  entry: "Change a setting, step by step",
  heading: "What would you like to change?",
  topics: {
    folders: "Where your games are, and where they are copied to",
    leaveOut: "Which kinds of games to leave out",
    region: "Which region's versions to favour",
    cart: "Whether your cart empties after a copy",
  },
  toSettings: "Back to Settings",
  changeMore: "Change something else",
  inUse: "In use now",
  savingHeading: "Saving your change…",
  unchangedHeading: "That is already your setting.",
  failedHeading: "Your change was not saved.",
  nothingChanged: "Nothing has changed.",
  tryAgain: "Try again",
  folders: {
    heading: "Which folder would you like to change?",
    games: "Where your games are",
    dest: "Where games are copied to",
    choose: "Choose another folder",
    sameAsDest:
      "Please choose a different folder from the one games are copied to.",
    sameAsGames:
      "Please choose a different folder from the one holding your games.",
    gamesSaved: (path: string) => `Your games are now read from ${path}.`,
    destSaved: (path: string) => `Games will now be copied to ${path}.`,
  },
  leaveOut: {
    heading: "Which kind of game?",
    leftOutNow: "Left out now",
    includedNow: "In your library now",
    yes: "Yes, leave them out",
    no: "No, keep them in",
    question: (kind: string) => `Leave out ${kind}?`,
    leftOut: (kind: string) => `${kind} are now left out of your library.`,
    included: (kind: string) => `${kind} are now in your library.`,
    /** `name` starts a sentence; `inSentence` sits inside one. */
    kinds: {
      drop_mature: {
        name: "Games for adults",
        inSentence: "games for adults",
        help: "Games marked as being for adults only.",
      },
      drop_japanese_only_text: {
        name: "Games with only Japanese text",
        inSentence: "games with only Japanese text",
        help: "Games whose words are all in Japanese.",
      },
      drop_preliminary_emulation: {
        name: "Games that do not work yet",
        inSentence: "games that do not work yet",
        help: "Games MAME marks as not working.",
      },
      drop_chd_required: {
        name: "Games that need a disk file",
        inSentence: "games that need a disk file",
        help: "Games that need a large extra disk file, called a CHD, as well as the game.",
      },
      drop_bios_devices_mechanical: {
        name: "BIOS files, devices and mechanical machines",
        inSentence: "BIOS files, devices and mechanical machines",
        help: "BIOS files and devices are parts other games use. Mechanical machines have real moving parts.",
      },
    },
  },
  region: {
    heading: "Which region's versions do you like best?",
    help: "Many games have a version for each part of the world. When MAME Curator picks a version, it favours this region.",
    firstNow: "Your first choice now",
    none: "There are no regions to choose from.",
    saved: (region: string) => `Versions for ${region} are now favoured.`,
    yoursStay: "Versions you chose yourself stay as they are.",
  },
  cart: {
    heading: "After a copy, should your cart be emptied?",
    options: {
      always: "Yes, always",
      on_success: "Only when every game was copied",
      never: "No, keep the games in it",
    } satisfies Record<CartPolicy, string>,
    saved: {
      always: "Your cart will now be emptied after every copy.",
      on_success: "Your cart will now be emptied when every game was copied.",
      never: "Your cart will now keep its games after a copy.",
    } satisfies Record<CartPolicy, string>,
  },
};
