import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { strings } from "@/strings";
import type { Snapshot } from "@/api/types";

interface SnapshotsTabProps {
  snapshots: readonly Snapshot[];
  loading?: boolean;
  error?: string | null;
  /** FP20-J: persistent alert above the snapshot list when the most
   * recent restore mutation failed. The dialog auto-closes on
   * confirm, and the toastApiError flash dismisses — without this
   * the user has no signal the restore actually failed and the
   * config didn't change. Mirrors ``BackupTab.error``.
   *
   * FP25-K(9) / FP26-L: lifetime contract — the alert lives from the
   * `useSnapshotRestore()` mutation's last error settle until the
   * next `mutate()` call. SettingsRoute owns the state via the
   * mutation hook; React Query 5 synchronously clears the mutation's
   * `error` field when `mutate()` is called, so the alert disappears
   * for the duration of a pending retry without any explicit clear.
   * The tab itself does NOT own the state — it would have no way to
   * distinguish "Settings just mounted" from "user opened the tab
   * after a fresh restore failed" once it remounted. */
  restoreError?: string | null;
  /** A restore is under way; stays on the page until it has finished. */
  restoring?: boolean;
  /** The last restore worked. */
  restored?: boolean;
  onRestore: (id: string) => void;
}

const FORMAT = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function SnapshotsTab({
  snapshots,
  loading = false,
  error = null,
  restoreError = null,
  restoring = false,
  restored = false,
  onRestore,
}: SnapshotsTabProps) {
  const [pending, setPending] = useState<Snapshot | null>(null);

  // Words that stay, for a toast has gone by the time the user looks. The list
  // reloads after a restore, and may come back with an error or empty.
  const restoreStatus = (restoring || restored) && (
    <p role="status" className="text-sm">
      {restoring
        ? strings.settings.snapshotRestoring
        : strings.settings.snapshotRestored}
    </p>
  );

  if (loading) {
    return (
      <p className="text-sm text-muted-foreground">
        {strings.settings.snapshotsLoading}
      </p>
    );
  }
  if (error) {
    return (
      <div className="flex flex-col gap-2">
        {restoreStatus}
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      </div>
    );
  }
  if (snapshots.length === 0) {
    return (
      <div className="flex flex-col gap-2">
        {restoreStatus}
        <p className="text-sm text-muted-foreground">
          {strings.settings.snapshotsEmpty}
        </p>
        <p className="text-xs text-muted-foreground">
          {strings.settings.snapshotsStateExclusionNote}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-sm font-medium">{strings.settings.snapshotsTitle}</h2>
      <p className="text-xs text-muted-foreground">
        {strings.settings.snapshotsStateExclusionNote}
      </p>
      {restoreStatus}
      {restoreError && (
        <p role="alert" className="text-sm text-destructive">
          {restoreError}
        </p>
      )}
      <ul className="flex flex-col gap-1">
        {snapshots.map((s) => (
          <li
            key={s.id}
            className="flex items-center justify-between rounded border border-muted px-3 py-2"
          >
            <span className="text-sm">
              <time dateTime={s.ts.toISOString()}>{FORMAT.format(s.ts)}</time>
              {" · "}
              <span className="text-muted-foreground">
                {strings.settings.snapshotItemFiles(s.files.length)}
              </span>
            </span>
            {/* aria-disabled, not disabled, so a closing dialog can hand focus back. */}
            <Button
              size="sm"
              variant="outline"
              aria-disabled={restoring || undefined}
              onClick={() => {
                if (!restoring) setPending(s);
              }}
            >
              {strings.settings.snapshotRestoreLabel}
            </Button>
          </li>
        ))}
      </ul>

      {pending && (
        <ConfirmationDialog
          open
          onOpenChange={(open) => {
            if (!open) setPending(null);
          }}
          title={strings.settings.snapshotRestoreConfirmTitle}
          description={strings.settings.snapshotRestoreConfirm(
            pending.files.length,
          )}
          actionLabel={strings.settings.snapshotRestoreActionLabel(
            pending.files.length,
          )}
          onConfirm={() => onRestore(pending.id)}
          destructive
        />
      )}
    </div>
  );
}
