import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { useFsAllowedRoots, useFsRevokeRoot } from "@/hooks/useFs";
import { strings } from "@/strings";
import type { FsAllowedRoot } from "@/api/types";

/** mame-curator-1175: the drives and folders granted in the picker, each removable.
    The app's own folders (home and the configured paths) are not listed:
    nothing here can remove them. */
export function AllowedRootsList() {
  const allowed = useFsAllowedRoots();
  const revoke = useFsRevokeRoot();
  const [pending, setPending] = useState<FsAllowedRoot | null>(null);
  const headingId = useId();

  if (!allowed.data) return null;
  const missingIds = new Set(allowed.data.missing.map((r) => r.id));
  const granted = [
    ...allowed.data.roots.filter((r) => r.source === "granted"),
    ...allowed.data.missing,
  ];

  return (
    <section className="flex flex-col gap-2 pt-4">
      <h2 id={headingId} className="text-lg font-semibold">
        {strings.settings.allowedTitle}
      </h2>
      <p className="text-sm text-muted-foreground">
        {strings.settings.allowedHint}
      </p>
      {granted.length === 0 ? (
        <p className="text-sm">{strings.settings.allowedNone}</p>
      ) : (
        <ul aria-labelledby={headingId} className="flex flex-col gap-2">
          {granted.map((root) => (
            <li
              key={root.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-2"
            >
              <span className="min-w-0 [overflow-wrap:anywhere]">
                <code>{root.path}</code>
                {missingIds.has(root.id) && (
                  <span className="ml-2 text-sm text-muted-foreground">
                    ({strings.settings.allowedMissing})
                  </span>
                )}
              </span>
              <Button
                size="sm"
                variant="outline"
                aria-label={strings.settings.allowedRemoveAria(root.path)}
                onClick={() => setPending(root)}
              >
                {strings.settings.allowedRemove}
              </Button>
            </li>
          ))}
        </ul>
      )}
      {pending !== null && (
        <ConfirmationDialog
          open
          // The prompt closes itself on confirm, so one press sends one request.
          onOpenChange={(o) => {
            if (!o) setPending(null);
          }}
          title={strings.settings.allowedRemoveTitle}
          description={strings.settings.allowedRemoveConfirm(pending.path)}
          actionLabel={strings.destructive.revokeRoot(pending.path)}
          destructive
          onConfirm={() => revoke.mutate(pending.id)}
        />
      )}
    </section>
  );
}
