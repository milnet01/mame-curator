/**
 * mame-curator-1199 — a copy's Activity entry can name the games it skipped
 * or failed, read from the copy's report.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { ActivityPage } from "../ActivityPage";
import { strings } from "@/strings";
import { renderWithClient } from "@/test/renderWithClient";
import { http, HttpResponse, server } from "@/test/handlers";

const names = strings.activity.copyNames;

function copyEntry(skipped: number, failed: number) {
  return {
    timestamp: "2026-11-10T12:00:01Z",
    event_type: "copy_finished",
    summary: `copy partial_failure: 1 ok, ${skipped} skipped, ${failed} failed`,
    session_id: "20261110T120001Z-0badc0de",
    details: {
      event_type: "copy_finished",
      report_summary: {
        succeeded_count: 1,
        skipped_count: skipped,
        failed_count: failed,
        bytes_copied: 10,
      },
    },
  };
}

function renderEntry(entry: Record<string, unknown>) {
  const { wrapper: Wrapper } = renderWithClient();
  render(
    <Wrapper>
      <MemoryRouter initialEntries={["/activity"]}>
        <ActivityPage pageSize={50} total={1} items={[entry]} />
      </MemoryRouter>
    </Wrapper>,
  );
}

describe("a copy's skipped and failed games in Activity", () => {
  it("names them, with the reason, behind Show which", async () => {
    const asked: string[] = [];
    server.use(
      http.get("/api/activity/copy/:session/names", ({ params }) => {
        asked.push(String(params.session));
        return HttpResponse.json({
          skipped: [
            {
              short_name: "galaga",
              role: "winner",
              status: "SKIPPED_MISSING_SOURCE",
              error: null,
            },
          ],
          failed: [
            {
              short_name: "dkong",
              role: "winner",
              status: "FAILED",
              error: "disk full",
            },
          ],
        });
      }),
    );
    renderEntry(copyEntry(1, 1));
    const show = screen.getByRole("button", { name: names.show });
    expect(show).toHaveAttribute("aria-expanded", "false");
    expect(asked).toEqual([]);
    await userEvent.click(show);
    expect(
      await screen.findByText(`galaga: ${names.reason.SKIPPED_MISSING_SOURCE}`),
    ).toBeInTheDocument();
    expect(screen.getByText("dkong: disk full")).toBeInTheDocument();
    expect(asked).toEqual(["20261110T120001Z-0badc0de"]);
    expect(show).toHaveAttribute("aria-expanded", "true");
  });

  it("says the names are not available when the report is gone", async () => {
    server.use(
      http.get("/api/activity/copy/:session/names", () =>
        HttpResponse.json(
          { code: "job_not_found", detail: "no", fields: [] },
          { status: 404 },
        ),
      ),
    );
    renderEntry(copyEntry(2, 0));
    await userEvent.click(screen.getByRole("button", { name: names.show }));
    expect(await screen.findByText(names.unavailable)).toBeInTheDocument();
  });

  it("offers nothing when the copy skipped and failed nothing", () => {
    renderEntry(copyEntry(0, 0));
    expect(
      screen.queryByRole("button", { name: names.show }),
    ).not.toBeInTheDocument();
  });
});
