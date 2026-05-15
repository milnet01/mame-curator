/**
 * User-facing string catalogue.
 *
 * Single source of truth for every visible label, message, banner, error
 * description, and action button copy. Section-keyed so a future i18n
 * migration is `import strings from './strings.<lang>'` and a single
 * locale switch — P06 ships English only (per spec § "Out of scope").
 *
 * `errorByCode` maps the `ApiError.code` values rendered by
 * `mame_curator.api.errors` to friendly UX strings. Unknown codes fall
 * back to `detail` (the server's prose) per spec § "Error envelope
 * handling".
 */

// FP24-GG: hoisted from FeaturedTilesRow.tsx so the strings catalogue
// can name the type and the row component can import it back as the
// single source of truth (no inline-cast duplication).
export interface FeaturedTileQuery {
  publisher?: string
  developer?: string
  genre?: string
  yearFrom?: number
  yearTo?: number
}

export interface FeaturedTile {
  id: string
  title: string
  description: string
  query: FeaturedTileQuery
}

export const strings = {
  app: {
    name: 'MAME Curator',
    tagline: 'Curate, copy, and verify your MAME library.',
  },

  /** Layout option labels (LayoutSwitcher dropdown). */
  layouts: {
    masonry: 'Masonry',
    list: 'List',
    covers: 'Covers',
    grouped: 'Grouped',
  },

  /** Theme palette labels (ThemeSwitcher dropdown). Keys mirror `ThemeName`. */
  themes: {
    dark: 'Dark',
    light: 'Light',
    double_dragon: 'Double Dragon',
    pacman: 'Pac-Man',
    sf2: 'SF2',
    neogeo: 'Neo Geo',
  },

  common: {
    cancel: 'Cancel',
    save: 'Save',
    retry: 'Try again',
    // FP25-H: in-flight label for the Retry button while LibraryErrorPanel's
    // refetch is running — gates double-clicks and gives a visible signal.
    retrying: 'Retrying…',
  },

  // DS02 B1 — route-level Suspense / data-fetch loading labels. Until
  // DS02 these strings were hardcoded JSX text inside App.tsx; the
  // catalogue is the only acceptable source per design § "Strings".
  loading: {
    sessions: 'Loading sessions…',
    activity: 'Loading activity…',
    stats: 'Loading stats…',
    help: 'Loading help…',
    settings: 'Loading settings…',
    generic: 'Loading…',
  },

  // DS02 Cluster C — a11y labels for landmarks + skip-link. Kept in
  // a dedicated namespace so the audit can grep `strings.a11y.` and
  // know it's screen-reader-only copy; visual labels live in `nav` /
  // `library` / `help` per their domain.
  a11y: {
    skipToMain: 'Skip to main content',
    mainLandmark: 'Main content',
    helpTopicsLandmark: 'Help topics',
    helpContentLandmark: 'Help content',
    filtersLandmark: 'Filters',
    cartLandmark: 'Cart',
  },

  nav: {
    library: 'Library',
    sessions: 'Sessions',
    activity: 'Activity',
    stats: 'Stats',
    settings: 'Settings',
    help: 'Help',
    commandPalette: 'Search games, settings, and actions',
    cart: (n: number) => `Cart (${n})`,
    more: 'More',
  },

  library: {
    /** FP21-T — accessible name for the LibraryGrid composite. */
    gridLabel: 'Game library grid',
    emptyTitle: 'No games match your filters',
    emptyHint:
      'Adjust the filters in the sidebar or clear them to see your full library.',
    /** FP20-I — inline error panel when the games query fails. */
    loadFailedTitle: 'Could not load the game library',
    loadFailedHint:
      'The backend may be down or unreachable. Check the server, then retry.',
    placeholderFlyer: 'No artwork available',
    countSummary: (n: number, gb: string, biosDeps: number) =>
      `${n.toLocaleString()} games · ${gb} · ${biosDeps} BIOS dep${biosDeps === 1 ? '' : 's'}`,
    actions: {
      dryRun: 'Dry-run',
      copy: 'Copy',
    },
    badges: {
      contested: 'Has alternative versions',
      overridden: 'Manually overridden',
      chd_missing: 'CHD file missing',
      bios_missing: 'BIOS dependency missing',
      has_notes: 'Has user notes',
    },
    featured: {
      heading: 'Featured',
      tiles: [
        {
          id: 'capcom-classics',
          title: 'Capcom Classics',
          description: 'Capcom CPS-1 / CPS-2 era arcade hits',
          query: { publisher: 'Capcom', yearTo: 2000 },
        },
        {
          id: 'beat-em-ups',
          title: "Beat 'em Ups",
          description: 'Side-scrolling brawlers',
          query: { genre: "Beat'em up" },
        },
        {
          id: 'run-and-gun',
          title: 'Run & Gun Shooters',
          description: 'Run-and-gun shooters',
          query: { genre: 'Shooter / Run-and-Gun' },
        },
        {
          id: 'best-of-1992',
          title: 'Best of 1992',
          description: 'Arcade titles released in 1992',
          query: { yearFrom: 1992, yearTo: 1992 },
        },
        {
          id: 'shmups-vertical',
          title: 'SHMUPS — Vertical',
          description: 'Vertical-scroll shoot-em-up classics',
          query: { genre: 'Shooter / Vertical' },
        },
      ] as readonly FeaturedTile[],
      countLabel: (n: number) =>
        `${n.toLocaleString()} game${n === 1 ? '' : 's'}`,
    },
    cart: {
      summaryEmpty: 'Cart empty',
      summary: (n: number) =>
        `${n.toLocaleString()} game${n === 1 ? '' : 's'}`,
      addToCart: (gameName: string) => `Add ${gameName} to cart`,
      removeFromCart: (gameName: string) => `Remove ${gameName} from cart`,
      added: '✓ Added',
      add: '+Add',
      bulkAdd: (n: number) => `Add all ${n.toLocaleString()}`,
      expand: 'Expand cart',
      collapse: 'Collapse cart',
      clearAll: 'Clear all',
      // FP24-O: AlertDialog labels for the destructive Clear-all flow.
      clearAllConfirm: {
        title: 'Clear cart?',
        description: (n: number) =>
          `This removes ${n.toLocaleString()} game${n === 1 ? '' : 's'} from your cart. This cannot be undone.`,
        action: (n: number) =>
          `Remove ${n.toLocaleString()} game${n === 1 ? '' : 's'} from cart`,
      },
      validateDroppedToast: (n: number) =>
        `${n} cart item${n === 1 ? '' : 's'} removed — they're no longer in your library.`,
      variantBadge: (variantName: string) => `⇄ ${variantName}`,
      storageUnavailableToast:
        'Browser storage unavailable; cart will not persist for this session.',
      maxCartReachedToast: (max: number) =>
        `Cart full (max ${max.toLocaleString()}); some items were not added.`,
    },
    onboarding: {
      body: "Tap a game to add it to your list. Click COPY when you're done.",
      dismissAriaLabel: 'Dismiss onboarding banner',
    },
    filters: {
      searchLabel: 'Search',
      searchPlaceholder: 'Search games…',
      yearRangeLabel: 'Year range',
      onlyContested: 'Only contested picks',
      onlyOverridden: 'Only manual overrides',
      onlyChdMissing: 'Only CHD missing',
      onlyBiosMissing: 'Only BIOS missing',
      saveAsSession: 'Save as session',
      sessionNameLabel: 'Session name',
      /** FP15 § C — one-line explainer above the Save button.
       *  FP16: clarified that this is filter-bookmark, not per-game
       *  progress tracking, after a user reported the mental-model
       *  mismatch ("I meant I went through games A to C"). */
      sessionsExplainer:
        'Sessions are named filter bookmarks (year range + preferred genres / publishers / developers). They do not track per-game review progress.',
      /** FP17 § C — letter / genre / publisher / developer filters. */
      letterLabel: 'Starting letter',
      letterAriaLabel: (l: string) =>
        l === '#' ? 'Filter to games starting with a digit' : `Filter to games starting with ${l.toUpperCase()}`,
      genreLabel: 'Genre',
      publisherLabel: 'Publisher',
      developerLabel: 'Developer',
      anyOption: '(any)',
    },
    /** FP15 § A toast on successful session save. */
    sessionSaved: (name: string) => `Saved session "${name}".`,
    /** FP16 § B toast on successful manual override. */
    overrideApplied: 'Override applied.',
    /** FP15 § B header pill copy (active + idle states). */
    activeSessionPill: (name: string) => `Session: ${name}`,
    activeSessionTitle: (name: string) =>
      `Active session "${name}". Click to manage sessions.`,
    noActiveSessionPill: 'No active session',
    noActiveSessionTitle: 'No active session — save the current filters as one to focus your library.',
    /** FP23 — Library-page banner shown when paths.listxml is unset
     *  (per ADR-0002, the picker can't collapse parent/clone groups
     *  without it, so every machine surfaces as its own card). */
    listxmlMissing: {
      title: 'MAME listxml not configured',
      body:
        'Without a MAME listxml file, region and version variants of the same game appear as separate cards. Configure the listxml path in Settings to collapse them into one card per game.',
      cta: 'Open Settings',
      emptyParseBody:
        'Listxml loaded but contains no cloneof entries — region/version variants will appear separately.',
    },
    // FP24-FF: dryRunConfirmDeferred deleted — the FP23-era toast for
    // the deferred Copy wiring is no longer needed; P15's cart redesign
    // shipped the real DryRun → Copy flow via useCopySession.
  },

  alternatives: {
    drawerTitle: 'Alternative versions',
    /** Subtitle when the family contains only the winner. */
    onlyVersionText: 'This is the only version in the library.',
    /** Subtitle when the family contains multiple versions. */
    familySummary: (n: number) =>
      `${n.toLocaleString()} version${n === 1 ? '' : 's'} in this family`,
    pickedLabel: 'Currently selected',
    overrideButton: 'Use this version',
    /** AT-only labels for the per-row Use button. */
    selectedAriaLabel: (description: string) => `${description} — currently selected`,
    useAriaLabel: (description: string) => `Use ${description}`,
    whyPickedTitle: 'Why was this picked?',
    whyPickedSubtitle:
      'Each line shows a tiebreaker rule and the trait that decided.',
    whyPickedEmpty:
      'No tiebreaker chain — only one candidate survived filtering.',
    candidatesConsidered: (names: string[]) =>
      `Candidates considered: ${names.join(', ')}`,
    notesLabel: 'Notes',
    notesPlaceholder: 'Notes (saved automatically when you click away)…',
    flyerAlt: (description: string) => `Box art for ${description}`,
    /** FP19 — Launch button + status copy. */
    launch: 'Launch in RetroArch',
    launching: 'Launching…',
    launchSuccess: (name: string) => `Launched ${name}.`,
    /** FP22-B — inline hint under the disabled Launch button. Split into
     *  prefix / link-label / suffix so the link in the middle is a real
     *  <Link> component and screen readers announce a normal sentence. */
    launchConfigurePrefix: 'Configure RetroArch in',
    launchConfigureLinkLabel: 'Settings → Paths',
    launchConfigureSuffix: ' to enable launching.',
  },

  sessions: {
    pageTitle: 'Sessions',
    emptyTitle: 'No saved sessions yet',
    emptyHint:
      'Save the current filter set as a named session to switch between focuses.',
    activeBadge: 'Active',
    actions: {
      newSession: 'New session',
      activate: 'Activate',
      deactivate: 'Deactivate',
      rename: 'Rename',
      delete: 'Delete',
      activateAriaLabel: (name: string) => `Activate ${name}`,
      deleteAriaLabel: (name: string) => `Delete ${name}`,
    },
    metaLabels: {
      genres: 'Genres',
      publishers: 'Publishers',
      developers: 'Developers',
      years: 'Years',
    },
    metaJoiner: ' · ',
    confirmDelete: {
      title: 'Delete saved session',
      description: (name: string) =>
        `Permanently remove the saved session "${name}". This cannot be undone.`,
    },
    newSessionHint:
      'To create a session, configure filters in the library and click "Save as session".',
    loadError: 'Could not load sessions.',
  },

  activity: {
    pageTitle: 'Activity',
    emptyTitle: 'No activity yet',
    emptyHint: 'Run a copy to see events here.',
    loadError: 'Could not load activity.',
    pagination: {
      next: 'Next',
      prev: 'Previous',
      page: (p: number, total: number) => `Page ${p} of ${total}`,
    },
  },

  stats: {
    pageTitle: 'Stats',
    sections: {
      genre: 'By genre',
      decade: 'By decade',
      publisher: 'Top publishers',
      driverStatus: 'Driver status',
    },
    totalSize: (gb: string) => `Total library size: ${gb}`,
    loadError: 'Could not load stats.',
  },

  settings: {
    pageTitle: 'Settings',
    sections: {
      paths: 'Paths',
      filters: 'Filters',
      picker: 'Picker',
      ui: 'Interface',
      updates: 'Updates',
      media: 'Media',
      snapshots: 'Snapshots',
      backup: 'Backup & restore',
      about: 'About',
    },
    filterLabels: {
      drop_bios_devices_mechanical: 'Drop BIOS / device / mechanical',
      drop_japanese_only_text: 'Drop Japanese-only text games',
      drop_preliminary_emulation: 'Drop preliminary emulation',
      drop_chd_required: 'Drop CHD-required games',
      drop_mature: 'Drop mature content',
    },
    /** FP12 § A — chip-list field labels (filters tab). */
    filterChipLists: {
      drop_categories: 'Drop categories',
      drop_genres: 'Drop genres',
      drop_publishers: 'Drop publishers',
      drop_developers: 'Drop developers',
    },
    filterChipPlaceholders: {
      drop_categories: 'Add category…',
      drop_genres: 'Add genre…',
      drop_publishers: 'Add publisher…',
      drop_developers: 'Add developer…',
    },
    pickerLabels: {
      prefer_parent_over_clone: 'Prefer parent over clone',
      prefer_good_driver: 'Prefer good driver',
      region_priority: 'Region priority',
    },
    /** FP12 § B — drag-reorder list (region_priority) helper copy. */
    regionPriorityHelp:
      'Order matters: when multiple region variants exist, the one nearest the top wins.',
    /** FP12 § A — chip-list field labels (picker tab). */
    pickerChipLists: {
      preferred_genres: 'Preferred genres',
      preferred_publishers: 'Preferred publishers',
      preferred_developers: 'Preferred developers',
    },
    pickerChipPlaceholders: {
      preferred_genres: 'Add genre…',
      preferred_publishers: 'Add publisher…',
      preferred_developers: 'Add developer…',
    },
    uiLabels: {
      show_alternatives_indicator: 'Show alternatives indicator',
      default_sort: 'Default sort order',
      cards_per_row_hint: 'Cards per row',
      cart_clear_on_copy: 'Clear cart after copy',
      cart_clear_on_copy_options: {
        always: 'Always',
        on_success: 'On success only',
        never: 'Never',
      },
    },
    /** FP12 § D — `default_sort` dropdown options (UI tab). */
    defaultSortOptions: {
      name: 'By name',
      year: 'By year',
      manufacturer: 'By manufacturer',
      rating: 'By rating',
    },
    /** P07 § C — `cards_per_row_hint` dropdown options (UI tab). */
    cardsPerRowOptions: {
      auto: 'Automatic',
      '4': '4 columns',
      '5': '5 columns',
      '6': '6 columns',
      '8': '8 columns',
    },
    updatesLabels: {
      check_on_startup: 'Check for app updates on startup',
      ini_check_on_startup: 'Check for INI updates on startup',
      channel: 'Update channel',
    },
    /** FP12 § E — `updates.channel` dropdown options. */
    updateChannelOptions: {
      stable: 'Stable',
      dev: 'Dev',
    },
    mediaLabels: {
      fetch_videos: 'Fetch video previews (post-P06)',
    },
    pathRowLabels: {
      sourceRoms: 'Source ROMs',
      destination: 'Destination',
      dat: 'DAT',
      retroarchPlaylist: 'RetroArch playlist',
    },
    /** FP12 § H — DAT swap is destructive (replaces the entire library). */
    datSwapConfirmTitle: 'Swap DAT?',
    datSwapConfirm:
      'Switching the DAT replaces every machine in the library. Existing sessions, overrides, and notes that reference removed games stay on disk but are unreachable until you swap back.',
    datSwapActionLabel: (path: string) => `Swap DAT to ${path}`,
    mediaCacheLabel: 'Media cache directory',
    mediaCacheBrowseLabel: 'Browse for media cache directory',
    backupBlurb:
      'Configuration snapshots can be restored from disk. Restore confirmation surfaces a destructive-action dialog.',
    banners: {
      // R35 & R36 read-only banners; Phase-7 will add wizard / apply paths.
      setupReady: 'Configuration looks ready.',
      setupIncomplete:
        'Some paths or reference files are missing — open the Paths section to fix.',
      updateAvailable: (current: string, latest: string) =>
        `Update available: ${current} → ${latest}. Apply flow ships in Phase 7.`,
      updateCurrent: (version: string) => `You're on the latest version (${version}).`,
      restartRequired:
        'Server settings changed — restart `mame-curator serve` for the new bind address to take effect.',
      /** FP16 § C — per-INI status line under the setup banner. */
      iniStatusLine: (
        present: number,
        required: number,
        missing: readonly string[],
      ) =>
        missing.length === 0
          ? `Reference INIs: ${present} / ${required} present.`
          : `Reference INIs: ${present} / ${required} present. Missing: ${missing.join(', ')}. Run \`uv run mame-curator refresh-inis --dest data/ini\` to download.`,
      /** FP22-C — RetroArch readiness line under the setup banner. */
      retroarchConfigured: 'RetroArch: configured.',
      retroarchNotConfigured:
        'RetroArch: not configured — set paths.retroarch and paths.retroarch_core in the Paths tab to enable launching.',
    },
    snapshotRestoreConfirm: (count: number) =>
      `Restore ${count} configuration file${count === 1 ? '' : 's'} from this snapshot? Current settings will be replaced.`,
    /** FP12 § I — Snapshots tab copy. */
    snapshotsTitle: 'Saved snapshots',
    snapshotsLoading: 'Loading snapshots…',
    snapshotsLoadError: 'Could not load snapshots.',
    /** FP20-J — generic fallback when ``restore.error`` is non-ApiError. */
    snapshotRestoreError: 'Could not restore that snapshot.',
    snapshotsEmpty: 'No snapshots yet — one is written automatically before each PATCH.',
    snapshotItemFiles: (count: number) =>
      `${count} file${count === 1 ? '' : 's'}`,
    snapshotRestoreLabel: 'Restore',
    snapshotRestoreConfirmTitle: 'Restore configuration?',
    snapshotRestoreActionLabel: (count: number) =>
      `Restore ${count} file${count === 1 ? '' : 's'}`,
    /** FP12 § J — Backup tab copy. */
    backupTabBlurb:
      'Export a JSON bundle of every config / session / override file, or replace them all from a previously-exported bundle.',
    backupExportLabel: 'Export bundle',
    backupImportLabel: 'Import bundle',
    backupExportError: 'Could not export configuration.',
    backupImportError: 'Could not import configuration.',
    backupImportInvalidJson: 'That file is not a valid JSON bundle.',
    backupImportInvalidShape:
      'That JSON is not a configuration bundle (expected `config`, `overrides`, `sessions`, `notes` keys).',
    backupImportTooLarge:
      'That file is too large — configuration bundles should be well under 5 MB.',
    backupImportConfirmTitle: 'Replace configuration?',
    backupImportConfirm: (filename: string) =>
      `Replace every configuration file with the contents of ${filename}? Current settings will be overwritten.`,
    backupImportActionLabel: (filename: string) =>
      `Replace settings from ${filename}`,
    backupWizardForwardLink:
      'Re-running the setup wizard ships in Phase 8.',
    /** FP12 § G — `<FsBrowser>` modal copy. */
    fsBrowserTitle: 'Pick a path',
    fsBrowserDescription:
      'Browse directories on this machine. Picking a path outside the existing allowlist surfaces a grant prompt.',
    fsBrowserHome: 'Home',
    fsBrowserUp: 'Up',
    fsBrowserUpAtTop: 'Already at the top of the allowed area.',
    fsBrowserBrowse: 'Browse…',
    fsBrowserUseDirectory: 'Use this directory',
    fsBrowserLoading: 'Loading…',
    fsBrowserListError: 'Could not list this directory.',
    fsBrowserHomeError:
      'Could not detect home directory — pick a drive root or quick-jump to continue.',
    fsBrowserEmpty: 'Empty.',
    fsBrowserDirTag: 'dir',
    /** FP13 § D4 — accessible name for the per-row Browse button. */
    fsBrowseAriaLabel: (target: string) => `Browse for ${target}`,
    fsGrantTitle: 'Grant filesystem access?',
    fsGrantConfirm: (path: string) =>
      `${path} is outside the current allowlist. Grant access so the picker can list its contents?`,
    fsGrantActionLabel: (path: string) => `Grant access to ${path}`,
  },

  copy: {
    dryRunTitle: 'Dry-run preview',
    dryRunHint: 'No files are written. Review the diff and confirm to copy.',
    /** AT-only label on the progress indicator. */
    progressAriaLabel: 'Copy progress',
    /** AT-only label on the conflict-resolution panel. */
    conflictRegionAriaLabel: 'Existing playlist conflict',
    modalTitle: 'Copy in progress',
    pause: 'Pause',
    resume: 'Resume',
    abort: 'Cancel',
    abortConfirm: (recyclable: boolean) =>
      recyclable
        ? 'Cancel the copy? Already-copied files can be moved to the recycle bin or kept.'
        : 'Cancel the copy? Already-copied files will be kept.',
    abortKeepFiles: 'Keep files',
    abortRecycleFiles: 'Move to recycle bin',
    progressLine: (done: number, total: number, currentFile: string) =>
      `${done.toLocaleString()} / ${total.toLocaleString()} — ${currentFile}`,
    conflictTitle: 'Existing playlist detected',
    conflictReadOnlyBanner:
      'Restart the copy with updated append_decisions to change the conflict strategy.',
    sessionState: {
      running: 'Copying',
      paused: 'Paused',
      terminating: 'Stopping',
      finished: 'Finished',
      aborted: 'Cancelled',
    },
    /** Modal-close affordance shown in terminal states. */
    done: 'Done',
  },

  help: {
    pageTitle: 'Help',
    emptyTitle: 'No help topics available',
    emptyHint: 'The bundled help library will land in Phase 7.',
    loadingTopic: 'Loading topic…',
    loadError: 'Could not load help topics.',
  },

  cmdK: {
    placeholder: 'Type a command, game, or setting…',
    sections: {
      // FP27 A5: dropped 'games' + 'settings'. Zero production
      // producers ever populated those sections; only test fixtures
      // did. See docs/specs/FP27.md § A5.
      actions: 'Actions',
      help: 'Help topics',
    },
    emptyHint: 'No matches.',
  },

  destructive: {
    // Concrete labels per design §8 / spec § ConfirmationDialog rule.
    clearMediaCache: (entries: number) => `Clear ${entries} cached image${entries === 1 ? '' : 's'}`,
    deleteSession: (name: string) => `Delete session "${name}"`,
    revokeRoot: (path: string) => `Revoke filesystem access to ${path}`,
  },

  errors: {
    /** Friendly headline for a generic toast when no specific copy applies. */
    genericTitle: 'Something went wrong',
    networkTitle: 'Connection problem',
    networkBody:
      'The backend did not respond. Make sure `mame-curator serve` is running.',
    /** Map of `ApiError.code` → friendly message. Unmapped codes fall back to `detail`.
     *
     * Keys MUST exist as `code = "..."` ClassVar values in
     * `mame_curator.api.errors` (FP11 § B1: prior versions carried
     * dead codes that no backend handler issued — `parent_not_found`,
     * `winner_must_be_in_family`, `path_outside_allowed_roots` were
     * spec-aspirational). The CI gate `tools/check_error_codes_sync.py`
     * (FP11 follow-up) asserts every backend `ApiException.code` has
     * a `byCode` entry and that no `byCode` entry is dead. */
    byCode: {
      game_not_found: 'No game with that short name in the loaded DAT.',
      override_not_found: 'No override registered for that parent.',
      session_name_invalid:
        'Session names must start with a letter and use only letters, numbers, hyphens, and underscores.',
      session_not_found: 'No session by that name.',
      fs_sandboxed:
        'That path is outside the allowed filesystem roots. Add it under Settings → Paths first.',
      fs_already_covered: 'That path is already inside an allowed root.',
      fs_path_invalid: 'The supplied path is not a valid directory.',
      fs_not_found: 'That path does not exist.',
      fs_root_not_found: 'That allowed root is no longer registered.',
      fs_config_root_not_revocable:
        'Roots from `config.yaml` cannot be revoked here — edit the config and restart.',
      job_already_running: 'Another copy job is already running. Wait or cancel it first.',
      job_not_found: 'No active copy job — it may have finished or never started.',
      copy_report_corrupt:
        'The copy report on disk is unreadable. Check disk integrity.',
      playlist_conflict_cancelled:
        'A playlist already exists at the destination — choose APPEND or OVERWRITE to continue.',
      snapshot_not_found: 'No configuration snapshot with that ID.',
      help_topic_not_found: 'That help topic is unavailable.',
      media_kind_invalid: 'That media kind is not supported.',
      media_upstream_error: 'Could not reach the libretro-thumbnails server.',
      media_upstream_not_found: 'The requested media is not in the libretro library.',
      // FP21-J / FP22-D: typed launch_game errors lifted out of bare HTTPException.
      retroarch_not_configured:
        'RetroArch is not configured. Set paths.retroarch and paths.retroarch_core under Settings → Paths, then restart.',
      rom_file_not_found:
        'The ROM file is missing on disk. Run a curated Copy first so the .zip is in your destination folder.',
      validation_error: 'The form has invalid values. Check the highlighted fields.',
      config_invalid: 'The configuration is not valid — see field errors below.',
      response_shape_invalid:
        'The server returned an unexpected shape. Refresh and try again.',
      response_not_json: 'The server response was not JSON.',
      network: 'Could not reach the backend.',
      internal: 'The backend hit an unexpected error.',
    } as Record<string, string>,
  },

  notes: {
    saving: 'Saving…',
    saved: 'Saved',
    saveError: 'Could not save — check the connection.',
  },
}

export type StringsCatalogue = typeof strings
