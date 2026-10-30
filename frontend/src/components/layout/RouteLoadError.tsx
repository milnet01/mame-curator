import { Button } from "@/components/ui/button";
import { strings } from "@/strings";

interface RouteLoadErrorProps {
  message: string;
  onRetry: () => void;
  retrying: boolean;
}

/**
 * What a page says when its data could not load: the failure, and a way
 * forward. A toast has gone by the time the user looks, so this stays.
 */
export function RouteLoadError({
  message,
  onRetry,
  retrying,
}: RouteLoadErrorProps) {
  return (
    <div className="flex flex-col items-start gap-2 p-4 text-sm">
      <div role="alert" className="text-destructive">
        <p className="font-medium">{message}</p>
        <p>{strings.common.loadFailedHint}</p>
      </div>
      {/* aria-disabled, not disabled, so a retry that fails keeps focus here. */}
      <Button
        variant="outline"
        size="sm"
        onClick={onRetry}
        aria-disabled={retrying || undefined}
      >
        {retrying ? strings.common.retrying : strings.common.retry}
      </Button>
    </div>
  );
}
