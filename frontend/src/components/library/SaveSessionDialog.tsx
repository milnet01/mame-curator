import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { strings } from "@/strings";

/** The filter sidebar's "Save as session" button and the dialog that names
 *  the session. A blank name saves nothing. */
export function SaveSessionDialog({
  onSave,
}: {
  onSave: (name: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  const handleSave = () => {
    if (!name.trim()) return;
    onSave(name.trim());
    setName("");
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          {strings.library.filters.saveAsSession}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{strings.library.filters.saveAsSession}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor="session-name">
            {strings.library.filters.sessionNameLabel}
          </Label>
          <Input
            id="session-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            {strings.common.cancel}
          </Button>
          <Button onClick={handleSave}>{strings.common.save}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
