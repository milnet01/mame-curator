/**
 * mame-curator-1254 — the Paths tab's listxml row, where the Library's
 * listxml notice sends the user.
 */
import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SettingsPage } from "../SettingsPage";
import { config, render } from "./_settingsPageFixtures";

describe("SettingsPage — listxml row", () => {
  it("mame-curator-1254: has a listxml row that patches paths.listxml", async () => {
    const user = userEvent.setup();
    const onPatch = vi.fn();
    render(
      <SettingsPage
        config={config}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    );
    const input = screen.getByLabelText("MAME listxml file");
    await user.type(input, "/mame/listxml.xml");
    await user.tab();
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ listxml: "/mame/listxml.xml" }),
      }),
    );
    expect(
      screen.getByText(
        "A new listxml file is read the next time the app starts.",
      ),
    ).toBeInTheDocument();
  });

  it("mame-curator-1254: saves an empty listxml as null", async () => {
    const user = userEvent.setup();
    const onPatch = vi.fn();
    render(
      <SettingsPage
        config={{ ...config, paths: { ...config.paths, listxml: "/old.xml" } }}
        onPatch={onPatch}
        onSnapshotRestore={() => {}}
      />,
    );
    await user.clear(screen.getByLabelText("MAME listxml file"));
    await user.tab();
    expect(onPatch).toHaveBeenCalledWith(
      expect.objectContaining({
        paths: expect.objectContaining({ listxml: null }),
      }),
    );
  });
});
