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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
;(globalThis as any).ResizeObserver = TestResizeObserver

// jsdom lacks `scrollIntoView`; cmdk and Radix's various scroll-into-view
// behaviours call it on focus changes. No-op is safe — tests don't assert
// on scroll position.
const proto = HTMLElement.prototype as unknown as Record<string, unknown>
if (!proto.scrollIntoView) {
  proto.scrollIntoView = function () {}
}
if (!proto.hasPointerCapture) {
  proto.hasPointerCapture = () => false
}
if (!proto.releasePointerCapture) {
  proto.releasePointerCapture = () => {}
}
