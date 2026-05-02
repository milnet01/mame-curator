import { describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { useKeyboard } from '../useKeyboard'

function Probe({
  bindings,
}: {
  bindings: Parameters<typeof useKeyboard>[0]
}) {
  useKeyboard(bindings)
  return <div tabIndex={0} data-testid="probe" />
}

describe('useKeyboard', () => {
  it('fires a single-key binding on document keydown', async () => {
    const handler = vi.fn()
    render(<Probe bindings={[{ combo: '/', handler }]} />)
    await userEvent.keyboard('/')
    expect(handler).toHaveBeenCalled()
  })

  it('fires a chord binding only after both keys arrive', async () => {
    const handler = vi.fn()
    render(<Probe bindings={[{ combo: 'g l', handler }]} />)
    await userEvent.keyboard('g')
    expect(handler).not.toHaveBeenCalled()
    await userEvent.keyboard('l')
    expect(handler).toHaveBeenCalled()
  })

  it('does not fire while typing in an input unless the binding is meta-keyed', async () => {
    const slash = vi.fn()
    const cmdK = vi.fn()
    render(
      <>
        <input data-testid="search" />
        <Probe
          bindings={[
            { combo: '/', handler: slash },
            { combo: 'k', handler: cmdK, meta: true },
          ]}
        />
      </>,
    )
    const input = document.querySelector(
      '[data-testid="search"]',
    ) as HTMLInputElement
    input.focus()
    await userEvent.type(input, '/')
    expect(slash).not.toHaveBeenCalled()
    await userEvent.keyboard('{Meta>}k{/Meta}')
    expect(cmdK).toHaveBeenCalled()
  })
})
