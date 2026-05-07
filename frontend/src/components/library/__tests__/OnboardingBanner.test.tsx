import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import {
  OnboardingBanner,
  ONBOARDING_DISMISS_KEY,
} from '@/components/library/OnboardingBanner'

describe('OnboardingBanner', () => {
  beforeEach(() => localStorage.clear())

  it('renders body copy on first mount', () => {
    render(<OnboardingBanner cartHasItems={false} />)
    expect(
      screen.getByText(/Tap a game to add it to your list/i),
    ).toBeInTheDocument()
  })

  it('hides itself after click on dismiss', () => {
    const { rerender } = render(<OnboardingBanner cartHasItems={false} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    rerender(<OnboardingBanner cartHasItems={false} />)
    expect(screen.queryByText(/Tap a game/i)).not.toBeInTheDocument()
  })

  it('persists dismissal across remounts via localStorage', () => {
    const { unmount } = render(<OnboardingBanner cartHasItems={false} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    unmount()
    render(<OnboardingBanner cartHasItems={false} />)
    expect(screen.queryByText(/Tap a game/i)).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_DISMISS_KEY)).toBe('1')
  })

  it('auto-dismisses when cart has items even without click', () => {
    render(<OnboardingBanner cartHasItems={true} />)
    expect(screen.queryByText(/Tap a game/i)).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_DISMISS_KEY)).toBe('1')
  })
})
