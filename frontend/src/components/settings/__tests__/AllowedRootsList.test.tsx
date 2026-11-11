// mame-curator-1175: Settings' list of the drives and folders granted in the picker.
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AllowedRootsList } from "../AllowedRootsList";
import { strings } from "@/strings";
import { server, http, HttpResponse } from "@/test/handlers";

const s = strings.settings;
const HOME = { id: "home", path: "/home/me", source: "config" };
const USB = { id: "usb", path: "/run/media/me/USB", source: "granted" };
const GONE = { id: "gone", path: "/mnt/old-games", source: "granted" };

let deleted: string[] = [];

function serve(roots: object[], missing: object[]) {
  server.use(
    http.get("/api/fs/allowed-roots", () =>
      HttpResponse.json({ roots, missing }),
    ),
    http.delete("/api/fs/allowed-roots/:id", ({ params }) => {
      deleted.push(String(params.id));
      return HttpResponse.json({
        roots: roots.filter((r) => (r as { id: string }).id !== params.id),
        missing: missing.filter((r) => (r as { id: string }).id !== params.id),
      });
    }),
  );
}

beforeEach(() => {
  deleted = [];
});

function renderList() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AllowedRootsList />
    </QueryClientProvider>,
  );
}

describe("AllowedRootsList (mame-curator-1175)", () => {
  it("lists only what was granted, marking a folder that is gone", async () => {
    serve([HOME, USB], [GONE]);
    renderList();
    const list = await screen.findByRole("list", { name: s.allowedTitle });
    const rows = within(list).getAllByRole("listitem");
    expect(rows.map((r) => r.textContent)).toEqual([
      expect.stringContaining(USB.path),
      expect.stringContaining(GONE.path),
    ]);
    expect(rows[1]).toHaveTextContent(s.allowedMissing);
    expect(rows[0]).not.toHaveTextContent(s.allowedMissing);
    expect(screen.queryByText(HOME.path)).not.toBeInTheDocument();
  });

  it("says when nothing has been granted", async () => {
    serve([HOME], []);
    renderList();
    expect(await screen.findByText(s.allowedNone)).toBeInTheDocument();
  });

  it("asks first, then removes, including a folder that is gone", async () => {
    serve([HOME, USB], [GONE]);
    const user = userEvent.setup();
    renderList();
    await user.click(
      await screen.findByRole("button", {
        name: s.allowedRemoveAria(GONE.path),
      }),
    );
    const prompt = await screen.findByRole("alertdialog");
    expect(prompt).toHaveTextContent(s.allowedRemoveConfirm(GONE.path));
    expect(deleted).toEqual([]);
    await user.click(
      within(prompt).getByRole("button", {
        name: strings.destructive.revokeRoot(GONE.path),
      }),
    );
    await waitFor(() => expect(deleted).toEqual(["gone"]));
    await waitFor(() =>
      expect(screen.queryByText(GONE.path)).not.toBeInTheDocument(),
    );
    expect(screen.getByText(USB.path)).toBeInTheDocument();
  });

  it("Cancel removes nothing", async () => {
    serve([HOME, USB], []);
    const user = userEvent.setup();
    renderList();
    await user.click(
      await screen.findByRole("button", {
        name: s.allowedRemoveAria(USB.path),
      }),
    );
    const prompt = await screen.findByRole("alertdialog");
    await user.click(
      within(prompt).getByRole("button", { name: strings.common.cancel }),
    );
    await waitFor(() =>
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
    );
    expect(deleted).toEqual([]);
    expect(screen.getByText(USB.path)).toBeInTheDocument();
  });
});
