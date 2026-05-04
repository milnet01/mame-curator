import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { BackupTab } from '../BackupTab'

afterEach(() => cleanup())

const sampleFile = () =>
  new File(['{"config":{},"overrides":{},"sessions":{},"notes":{}}'], 'backup.json', {
    type: 'application/json',
  })

describe('BackupTab (FP12 § J)', () => {
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

  it('opens a confirmation dialog when a file is selected', async () => {
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

  it('calls onImport with the file only after confirming', async () => {
    const onImport = vi.fn()
    const file = sampleFile()
    render(<BackupTab onExport={() => {}} onImport={onImport} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    await userEvent.upload(input, file)
    expect(onImport).not.toHaveBeenCalled()
    await userEvent.click(
      screen.getByRole('button', { name: 'Replace settings from backup.json' }),
    )
    expect(onImport).toHaveBeenCalledExactlyOnceWith(file)
  })

  it('does not call onImport when the dialog is cancelled', async () => {
    const onImport = vi.fn()
    render(<BackupTab onExport={() => {}} onImport={onImport} />)
    const input = screen.getByLabelText(/^Import/) as HTMLInputElement
    await userEvent.upload(input, sampleFile())
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onImport).not.toHaveBeenCalled()
  })

  it('renders an error message when error is set', () => {
    render(
      <BackupTab onExport={() => {}} onImport={() => {}} error="Bad bundle." />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/bad bundle/i)
  })
})
