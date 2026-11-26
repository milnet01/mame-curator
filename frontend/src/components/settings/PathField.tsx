import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FsBrowser } from "@/components/settings/FsBrowser";
import { folderOf } from "@/lib/folderOf";
import { strings } from "@/strings";

interface PathFieldCommon {
  id: string;
  label: string;
  /** The Browse button's accessible name; defaults to "Browse for <label>". */
  browseLabel?: string;
  help?: string;
  /** What Browse picks. A file row's picker opens at the file's folder. */
  mode?: "directory" | "file";
}

/** An optional setting shows null as an empty field and saves an emptied
 *  field as null; a required one only ever saves a path. */
type PathFieldProps = PathFieldCommon &
  (
    | { optional?: false; value: string; onCommit: (value: string) => void }
    | {
        optional: true;
        value: string | null;
        onCommit: (value: string | null) => void;
      }
  );

/** A path setting: a text field that saves on blur, plus a Browse picker.
 *  Either saves only a change. */
export function PathField(props: PathFieldProps) {
  const { id, label, browseLabel, help, mode = "directory", value } = props;
  // Only while typing, so a path the server refused does not stay looking saved.
  const [draft, setDraft] = useState<string | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);

  const commit = (next: string) => {
    if (props.optional) {
      const committed = next.trim() === "" ? null : next;
      if (committed !== value) props.onCommit(committed);
    } else if (next !== value) {
      props.onCommit(next);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex items-center gap-2">
        <Input
          id={id}
          value={draft ?? value ?? ""}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => {
            if (draft !== null) commit(draft);
            setDraft(null);
          }}
        />
        <Button
          variant="outline"
          onClick={() => setBrowseOpen(true)}
          aria-label={browseLabel ?? strings.settings.fsBrowseAriaLabel(label)}
        >
          {strings.settings.fsBrowserBrowse}
        </Button>
      </div>
      {help && <p className="text-xs text-muted-foreground">{help}</p>}
      {browseOpen && (
        <FsBrowser
          open
          onOpenChange={setBrowseOpen}
          onPick={commit}
          mode={mode}
          // A file row holds a file, which may not exist yet, and a listing
          // or a grant needs a folder.
          initialPath={
            mode === "file" ? folderOf(value ?? "") : value || undefined
          }
        />
      )}
    </div>
  );
}
