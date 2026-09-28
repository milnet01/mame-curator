// mame-curator-1126 — Settings → Media folder fields for artwork another
// tool already scraped (ES-DE, RetroArch). Both settings are optional: an
// empty field means "not set", sent as null.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MediaTab } from "../MediaTab";
import type { AppConfigResponse } from "@/api/types";

function media(
  over: Partial<AppConfigResponse["media"]> = {},
): AppConfigResponse["media"] {
  return {
    fetch_videos: false,
    cache_dir: "/x",
    snaps_dir: "/x/snaps",
    esde_media_dir: null,
    retroarch_thumbnails_dir: null,
    arcadedb_rate_limit_per_min: 30,
    mobygames_rate_limit_per_min: 5,
    sources: ["libretro"],
    ...over,
  };
}

function renderTab(cfg = media(), onChange = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MediaTab media={cfg} onChange={onChange} />
    </QueryClientProvider>,
  );
  return { onChange };
}

describe("MediaTab — scraped-art folders", () => {
  it("shows an empty ES-DE field when the setting is unset", () => {
    renderTab();
    expect(screen.getByLabelText("ES-DE media folder")).toHaveValue("");
  });

  it("saves a typed ES-DE folder on blur", async () => {
    const { onChange } = renderTab();
    const field = screen.getByLabelText("ES-DE media folder");
    await userEvent.type(field, "/es/mame");
    await userEvent.tab();
    expect(onChange).toHaveBeenCalledWith("esde_media_dir", "/es/mame");
  });

  it("clears the RetroArch folder to null when emptied", async () => {
    const { onChange } = renderTab(
      media({ retroarch_thumbnails_dir: "/ra/thumbnails/MAME" }),
    );
    const field = screen.getByLabelText("RetroArch thumbnails folder");
    await userEvent.clear(field);
    await userEvent.tab();
    expect(onChange).toHaveBeenCalledWith("retroarch_thumbnails_dir", null);
  });
});
