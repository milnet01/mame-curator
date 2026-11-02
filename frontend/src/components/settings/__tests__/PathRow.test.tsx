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
