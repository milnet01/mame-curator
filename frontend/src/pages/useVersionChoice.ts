import { useState } from "react";
import { toast } from "sonner";

import type { Alternatives, OverridePostRequest } from "@/api/types";
import { useForgetChoices, useOverride } from "@/hooks/useAlternatives";
import type { UseCartResult } from "@/hooks/useCart";
import { toastApiError } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

/** The warning is a long sentence, and it needs reading: the default is 4 s. */
const WARNING_MS = 15_000;

/** mame-curator-1146: a caller that says the outcome on screen, not in a
 *  pop-up message, as the version guide does. */
export interface VersionChoiceReport {
  /** `unusable` names the saved choices the warnings are about. */
  onSaved: (warnings: string[], unusable: string[]) => void;
  onFailed: (error: unknown) => void;
}

/**
 * mame-curator-1149: what choosing a version does after the server answers.
 *
 * `useOverride` waits for the game list to reload, so the page already shows
 * the choice when the message appears and `focusCard` can be found.
 */
export function useVersionChoice(
  cart: UseCartResult,
  initialFocus: string | null = null,
) {
  const override = useOverride();
  const forget = useForgetChoices();
  // mame-curator-1189: the warning's way out, so it stops coming back.
  const forgetOld = (unusable: string[]) =>
    forget.mutate(unusable, {
      onSuccess: () =>
        toast.success(strings.library.overrideForgotten(unusable.length)),
      onError: toastApiError,
    });
  // The chosen version's card, which replaces the one that had focus; or the
  // card the version guide sent back (mame-curator-1196).
  const [focusCard, setFocusCard] = useState<string | null>(initialFocus);

  const chooseVersion = (
    req: OverridePostRequest,
    family: Alternatives,
    report?: VersionChoiceReport,
  ) => {
    override.mutate(req, {
      onSuccess: ({ warnings, unusable }) => {
        // A cart entry is saved under whichever version was on show when added.
        const names = new Set(family.items.map((game) => game.short_name));
        for (const { shortName } of cart.items) {
          if (names.has(shortName)) cart.setVariant(shortName, req.winner);
        }
        setFocusCard(req.winner);
        if (report) {
          report.onSaved(warnings, unusable);
          return;
        }
        if (warnings.length > 0) {
          toast.warning(
            strings.library.overrideOldChoicesUnusable(warnings.length),
            {
              duration: WARNING_MS,
              action: {
                label: strings.library.overrideForgetOld(unusable.length),
                onClick: () => forgetOld(unusable),
              },
            },
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
