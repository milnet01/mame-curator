import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { DryRunModal } from '../DryRunModal'
import type { DryRunReport } from '@/api/types'

const report: DryRunReport = {
  counts: {
    new: 12,
    replace: 3,
    skip: 5,
    bios_included: 2,
  },
  summary: {},
}

describe('DryRunModal', () => {
  it('renders new / replace / skip counts when open', () => {
    render(
      <DryRunModal
        open
        onOpenChange={() => {}}
        report={report}
        onConfirm={() => {}}
      />,
    )
    expect(screen.getByText(/12 new/)).toBeInTheDocument()
    expect(screen.getByText(/3 replace/)).toBeInTheDocument()
    expect(screen.getByText(/5 skip/)).toBeInTheDocument()
    expect(screen.getByText(/2 BIOS/)).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(
      <DryRunModal
        open={false}
        onOpenChange={() => {}}
        report={report}
        onConfirm={() => {}}
      />,
    )
    expect(screen.queryByText(/12 new/)).not.toBeInTheDocument()
  })

  it('calls onConfirm when the confirm button is clicked', async () => {
    const onConfirm = vi.fn()
    render(
      <DryRunModal
        open
        onOpenChange={() => {}}
        report={report}
        onConfirm={onConfirm}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /^copy/i }))
    expect(onConfirm).toHaveBeenCalled()
  })
})
