import { useMemo } from "react";
import DOMPurify, { type Config } from "dompurify";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { strings } from "@/strings";

// A scoped instance, as HelpPage keeps its own: hooks added to one never
// reach the other. The server already renders the notes with raw HTML
// disabled (api/markdown.py); this is the second line.
const notesSanitizer = DOMPurify(window);

const NOTES_SANITIZE_CONFIG: Config = {
  ALLOWED_URI_REGEXP: /^(?:https?|mailto):/i,
  // Nothing that fetches: opening the notes must not reach hosts they name.
  // Images, media, SVG and image inputs go, and so do the attributes that
  // load a URL, in case a tag carrying one is ever allowed (mame-curator-1225).
  FORBID_TAGS: [
    "style",
    "form",
    "img",
    "video",
    "audio",
    "source",
    "track",
    "picture",
    "svg",
    "image",
    "input",
  ],
  // Links keep their href: a link fetches nothing until it is followed.
  FORBID_ATTR: ["style", "src", "srcset", "poster", "xlink:href"],
};

interface ReleaseNotesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  version: string;
  /** The release body, rendered by GET /api/updates/check. */
  notesHtml: string;
}

/** mame-curator-1010 §4.5 — the "What's new" modal. */
export function ReleaseNotesDialog({
  open,
  onOpenChange,
  version,
  notesHtml,
}: ReleaseNotesDialogProps) {
  const html = useMemo(
    () => notesSanitizer.sanitize(notesHtml, NOTES_SANITIZE_CONFIG),
    [notesHtml],
  );
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {strings.settings.updates.whatsNewTitle(version)}
          </DialogTitle>
        </DialogHeader>
        <div
          className="prose prose-sm max-w-none dark:prose-invert"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </DialogContent>
    </Dialog>
  );
}
