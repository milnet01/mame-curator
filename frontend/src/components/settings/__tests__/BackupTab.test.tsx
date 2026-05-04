import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { BackupTab } from '../BackupTab'

afterEach(() => cleanup())

const VALID_BUNDLE_JSON =
  '{"config":{},"overrides":{},"sessions":{},"notes":{}}'

const sampleFile = () =>
  new File([VALID_BUNDLE_JSON], 'backup.json', {
    type: 'application/json',
  })

describe('BackupTab (FP12 § J + FP13 § B1/B3)', () => {
  it('renders Export and Import controls', () => {
    render(<BackupTab onExport={() => {}} onImport={() => {}} />)
    expect(screen.getByRole('button', { name: /^Export/ })).toBeInTheDocument()
    expect(screen.getByLabelText(/^Import/)).toBeInTheDocument()
  })

  it('renders the Phase-8 forward-link banner', () => {
    render(<BackupTab onExport={() => {}} onImport={() => {}} />)
    expect(screen.getByText(/setup wizard/i)).toBeInTheDocument()
  })

  it('calls onExport when Export is clicked', async () => {
    const onExport = vi.fn()
    render(<BackupTab onExport={onExport} onImport={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /^Export/ }))
    expect(onExport).toHaveBeenCalledOnce()
  })

  it('opens a confirmation dialog when a valid file is selected', async () => {
    render(<BackupTab onExport={() => {}} onImport={() => {}} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    await userEvent.upload(input, sampleFile())
    expect(
      screen.getByRole('alertdialog', { name: /replace configuration/i }),
    ).toBeInTheDocument()
  })

  it('uses a concrete action label naming the file (design §8)', async () => {
    render(<BackupTab onExport={() => {}} onImport={() => {}} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    await userEvent.upload(input, sampleFile())
    expect(
      screen.getByRole('button', { name: 'Replace settings from backup.json' }),
    ).toBeInTheDocument()
  })

  it('calls onImport with the parsed bundle only after confirming (FP13 § B1)', async () => {
    const onImport = vi.fn()
    render(<BackupTab onExport={() => {}} onImport={onImport} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    await userEvent.upload(input, sampleFile())
    expect(onImport).not.toHaveBeenCalled()
    await userEvent.click(
      screen.getByRole('button', { name: 'Replace settings from backup.json' }),
    )
    expect(onImport).toHaveBeenCalledExactlyOnceWith({
      config: {},
      overrides: {},
      sessions: {},
      notes: {},
    })
  })

  it('does not call onImport when the dialog is cancelled', async () => {
    const onImport = vi.fn()
    render(<BackupTab onExport={() => {}} onImport={onImport} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    await userEvent.upload(input, sampleFile())
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onImport).not.toHaveBeenCalled()
  })

  it('renders a parent-supplied error message when error is set', () => {
    render(
      <BackupTab onExport={() => {}} onImport={() => {}} error="Bad bundle." />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/bad bundle/i)
  })

  it('rejects a file whose JSON parse fails — no dialog opens (FP13 § B1)', async () => {
    const onImport = vi.fn()
    render(<BackupTab onExport={() => {}} onImport={onImport} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    const garbage = new File(['{ not json'], 'garbage.json', {
      type: 'application/json',
    })
    await userEvent.upload(input, garbage)
    expect(screen.getByRole('alert')).toHaveTextContent(/not a valid JSON/i)
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('rejects a file whose schema does not match — no dialog opens (FP13 § B1)', async () => {
    const onImport = vi.fn()
    render(<BackupTab onExport={() => {}} onImport={onImport} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    // Valid JSON but wrong shape (missing required keys + extra key).
    const wrongShape = new File([JSON.stringify({ unrelated: 1 })], 'wrong.json', {
      type: 'application/json',
    })
    await userEvent.upload(input, wrongShape)
    expect(screen.getByRole('alert')).toHaveTextContent(
      /not a configuration bundle/i,
    )
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('rejects a file larger than the size cap — no parse, no dialog (FP13 § B3)', async () => {
    const onImport = vi.fn()
    render(<BackupTab onExport={() => {}} onImport={onImport} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    // Build a 6 MB blob — over the 5 MB cap. Content can be empty padding;
    // size check happens before parse, so the body never matters.
    const huge = new File(['x'.repeat(6 * 1024 * 1024)], 'huge.json', {
      type: 'application/json',
    })
    await userEvent.upload(input, huge)
    expect(screen.getByRole('alert')).toHaveTextContent(/too large/i)
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })
})
