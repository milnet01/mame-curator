/**
 * The Library's dry run and copy, the lock that stops two starting, and
 * what a copy's end does to the cart (mame-curator-1234, CR-09-12: out of
 * `useLibraryController.ts`, over its size cap).
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import type { DryRunReport } from "@/api/types";
import { type CartItem, type UseCartResult } from "@/hooks/useCart";
import { type useConfig } from "@/hooks/useConfig";
import { useCopySession } from "@/hooks/useCopySession";
import { useDryRun } from "@/hooks/useDryRun";
import { useValidateCart } from "@/hooks/useValidateCart";
import { toastApiError, toastError } from "@/lib/apiErrorToast";
import { copyOutcome } from "@/lib/copyOutcome";
import { strings } from "@/strings";

export function useLibraryCopy(
  cart: UseCartResult,
  config: ReturnType<typeof useConfig>,
) {
  const [dryRunReport, setDryRunReport] = useState<DryRunReport | null>(null);
  const dryRun = useDryRun();
  const validateCart = useValidateCart();
  const copySession = useCopySession();
  // FP24-N: Copy and Dry run are off while a copy is checked, started or
  // running, so a double-click cannot start two. mame-curator-1234 (CR-09-6):
  // and while a dry run is out, whose window would offer Copy again.
  const copyLocked =
    dryRun.isPending ||
    validateCart.isPending ||
    copySession.isStarting ||
    copySession.state !== null;

  // mame-curator-1148: add to an existing playlist, as the guide does. CANCEL
  // made the server refuse every copy once a playlist existed.
  const conflictStrategy = "APPEND";

  // P15: dry-run reads from cart.items (with chosenVariant substitution).
  const handleDryRun = () => {
    if (cart.items.length === 0) return;
    dryRun.mutate(
      {
        selected_names: cart.items.map((i) => i.chosenVariant ?? i.shortName),
        conflict_strategy: conflictStrategy,
        append_decisions: {},
      },
      { onSuccess: setDryRunReport, onError: toastApiError },
    );
  };

  const handleCopy = () => {
    if (cart.items.length === 0) return;
    // What is checked is what is sent: the server refuses a whole copy over a
    // name it does not hold, so a stale variant is dropped and said here too.
    const nameOf = (i: CartItem) => i.chosenVariant ?? i.shortName;
    validateCart.mutate(
      { short_names: cart.items.map(nameOf) },
      {
        onSuccess: ({ existing, missing, setupRequired }) => {
          // With no game list, every name is "missing" and none of them has
          // gone. Taking them out would empty the saved cart.
          if (setupRequired) {
            toastError(strings.errors.byCode.copy_setup_required);
            return;
          }
          if (missing.length > 0) {
            toast.warning(
              strings.library.cart.validateDroppedToast(missing.length),
            );
            const gone = new Set(missing);
            for (const item of cart.items) {
              if (gone.has(nameOf(item))) cart.remove(item.shortName);
            }
          }
          if (existing.length === 0) return;
          copySession.start(
            {
              selected_names: [...existing],
              conflict_strategy: conflictStrategy,
              append_decisions: {},
            },
            { onError: toastApiError },
          );
        },
        onError: toastApiError,
      },
    );
  };

  // P15 D9: what a copy's end does to the cart, per config.ui.cart_clear_on_copy,
  // and whether the modal still has anything to say. A lost stream's outcome is
  // not known, so it does neither. Waits for the config: until it loads, the
  // user may be one who chose `never`.
  // FP24-T: cart and copySession.reset are stable useCallback refs out of
  // useCart / useCopySession, so omitting them from the dep array is
  // intentional — including them would re-run this effect on every cart
  // mutation (cart.clear changes identity if cart re-renders) and the
  // policy logic only wants to react to outcome and policy changes.
  const copyEnd = copySession.state ? copyOutcome(copySession.state) : null;
  const clearPolicy = config.data?.ui.cart_clear_on_copy;
  useEffect(() => {
    if (
      !clearPolicy ||
      !copyEnd ||
      copyEnd === "active" ||
      copyEnd === "lost"
    ) {
      return;
    }
    // mame-curator-1158: a copy taken up on opening may be the guide's, so
    // its end is no reason to empty the cart.
    if (
      !copySession.state?.reattached &&
      (clearPolicy === "always" ||
        (clearPolicy === "on_success" && copyEnd === "complete"))
    ) {
      cart.clear();
    }
    // mame-curator-1164: BIOS warnings stay on screen until the user closes them.
    const warned = (copySession.state?.warnings.length ?? 0) > 0;
    if (copyEnd === "complete" && clearPolicy !== "never" && !warned) {
      toast.success(strings.guide.copying.finishedHeading);
      copySession.reset();
    } else if (copyEnd === "stopped" && clearPolicy === "always") {
      copySession.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [copyEnd, clearPolicy]);

  return {
    dryRunReport,
    setDryRunReport,
    copyLocked,
    copySession,
    handleDryRun,
    handleCopy,
  };
}
