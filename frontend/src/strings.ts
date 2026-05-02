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
  },

  alternatives: {
    drawerTitle: 'Alternative versions',
    emptyText: 'No alternatives — this is the only version.',
    pickedLabel: 'Currently selected',
    overrideButton: 'Use this version',
    whyPickedTitle: 'Why was this picked?',
    whyPickedSubtitle:
      'Each line shows a tiebreaker rule and the trait that decided.',
    notesPlaceholder: 'Notes (saved automatically when you click away)…',
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
    },
  },

  activity: {
    pageTitle: 'Activity',
    emptyTitle: 'No activity yet',
    emptyHint: 'Run a copy to see events here.',
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
    banners: {
      // R35 & R36 read-only banners; Phase-7 will add wizard / apply paths.
      setupReady: 'Configuration looks ready.',
      setupIncomplete:
        'Some paths or reference files are missing — open the Paths section to fix.',
      updateAvailable: (current: string, latest: string) =>
        `Update available: ${current} → ${latest}. Apply flow ships in Phase 7.`,
      updateCurrent: (version: string) => `You're on the latest version (${version}).`,
    },
    snapshotRestoreConfirm: (count: number) =>
      `Restore ${count} configuration file${count === 1 ? '' : 's'} from this snapshot? Current settings will be replaced.`,
  },

  copy: {
    dryRunTitle: 'Dry-run preview',
    dryRunHint: 'No files are written. Review the diff and confirm to copy.',
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
  },

  help: {
    pageTitle: 'Help',
    emptyTitle: 'No help topics available',
    emptyHint: 'The bundled help library will land in Phase 7.',
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
    /** Map of `ApiError.code` → friendly message. Unmapped codes fall back to `detail`. */
    byCode: {
      game_not_found: 'No game with that short name in the loaded DAT.',
      parent_not_found: 'The override target is not in the visible set.',
      winner_must_be_in_family:
        'The chosen winner must be a parent or clone of the override target.',
      session_name_invalid:
        'Session names must start with a letter and use only letters, numbers, hyphens, and underscores.',
      session_not_found: 'No session by that name.',
      override_not_found: 'No override registered for that parent.',
      path_outside_allowed_roots:
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
