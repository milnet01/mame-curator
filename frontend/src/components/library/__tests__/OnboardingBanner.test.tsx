import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import {
  OnboardingBanner,
  ONBOARDING_DISMISS_KEY,
} from '@/components/library/OnboardingBanner'
import { strings } from '@/strings'

describe('OnboardingBanner', () => {
  beforeEach(() => localStorage.clear())

  it('renders body copy on first mount', () => {
    render(<OnboardingBanner cartHasItems={false} />)
    expect(
      screen.getByText(strings.library.onboarding.body),
    ).toBeInTheDocument()
  })

  it('hides itself after click on dismiss', () => {
    const { rerender } = render(<OnboardingBanner cartHasItems={false} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    rerender(<OnboardingBanner cartHasItems={false} />)
    expect(
      screen.queryByText(strings.library.onboarding.body),
    ).not.toBeInTheDocument()
  })

  it('persists dismissal across remounts via localStorage', () => {
    const { unmount } = render(<OnboardingBanner cartHasItems={false} />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    unmount()
    render(<OnboardingBanner cartHasItems={false} />)
    expect(
      screen.queryByText(strings.library.onboarding.body),
    ).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_DISMISS_KEY)).toBe('1')
  })

  it('auto-dismisses when cart has items even without click', () => {
    render(<OnboardingBanner cartHasItems={true} />)
    expect(
      screen.queryByText(strings.library.onboarding.body),
    ).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_DISMISS_KEY)).toBe('1')
  })
})
