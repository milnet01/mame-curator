import { useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useFsMakeFolder } from "@/hooks/useFs";
import { cn } from "@/lib/utils";
import { strings } from "@/strings";

interface FsNewFolderProps {
  /** The folder the picker shows; null while none is open. */
  parent: string | null;
  /** Called with the new folder's path once it is made. */
  onMade: (path: string) => void;
  large?: boolean;
}

/** mame-curator-1169: a New folder button that opens a name box in place. */
export function FsNewFolder({ parent, onMade, large }: FsNewFolderProps) {
  const make = useFsMakeFolder();
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const buttonRef = useRef<HTMLButtonElement>(null);
  const inputId = useId();
  const trimmed = name.trim();
  const words = large ? "min-h-12 text-xl" : undefined;
  const size = large ? "default" : "sm";

  const close = () => {
    setNaming(false);
    setName("");
    make.reset();
    requestAnimationFrame(() => buttonRef.current?.focus());
  };

  if (!naming) {
    return (
      <div>
        <Button
          ref={buttonRef}
          size={size}
          variant="outline"
          className={words}
          disabled={parent === null}
          onClick={() => setNaming(true)}
        >
          {strings.settings.fsNewFolder}
        </Button>
      </div>
    );
  }

  const errCode =
    make.error && "code" in make.error
      ? (make.error as { code: unknown }).code
      : null;

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (parent === null || trimmed === "" || make.isPending) return;
        make.mutate(
          { parent, name: trimmed },
          {
            onSuccess: (made) => {
              setNaming(false);
              setName("");
              onMade(made.path);
            },
          },
        );
      }}
    >
      <label htmlFor={inputId} className={large ? "text-xl" : "text-sm"}>
        {strings.settings.fsNewFolderName}
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <input
          id={inputId}
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={cn(
            "min-w-0 flex-1 rounded-md border bg-background px-2",
            large ? "min-h-12 text-xl" : "h-8 text-sm",
          )}
        />
        <Button
          type="submit"
          size={size}
          className={words}
          disabled={trimmed === "" || make.isPending}
        >
          {strings.settings.fsNewFolderMake}
        </Button>
        <Button
          type="button"
          size={size}
          variant="ghost"
          className={words}
          onClick={close}
        >
          {strings.common.cancel}
        </Button>
      </div>
      {make.error && (
        <p
          role="alert"
          className={cn(large ? "text-xl" : "text-sm", "text-destructive")}
        >
          {errCode === "fs_folder_exists"
            ? strings.settings.fsNewFolderExists
            : strings.settings.fsNewFolderFailed}
        </p>
      )}
    </form>
  );
}
