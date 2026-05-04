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
  },

  nav: {
    library: 'Library',
    sessions: 'Sessions',
    activity: 'Activity',
    stats: 'Stats',
    settings: 'Settings',
    help: 'Help',
    commandPalette: 'Search games, settings, and actions',
  },

  library: {
    emptyTitle: 'No games match your filters',
    emptyHint:
      'Adjust the filters in the sidebar or clear them to see your full library.',
    flyerAlt: (name: string) => `Box art for ${name}`,
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
    },
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
    },
    /** FP12 § D — `default_sort` dropdown options (UI tab). */
    defaultSortOptions: {
      name: 'By name',
      year: 'By year',
      manufacturer: 'By manufacturer',
      rating: 'By rating',
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
    },
    snapshotRestoreConfirm: (count: number) =>
      `Restore ${count} configuration file${count === 1 ? '' : 's'} from this snapshot? Current settings will be replaced.`,
    /** FP12 § I — Snapshots tab copy. */
    snapshotsTitle: 'Saved snapshots',
    snapshotsLoading: 'Loading snapshots…',
    snapshotsLoadError: 'Could not load snapshots.',
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
    fsBrowserBrowse: 'Browse…',
    fsBrowserUseDirectory: 'Use this directory',
    fsBrowserLoading: 'Loading…',
    fsBrowserListError: 'Could not list this directory.',
    fsBrowserEmpty: 'Empty.',
    fsBrowserDirTag: 'dir',
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
    conflictKeepExisting: 'Keep existing',
    conflictReplace: 'Replace',
    conflictReplaceAndRecycle: 'Replace and recycle old',
    sessionState: {
      running: 'Copying',
      paused: 'Paused',
      terminating: 'Stopping',
      finished: 'Finished',
      aborted: 'Cancelled',
    },
    historyEmpty: 'No copy history yet.',
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
      games: 'Games',
      settings: 'Settings',
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
    resetConfig: 'Reset configuration to defaults',
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
