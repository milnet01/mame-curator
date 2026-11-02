import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FsBrowser } from "@/components/settings/FsBrowser";
import { folderOf } from "@/lib/folderOf";
import { strings } from "@/strings";

interface PathRowProps {
  id: string;
  label: string;
  value: string;
  mode?: "directory" | "file";
  onChange: (next: string) => void;
}

// FP12 § H — single Label + Input + Browse cell. The Input patches on blur
// (avoids per-keystroke noise); the Browse button opens an <FsBrowser>
// scoped to this row so multiple PathRows don't share a modal. The draft
// lives only while typing, so the field always ends on what is saved: a path
// the server refused does not stay in it looking saved.
export function PathRow({
  id,
  label,
  value,
  mode = "directory",
  onChange,
}: PathRowProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <div className="flex items-center gap-2">
        <Input
          id={id}
          value={draft ?? value}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => {
            if (draft !== null && draft !== value) onChange(draft);
            setDraft(null);
          }}
        />
        <Button
          variant="outline"
          onClick={() => setBrowseOpen(true)}
          aria-label={strings.settings.fsBrowseAriaLabel(label)}
        >
          {strings.settings.fsBrowserBrowse}
        </Button>
      </div>
      {browseOpen && (
        <FsBrowser
          open
          onOpenChange={setBrowseOpen}
          onPick={onChange}
          mode={mode}
          // A file row holds a file, which may not exist yet, and a listing
          // or a grant needs a folder.
          initialPath={mode === "file" ? folderOf(value) : value || undefined}
        />
      )}
    </div>
  );
}
