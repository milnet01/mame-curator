import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FsBrowser } from "@/components/settings/FsBrowser";
import { strings } from "@/strings";

interface FolderFieldProps {
  id: string;
  label: string;
  browseLabel: string;
  help?: string;
  /** null = the setting is unset; shown as an empty field. */
  value: string | null;
  /** Called on blur or pick when the folder changed. An emptied field
   *  commits null only when the setting is `optional`. */
  onCommit: (value: string | null) => void;
  optional?: boolean;
}

/** A folder setting: a text field that saves on blur, plus a Browse picker. */
export function FolderField({
  id,
  label,
  browseLabel,
  help,
  value,
  onCommit,
  optional = false,
}: FolderFieldProps) {
  const [draft, setDraft] = useState(value ?? "");
  const [browseOpen, setBrowseOpen] = useState(false);

  const commit = (next: string) => {
    const committed = optional && next.trim() === "" ? null : next;
    if (committed !== value) onCommit(committed);
  };

  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex items-center gap-2">
        <Input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => commit(draft)}
        />
        <Button
          variant="outline"
          onClick={() => setBrowseOpen(true)}
          aria-label={browseLabel}
        >
          {strings.settings.fsBrowserBrowse}
        </Button>
      </div>
      {help && <p className="text-xs text-muted-foreground">{help}</p>}
      {browseOpen && (
        <FsBrowser
          open
          onOpenChange={setBrowseOpen}
          onPick={(picked) => {
            setDraft(picked);
            commit(picked);
          }}
          initialPath={value || undefined}
        />
      )}
    </div>
  );
}
