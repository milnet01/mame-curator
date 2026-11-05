import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { ApiError } from "@/api/client";
import { Toaster } from "@/components/ui/sonner";
import { strings } from "@/strings";
import {
  _resetApiErrorToastDedupForTests,
  toastApiError,
} from "../apiErrorToast";

// mame-curator-1190: an error toast stays until the user closes it, so a
// slow reader at large text has time to read it. Success toasts still go
// by themselves.

beforeEach(() => {
  // jsdom has no matchMedia, and the Toaster reads it.
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
});

afterEach(() => {
  act(() => toast.dismiss());
  vi.unstubAllGlobals();
  vi.useRealTimers();
  _resetApiErrorToastDedupForTests();
});

const refusal = () =>
  new ApiError({ code: "game_not_found", detail: "nope", fields: [] }, 404);

describe("error toasts (mame-curator-1190)", () => {
  it("an error toast is still on screen long after a success toast has gone", () => {
    vi.useFakeTimers();
    render(<Toaster />);
    act(() => {
      toastApiError(refusal());
      toast.success("Saved");
    });
    // Sonner adds a toast on the next tick.
    act(() => vi.advanceTimersByTime(10));
    expect(screen.getByText("Saved")).toBeInTheDocument();
    const message = strings.errors.byCode.game_not_found;
    expect(screen.getByText(message)).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(60_000));

    expect(screen.queryByText("Saved")).not.toBeInTheDocument();
    expect(screen.getByText(message)).toBeInTheDocument();
  });

  it("the error toast is announced and can be closed from the keyboard", async () => {
    const user = userEvent.setup();
    render(<Toaster />);
    act(() => toastApiError(refusal()));
    const message = strings.errors.byCode.game_not_found;
    const text = await screen.findByText(message);
    // Sonner's list is a polite live region, so a screen reader reads it out.
    expect(text.closest("[aria-live]")).toHaveAttribute("aria-live", "polite");

    const close = screen.getByRole("button", { name: "Close toast" });
    await user.keyboard("{Alt>}t{/Alt}");
    for (let i = 0; i < 5 && document.activeElement !== close; i++) {
      await user.tab();
    }
    expect(close).toHaveFocus();
    await user.keyboard("{Enter}");

    await vi.waitFor(() =>
      expect(screen.queryByText(message)).not.toBeInTheDocument(),
    );
  });
});
