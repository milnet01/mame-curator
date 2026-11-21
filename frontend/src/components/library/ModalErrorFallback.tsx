import { strings } from "@/strings";

/** What a Library window shows in place of itself when it crashes: what
 *  failed, the error, and a Retry that draws it again. */
export function ModalErrorFallback({
  message,
  error,
  onRetry,
}: {
  message: string;
  error: Error;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-2 rounded border border-destructive/40 bg-destructive/10 p-4 text-sm"
    >
      <p className="font-semibold">{message}</p>
      <p className="text-xs text-muted-foreground">{error.message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="rounded border bg-background px-3 py-1 text-xs hover:bg-muted"
      >
        {strings.common.retry}
      </button>
    </div>
  );
}
