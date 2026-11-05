import { useState } from "react";
import { toast } from "sonner";

import type { Alternatives, OverridePostRequest } from "@/api/types";
import { useOverride } from "@/hooks/useAlternatives";
import type { UseCartResult } from "@/hooks/useCart";
import { toastApiError } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

/** The warning is a long sentence, and it needs reading: the default is 4 s. */
const WARNING_MS = 15_000;

/** mame-curator-1146: a caller that says the outcome on screen, not in a
 *  pop-up message, as the version guide does. */
export interface VersionChoiceReport {
  onSaved: (warnings: string[]) => void;
  onFailed: (error: unknown) => void;
}

/**
 * mame-curator-1149: what choosing a version does after the server answers.
 *
 * `useOverride` waits for the game list to reload, so the page already shows
 * the choice when the message appears and `focusCard` can be found.
 */
export function useVersionChoice(cart: UseCartResult) {
  const override = useOverride();
  // The chosen version's card, which replaces the one that had focus.
  const [focusCard, setFocusCard] = useState<string | null>(null);

  const chooseVersion = (
    req: OverridePostRequest,
    family: Alternatives,
    report?: VersionChoiceReport,
  ) => {
    override.mutate(req, {
      onSuccess: ({ warnings }) => {
        // A cart entry is saved under whichever version was on show when added.
        const names = new Set(family.items.map((game) => game.short_name));
        for (const { shortName } of cart.items) {
          if (names.has(shortName)) cart.setVariant(shortName, req.winner);
        }
        setFocusCard(req.winner);
        if (report) {
          report.onSaved(warnings);
          return;
        }
        if (warnings.length > 0) {
          toast.warning(
            strings.library.overrideOldChoicesUnusable(warnings.length),
            { duration: WARNING_MS },
          );
          return;
        }
        const chosen = family.items.find((g) => g.short_name === req.winner);
        toast.success(
          strings.library.overrideApplied(chosen?.description ?? req.winner),
        );
      },
      onError: report?.onFailed ?? toastApiError,
    });
  };

  return { chooseVersion, focusCard, clearFocusCard: () => setFocusCard(null) };
}
