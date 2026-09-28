import { afterEach, describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { server, http, HttpResponse } from "@/test/handlers";
import { makeClientWrapper } from "@/test/renderWithClient";
import { UpdateStartupToast } from "../UpdateStartupToast";

vi.mock("sonner", () => ({ toast: { message: vi.fn() } }));

import { toast } from "sonner";

afterEach(() => vi.mocked(toast.message).mockClear());

function answer(update_available: boolean) {
  return {
    app: {
      current_version: "1.3.0",
      latest_version: "1.4.0",
      update_available,
      install_kind: "git",
      can_apply: update_available,
      notes_html: null,
      release_url: null,
      check_error: null,
      restart_pending: false,
      rollback_available: false,
    },
    ini: [],
  };
}

function renderToast(enabled: boolean) {
  const Wrapper = makeClientWrapper();
  render(
    <Wrapper>
      <MemoryRouter>
        <UpdateStartupToast enabled={enabled} />
      </MemoryRouter>
    </Wrapper>,
  );
}

describe("UpdateStartupToast (mame-curator-1010 §4.7)", () => {
  it("toasts once when the startup check finds an update", async () => {
    const seen = vi.fn();
    server.use(
      http.get("/api/updates/check", () => {
        seen();
        return HttpResponse.json(answer(true));
      }),
    );
    renderToast(true);
    await waitFor(() =>
      expect(vi.mocked(toast.message)).toHaveBeenCalledOnce(),
    );
    expect(vi.mocked(toast.message).mock.calls[0][0]).toContain("1.4.0");
    expect(seen).toHaveBeenCalledOnce();
  });

  it("stays silent when there is no update", async () => {
    const seen = vi.fn();
    server.use(
      http.get("/api/updates/check", () => {
        seen();
        return HttpResponse.json(answer(false));
      }),
    );
    renderToast(true);
    await waitFor(() => expect(seen).toHaveBeenCalledOnce());
    expect(vi.mocked(toast.message)).not.toHaveBeenCalled();
  });

  it("does not check at all when check_on_startup is off", async () => {
    const seen = vi.fn();
    server.use(
      http.get("/api/updates/check", () => {
        seen();
        return HttpResponse.json(answer(true));
      }),
    );
    renderToast(false);
    await new Promise((r) => setTimeout(r, 50));
    expect(seen).not.toHaveBeenCalled();
    expect(vi.mocked(toast.message)).not.toHaveBeenCalled();
  });
});
