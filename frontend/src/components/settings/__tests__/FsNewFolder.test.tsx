// mame-curator-1169: the folder picker's New folder button.
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { FsBrowser } from "../FsBrowser";
import { strings } from "@/strings";
import { server, http, HttpResponse } from "@/test/handlers";

const HOME = "/home/test";
const MADE = "/home/test/Arcade";
const s = strings.settings;

let posted: unknown[] = [];

function listing(path: string, parent: string | null) {
  return { path, parent, entries: [] };
}

beforeEach(() => {
  posted = [];
  server.use(
    http.get("/api/fs/home", () => HttpResponse.json({ path: HOME })),
    http.get("/api/fs/roots", () => HttpResponse.json({ roots: [] })),
    http.get("/api/fs/allowed-roots", () =>
      HttpResponse.json({
        roots: [{ id: "r1", path: HOME, source: "config" }],
      }),
    ),
    http.get("/api/fs/list", ({ request }) => {
      const path = new URL(request.url).searchParams.get("path");
      return HttpResponse.json(
        path === MADE ? listing(MADE, HOME) : listing(HOME, null),
      );
    }),
    http.post("/api/fs/folders", async ({ request }) => {
      posted.push(await request.json());
      return HttpResponse.json({ path: MADE });
    }),
  );
});

function renderPicker(mode: "directory" | "file" = "directory") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <FsBrowser open mode={mode} onOpenChange={() => {}} onPick={() => {}} />
    </QueryClientProvider>,
  );
}

/** The picker's location line says this folder. */
async function shows(path: string) {
  await waitFor(() =>
    expect(screen.getByRole("status")).toHaveTextContent(path),
  );
  expect(screen.getByRole("status").textContent).toBe(path);
}

/** Ready once the folder's contents have loaded. */
async function newFolderButton() {
  const find = () => screen.getByRole("button", { name: s.fsNewFolder });
  await waitFor(() => expect(find()).toBeEnabled());
  return find();
}

async function makeFolder(name: string) {
  const user = userEvent.setup();
  await user.click(await newFolderButton());
  await user.type(screen.getByLabelText(s.fsNewFolderName), name);
  await user.click(screen.getByRole("button", { name: s.fsNewFolderMake }));
}

describe("FsBrowser New folder (mame-curator-1169)", () => {
  it("makes the folder where you are, then opens it", async () => {
    renderPicker();
    await shows(HOME);
    await makeFolder("  Arcade  ");
    await shows(MADE);
    expect(posted).toEqual([{ parent: HOME, name: "Arcade" }]);
    expect(screen.queryByLabelText(s.fsNewFolderName)).not.toBeInTheDocument();
  });

  it("cannot make a folder with a blank name", async () => {
    const user = userEvent.setup();
    renderPicker();
    await user.click(await newFolderButton());
    await user.type(screen.getByLabelText(s.fsNewFolderName), "   ");
    expect(
      screen.getByRole("button", { name: s.fsNewFolderMake }),
    ).toBeDisabled();
  });

  it("says when the name is already there, and stays put", async () => {
    server.use(
      http.post("/api/fs/folders", () =>
        HttpResponse.json(
          { code: "fs_folder_exists", detail: "already there", fields: [] },
          { status: 409 },
        ),
      ),
    );
    renderPicker();
    await shows(HOME);
    await makeFolder("Arcade");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      s.fsNewFolderExists,
    );
    await shows(HOME);
    expect(screen.getByLabelText(s.fsNewFolderName)).toHaveValue("Arcade");
  });

  it("says when the folder could not be made", async () => {
    server.use(
      http.post("/api/fs/folders", () =>
        HttpResponse.json(
          { code: "fs_path_invalid", detail: "no", fields: [] },
          { status: 400 },
        ),
      ),
    );
    renderPicker();
    await shows(HOME);
    await makeFolder("Arcade.");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      s.fsNewFolderFailed,
    );
  });

  it("Cancel puts the button back without making anything", async () => {
    const user = userEvent.setup();
    renderPicker();
    await user.click(await newFolderButton());
    await user.type(screen.getByLabelText(s.fsNewFolderName), "Arcade");
    await user.click(
      screen.getAllByRole("button", { name: strings.common.cancel })[0],
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: s.fsNewFolder })).toHaveFocus(),
    );
    expect(posted).toEqual([]);
  });

  it("is not offered when choosing a file", async () => {
    renderPicker("file");
    await shows(HOME);
    expect(
      screen.queryByRole("button", { name: s.fsNewFolder }),
    ).not.toBeInTheDocument();
  });
});
