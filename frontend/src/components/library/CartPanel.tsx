import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'
import type { CartItem } from '@/hooks/useCart'

interface CartPanelProps {
  open: boolean
  items: CartItem[]
  onRemove: (shortName: string) => void
  onClearAll: () => void
}

/**
 * P15 § 4.4 — expand-up cart contents panel.
 *
 * Mounts as a sibling of CartBar. Each row: shortName + optional
 * variant badge + per-row ✕. Bottom row: Clear all link. CSS-
 * only mount/unmount (no framer-motion dep needed at v1; spec
 * § 4.4 explicitly allows the simpler approach).
 */
export function CartPanel({ open, items, onRemove, onClearAll }: CartPanelProps) {
  if (!open) return null
  return (
    <aside
      // FP24-W: id anchors CartBar's aria-controls disclosure pattern.
      // DS02 C4: aria-label moved to the dedicated `a11y.cartLandmark`
      // namespace so the screen-reader copy travels with the other
      // landmark labels.
      id="cart-panel"
      role="region"
      aria-label={strings.a11y.cartLandmark}
      className="max-h-80 overflow-y-auto border-t bg-background px-4 py-3"
    >
      <ul className="flex flex-col gap-1">
        {items.map((item) => (
          <li
            key={item.shortName}
            className="flex items-center gap-2 rounded px-2 py-1 hover:bg-muted/40"
          >
            <span className="font-mono text-sm">{item.shortName}</span>
            {item.chosenVariant && (
              <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                {strings.library.cart.variantBadge(item.chosenVariant)}
              </span>
            )}
            <Button
              size="icon"
              variant="ghost"
              onClick={() => onRemove(item.shortName)}
              aria-label={strings.library.cart.removeFromCart(item.shortName)}
              className="ml-auto h-6 w-6"
            >
              <X className="h-3 w-3" aria-hidden="true" />
            </Button>
          </li>
        ))}
      </ul>
      {items.length > 0 && (
        <div className="mt-2 flex justify-end">
          <Button variant="ghost" size="sm" onClick={onClearAll}>
            {strings.library.cart.clearAll}
          </Button>
        </div>
      )}
    </aside>
  )
}
