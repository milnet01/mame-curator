import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";

import { ActivityPage } from "../ActivityPage";
import { strings } from "@/strings";

const items: Record<string, unknown>[] = [
  {
    timestamp: "2026-05-02T10:00:00Z",
    event_type: "copy_finished",
    summary: "Copied 42 games",
    session_id: "sess-1",
  },
  {
    timestamp: "2026-05-02T09:00:00Z",
    event_type: "override_set",
    summary: "Override pacman → pacmanjr",
    session_id: "sess-2",
  },
];

function renderAt(initialEntry: string, total = 150, itemsOverride = items) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <ActivityPage pageSize={50} total={total} items={itemsOverride} />
    </MemoryRouter>,
  );
}

describe("ActivityPage", () => {
  it("renders the paginated feed", () => {
    renderAt("/activity", 2);
    expect(screen.getByText(/Copied 42 games/)).toBeInTheDocument();
    expect(screen.getByText(/Override pacman/)).toBeInTheDocument();
  });

  it("reads the initial page from the URL ?page query (FP11 § B4)", () => {
    renderAt("/activity?page=3", 200);
    expect(screen.getByText(/Page 3 of/)).toBeInTheDocument();
  });

  it("writes ?page when the user clicks Next", async () => {
    const user = userEvent.setup();
    renderAt("/activity?page=2", 200);
    await user.click(screen.getByRole("button", { name: /next/i }));
    // Page indicator advances from 2 → 3.
    expect(screen.getByText(/Page 3 of/)).toBeInTheDocument();
  });

  it("renders an empty state when items is empty", () => {
    renderAt("/activity", 0, []);
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument();
  });

  // mame-curator-1233 (CR-09-14): a ?page= past the end is not "no activity".
  it("offers the last page when ?page is past the end", async () => {
    const user = userEvent.setup();
    function Where() {
      return <p data-testid="where">{useLocation().search}</p>;
    }
    render(
      <MemoryRouter initialEntries={["/activity?page=9"]}>
        <ActivityPage pageSize={50} total={150} items={[]} />
        <Where />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/no activity yet/i)).toBeNull();
    await user.click(
      screen.getByRole("button", { name: strings.activity.goToLastPage }),
    );
    expect(screen.getByTestId("where")).toHaveTextContent("page=3");
  });
});
