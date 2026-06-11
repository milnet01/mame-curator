import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

  it('hides itself after click on dismiss', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<OnboardingBanner cartHasItems={false} />)
    await user.click(screen.getByRole('button', { name: /dismiss/i }))
    rerender(<OnboardingBanner cartHasItems={false} />)
    expect(
      screen.queryByText(strings.library.onboarding.body),
    ).not.toBeInTheDocument()
  })

  it('persists dismissal across remounts via localStorage', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<OnboardingBanner cartHasItems={false} />)
    await user.click(screen.getByRole('button', { name: /dismiss/i }))
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
