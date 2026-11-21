import { useEffect, useRef, useState } from "react";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { CartBar } from "@/components/library/CartBar";
import { CartPanel } from "@/components/library/CartPanel";
import { type UseCartResult } from "@/hooks/useCart";
import { strings } from "@/strings";

interface LibraryCartAreaProps {
  cart: UseCartResult;
  expanded: boolean;
  onExpandedChange: (next: boolean) => void;
  /** The simple view has one column; the full view spans both. */
  simple: boolean;
  bulkAddTotal: number | null;
  onBulkAdd: () => void;
  bulkAdding: boolean;
  onDryRun: () => void;
  onCopy: () => void;
  copyDisabled: boolean;
  onShowCopy?: () => void;
}

/** The foot of the Library: the cart's list, its Clear all confirmation,
 *  and the cart bar. */
export function LibraryCartArea({
  cart,
  expanded,
  onExpandedChange,
  simple,
  bulkAddTotal,
  onBulkAdd,
  bulkAdding,
  onDryRun,
  onCopy,
  copyDisabled,
  onShowCopy,
}: LibraryCartAreaProps) {
  // FP24-O: Clear-all is destructive (cart has no undo) — coding-
  // standards § 4 mandates AlertDialog confirm for destructive ops.
  const [clearAllOpen, setClearAllOpen] = useState(false);

  // Opening the cart can push the bar below the fold, because the games keep
  // their height. This keeps the bar, and the button just pressed, in place.
  const cartRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (expanded) cartRef.current?.scrollIntoView({ block: "end" });
  }, [expanded]);

  return (
    <div ref={cartRef} className={simple ? undefined : "roomy:col-span-2"}>
      <CartPanel
        open={expanded}
        items={cart.items}
        onRemove={cart.remove}
        onClearAll={() => setClearAllOpen(true)}
      />
      <ConfirmationDialog
        open={clearAllOpen}
        onOpenChange={setClearAllOpen}
        title={strings.library.cart.clearAllConfirm.title}
        description={strings.library.cart.clearAllConfirm.description(
          cart.items.length,
        )}
        actionLabel={strings.library.cart.clearAllConfirm.action(
          cart.items.length,
        )}
        onConfirm={() => cart.clear()}
        destructive
      />
      <CartBar
        itemCount={cart.items.length}
        bulkAddTotal={bulkAddTotal}
        expanded={expanded}
        onBulkAdd={onBulkAdd}
        bulkAdding={bulkAdding}
        onToggleExpand={() => onExpandedChange(!expanded)}
        onDryRun={onDryRun}
        onCopy={onCopy}
        copyDisabled={copyDisabled}
        onShowCopy={onShowCopy}
      />
    </div>
  );
}
