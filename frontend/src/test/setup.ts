import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './handlers'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// jsdom lacks a real ResizeObserver — `@tanstack/react-virtual` waits on it
// for the initial measurement and renders zero rows until it fires. Trigger
// the callback synchronously on observe so the virtualizer measures right
// away in component tests.
class TestResizeObserver {
  private cb: ResizeObserverCallback
  constructor(cb: ResizeObserverCallback) {
    this.cb = cb
  }
  observe(target: Element) {
    this.cb(
      [
        {
          target,
          contentRect: target.getBoundingClientRect(),
        } as ResizeObserverEntry,
      ],
      this as unknown as ResizeObserver,
    )
  }
  unobserve() {}
  disconnect() {}
}

;(globalThis as { ResizeObserver?: typeof TestResizeObserver }).ResizeObserver =
  TestResizeObserver
