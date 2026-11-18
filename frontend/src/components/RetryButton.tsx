import { Button } from "@/components/ui/button";
import { strings } from "@/strings";

interface RetryButtonProps {
  onRetry: () => void;
  /** True while the retry is under way: the button says so and ignores presses. */
  retrying: boolean;
}

/**
 * The Retry button every load failure shows. It uses aria-disabled, not
 * disabled, so a retry that fails again keeps a keyboard user's focus here
 * (mame-curator-1165).
 */
export function RetryButton({ onRetry, retrying }: RetryButtonProps) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={retrying ? undefined : onRetry}
      aria-disabled={retrying || undefined}
      className="aria-disabled:cursor-not-allowed aria-disabled:opacity-50"
    >
      {retrying ? strings.common.retrying : strings.common.retry}
    </Button>
  );
}
