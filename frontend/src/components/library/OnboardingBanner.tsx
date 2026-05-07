import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

export const ONBOARDING_DISMISS_KEY = 'mame-curator:onboarding-dismissed:v1'

interface OnboardingBannerProps {
  cartHasItems: boolean
}

/**
 * P15 § 4.4 — first-load instructional banner above the grid.
 * Dismissed in two ways: explicit ✕ click, or auto on first
 * cart.add (cartHasItems flips true). Both persist in
 * localStorage so the banner stays gone across reloads.
 */
export function OnboardingBanner({ cartHasItems }: OnboardingBannerProps) {
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(ONBOARDING_DISMISS_KEY) === '1',
  )

  useEffect(() => {
    if (cartHasItems && !dismissed) {
      setDismissed(true)
      try {
        localStorage.setItem(ONBOARDING_DISMISS_KEY, '1')
      } catch {
        /* private browsing / quota — degrade silently */
      }
    }
  }, [cartHasItems, dismissed])

  if (dismissed) return null

  const handleDismiss = () => {
    setDismissed(true)
    try {
      localStorage.setItem(ONBOARDING_DISMISS_KEY, '1')
    } catch {
      /* see above */
    }
  }

  return (
    <div
      role="status"
      className="mx-4 mt-2 flex items-center gap-3 rounded border bg-muted/40 px-3 py-2 text-sm"
    >
      <span>{strings.library.onboarding.body}</span>
      <Button
        size="icon"
        variant="ghost"
        onClick={handleDismiss}
        aria-label={strings.library.onboarding.dismissAriaLabel}
        className="ml-auto h-6 w-6"
      >
        <X className="h-3 w-3" aria-hidden="true" />
      </Button>
    </div>
  )
}
