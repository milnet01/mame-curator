import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { FolderField } from "../FolderField";
import { PathRow } from "../PathRow";
import { http, HttpResponse, server } from "@/test/handlers";

function listed() {
  const paths: string[] = [];
  server.use(
    http.get("/api/fs/home", () => HttpResponse.json({ path: "/home/me" })),
    http.get("/api/fs/roots", () => HttpResponse.json({ roots: [] })),
    http.get("/api/fs/allowed-roots", () => HttpResponse.json({ roots: [] })),
    http.get("/api/fs/list", ({ request }) => {
      const path = new URL(request.url).searchParams.get("path")!;
      paths.push(path);
      return HttpResponse.json({ path, parent: null, entries: [] });
    }),
  );
  return paths;
}

function inClient(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

const row = (props: Partial<React.ComponentProps<typeof PathRow>>) => (
  <PathRow id="r" label="Thing" value="" onChange={() => {}} {...props} />
);

describe("PathRow Browse (mame-curator-1145 review)", () => {
  it("on a file row opens the folder that holds the file", async () => {
    const user = userEvent.setup();
    const paths = listed();
    inClient(row({ mode: "file", value: "/mnt/lists/mame.dat" }));
    await user.click(screen.getByRole("button", { name: /browse/i }));
    await waitFor(() => expect(paths).toEqual(["/mnt/lists"]));
  });

  it("on a folder row opens the folder itself", async () => {
    const user = userEvent.setup();
    const paths = listed();
    inClient(row({ value: "/mnt/roms" }));
    await user.click(screen.getByRole("button", { name: /browse/i }));
    await waitFor(() => expect(paths).toEqual(["/mnt/roms"]));
  });

  it("on an empty file row opens home", async () => {
    const user = userEvent.setup();
    const paths = listed();
    inClient(row({ mode: "file" }));
    await user.click(screen.getByRole("button", { name: /browse/i }));
    await waitFor(() => expect(paths).toEqual(["/home/me"]));
  });
});

describe("a save the server refuses (mame-curator-1145 review)", () => {
  it("PathRow goes back to the saved path, and does not send it again", () => {
    const onChange = vi.fn();
    inClient(row({ value: "/saved", onChange }));
    const field = screen.getByRole("textbox");
    fireEvent.change(field, { target: { value: "/refused" } });
    fireEvent.blur(field);
    expect(onChange).toHaveBeenCalledExactlyOnceWith("/refused");
    // The parent's value did not change, because the server said no.
    expect(field).toHaveValue("/saved");
    fireEvent.blur(field);
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("PathRow shows the new path once it is saved", () => {
    const qc = new QueryClient();
    const ui = (value: string) => (
      <QueryClientProvider client={qc}>{row({ value })}</QueryClientProvider>
    );
    const { rerender } = render(ui("/saved"));
    const field = screen.getByRole("textbox");
    fireEvent.change(field, { target: { value: "/new" } });
    fireEvent.blur(field);
    rerender(ui("/new"));
    expect(field).toHaveValue("/new");
  });

  it("FolderField goes back to the saved path, and does not send it again", () => {
    const onCommit = vi.fn();
    inClient(
      <FolderField
        id="f"
        label="Folder"
        browseLabel="Browse"
        value="/saved"
        onCommit={onCommit}
      />,
    );
    const field = screen.getByRole("textbox");
    fireEvent.change(field, { target: { value: "/refused" } });
    fireEvent.blur(field);
    expect(onCommit).toHaveBeenCalledExactlyOnceWith("/refused");
    expect(field).toHaveValue("/saved");
    fireEvent.blur(field);
    expect(onCommit).toHaveBeenCalledTimes(1);
  });
});

// mame-curator-1176: the pickers have no Radix trigger, so focus fell to the
// page when they closed. It goes back to Browse.
describe("Settings folder pickers give focus back (mame-curator-1176)", () => {
  const browse = () => screen.getByRole("button", { name: /browse/i });
  const closed = () =>
    waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    });

  it("PathRow: Cancel gives focus back to Browse", async () => {
    const user = userEvent.setup();
    listed();
    inClient(row({ value: "/mnt/roms" }));
    await user.click(browse());
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /^cancel$/i }));
    await closed();
    expect(browse()).toHaveFocus();
  });

  it("PathRow: Esc gives focus back to Browse", async () => {
    const user = userEvent.setup();
    listed();
    inClient(row({ value: "/mnt/roms" }));
    browse().focus();
    await user.keyboard("{Enter}");
    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");
    await closed();
    expect(browse()).toHaveFocus();
  });

  it("PathRow: choosing a folder gives focus back to Browse", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    listed();
    inClient(row({ value: "/mnt/roms", onChange }));
    await user.click(browse());
    const use = await screen.findByRole("button", { name: /use this folder/i });
    await waitFor(() => expect(use).toBeEnabled());
    await user.click(use);
    await closed();
    expect(onChange).toHaveBeenCalledWith("/mnt/roms");
    expect(browse()).toHaveFocus();
  });

  it("PathRow: cancelling the grant prompt gives focus back to Browse", async () => {
    const user = userEvent.setup();
    listed();
    server.use(
      http.get("/api/fs/list", () =>
        HttpResponse.json(
          { code: "fs_sandboxed", detail: "outside", fields: [] },
          { status: 403 },
        ),
      ),
    );
    inClient(row({ value: "/etc" }));
    await user.click(browse());
    await screen.findByRole("alertdialog");
    await user.click(screen.getByRole("button", { name: /^cancel$/i }));
    await closed();
    expect(browse()).toHaveFocus();
  });

  it("FolderField: Esc gives focus back to Browse", async () => {
    const user = userEvent.setup();
    listed();
    inClient(
      <FolderField
        id="f"
        label="Folder"
        browseLabel="Browse for the folder"
        value="/mnt/roms"
        onCommit={() => {}}
      />,
    );
    await user.click(browse());
    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");
    await closed();
    expect(browse()).toHaveFocus();
  });

  it("the picker does not open with focus on Cancel, so Enter does not close it", async () => {
    const user = userEvent.setup();
    listed();
    inClient(row({ value: "/mnt/roms" }));
    browse().focus();
    await user.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog");
    expect(screen.getByRole("button", { name: /^cancel$/i })).not.toHaveFocus();
    expect(dialog.contains(document.activeElement)).toBe(true);
    await user.keyboard("{Enter}");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
