/**
 * mame-curator-1143 — "Look for a picture again" in the game's panel.
 * Shown only when the game's picture did not load; it asks the server to
 * forget the remembered miss and look now.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { http, HttpResponse, server } from "@/test/handlers";
import { strings } from "@/strings";
import { PictureRetry } from "../PictureRetry";

function renderRetry(shortName: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return render(<PictureRetry shortName={shortName} picture={null} />, {
    wrapper,
  });
}

const button = () =>
  screen.queryByRole("button", { name: strings.alternatives.pictureRetry });

describe("PictureRetry", () => {
  it("shows nothing while the game has a picture", () => {
    renderRetry("hasart");
    fireEvent.load(screen.getByTestId("picture-probe"));
    expect(button()).toBeNull();
  });

  it("offers the button when the picture did not load", () => {
    renderRetry("noart");
    fireEvent.error(screen.getByTestId("picture-probe"));
    expect(button()).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      strings.alternatives.pictureMissing,
    );
  });

  it("looks again, and loads the picture it found", async () => {
    server.use(
      http.post("/api/media/:name/retry", ({ params }) =>
        HttpResponse.json({ short_name: params.name, found: true }),
      ),
    );
    renderRetry("foundart");
    fireEvent.error(screen.getByTestId("picture-probe"));
    await userEvent.click(button()!);
    expect(await screen.findByRole("status")).toHaveTextContent(
      strings.alternatives.pictureFound,
    );
    expect(screen.getByTestId("picture-probe")).toHaveAttribute(
      "src",
      "/media/foundart/boxart?r=1",
    );
    expect(button()).toBeNull();
  });

  it("says so when there is still no picture", async () => {
    server.use(
      http.post("/api/media/:name/retry", ({ params }) =>
        HttpResponse.json({ short_name: params.name, found: false }),
      ),
    );
    renderRetry("stillnone");
    fireEvent.error(screen.getByTestId("picture-probe"));
    await userEvent.click(button()!);
    expect(await screen.findByRole("status")).toHaveTextContent(
      strings.alternatives.pictureStillMissing,
    );
    expect(button()).toBeInTheDocument();
  });

  it("says so when the look failed", async () => {
    server.use(
      http.post("/api/media/:name/retry", () =>
        HttpResponse.json(
          { detail: "boom", code: "internal", fields: [] },
          { status: 500 },
        ),
      ),
    );
    renderRetry("failedlook");
    fireEvent.error(screen.getByTestId("picture-probe"));
    await userEvent.click(button()!);
    expect(await screen.findByRole("status")).toHaveTextContent(
      strings.alternatives.pictureRetryFailed,
    );
  });
});
