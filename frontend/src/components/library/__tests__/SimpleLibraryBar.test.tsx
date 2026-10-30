/** mame-curator-1144 review — the simple Library's search box. */
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { SimpleLibraryBar } from "../SimpleLibraryBar";

function bar(search: string, onSearch: (s: string) => void = () => {}) {
  return (
    <MemoryRouter>
      <SimpleLibraryBar
        search={search}
        onSearch={onSearch}
        filtersOn={false}
        onClearFilters={() => {}}
        shown={1}
        total={1}
        onMoreOptions={() => {}}
      />
    </MemoryRouter>
  );
}

describe("SimpleLibraryBar search box", () => {
  it("keeps what was typed while an older search comes back", async () => {
    const sent: string[] = [];
    const { rerender } = render(bar("", (s) => sent.push(s)));
    const box = screen.getByRole("searchbox");
    fireEvent.change(box, { target: { value: "pa" } });
    await screen.findByDisplayValue("pa");
    await new Promise((r) => setTimeout(r, 250)); // the debounce sends "pa"
    expect(sent).toEqual(["pa"]);
    fireEvent.change(box, { target: { value: "pac" } });
    rerender(bar("pa", (s) => sent.push(s))); // "pa" arrives after the key
    expect(box).toHaveValue("pac");
  });

  it("follows a search the page changed, such as Clear filters", async () => {
    const { rerender } = render(bar(""));
    const box = screen.getByRole("searchbox");
    fireEvent.change(box, { target: { value: "pa" } });
    await new Promise((r) => setTimeout(r, 250));
    rerender(bar("pa"));
    rerender(bar(""));
    expect(box).toHaveValue("");
  });
});
