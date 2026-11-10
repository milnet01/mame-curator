/**
 * mame-curator-1199 — the games a copy skipped or failed, for its Activity
 * entry. The names come from the copy's report, and are fetched only when
 * asked for, so the list stays short.
 */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { CopyNamesSchema, type CopyName, type CopyNames } from "@/api/types";
import { useApiQuery } from "@/hooks/useApi";
import { strings } from "@/strings";

/** The skipped and failed counts of a `copy_finished` entry; 0 otherwise. */
function problemCount(entry: Record<string, unknown>): number {
  if (entry.event_type !== "copy_finished") return 0;
  const details = entry.details as
    | { report_summary?: { skipped_count?: unknown; failed_count?: unknown } }
    | undefined;
  const summary = details?.report_summary;
  const count = (value: unknown) => (typeof value === "number" ? value : 0);
  return count(summary?.skipped_count) + count(summary?.failed_count);
}

function line(item: CopyName): string {
  const name =
    item.role === "bios"
      ? strings.activity.copyNames.bios(item.short_name)
      : item.short_name;
  return `${name}: ${item.error ?? strings.activity.copyNames.reason[item.status]}`;
}

function NameList({ heading, items }: { heading: string; items: CopyName[] }) {
  if (items.length === 0) return null;
  return (
    <>
      <p className="text-sm font-medium">{heading}</p>
      <ul className="list-disc pl-5 text-sm">
        {items.map((item) => (
          <li key={`${item.role}-${item.short_name}`}>{line(item)}</li>
        ))}
      </ul>
    </>
  );
}

function Names({ sessionId }: { sessionId: string }) {
  const names = useApiQuery<CopyNames>(
    ["activity", "copy-names", sessionId],
    `/api/activity/copy/${encodeURIComponent(sessionId)}/names`,
    CopyNamesSchema,
    { retry: false },
  );
  if (names.isError)
    return <p className="text-sm">{strings.activity.copyNames.unavailable}</p>;
  if (!names.data) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        {strings.loading.generic}
      </p>
    );
  }
  return (
    <>
      <NameList
        heading={strings.activity.copyNames.skipped}
        items={names.data.skipped}
      />
      <NameList
        heading={strings.activity.copyNames.failed}
        items={names.data.failed}
      />
    </>
  );
}

export function ActivityCopyNames({
  entry,
}: {
  entry: Record<string, unknown>;
}) {
  const [open, setOpen] = useState(false);
  if (problemCount(entry) === 0) return null;
  const sessionId = String(entry.session_id ?? "");
  return (
    <div className="mt-1 flex flex-col gap-1">
      <Button
        variant="outline"
        size="sm"
        className="self-start"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {strings.activity.copyNames.show}
      </Button>
      {open && <Names sessionId={sessionId} />}
    </div>
  );
}
