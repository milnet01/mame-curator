import { useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { useUpdatesCheck } from "@/hooks/useUpdates";
import { strings } from "@/strings";

/**
 * mame-curator-1010 §4.7: one check at app start when
 * `updates.check_on_startup` is on; an update found shows a toast whose
 * button opens Settings → Updates (design § 6.7). A failed or empty check
 * shows nothing.
 */
export function UpdateStartupToast({ enabled }: { enabled: boolean }) {
  const navigate = useNavigate();
  const check = useUpdatesCheck(enabled);
  const shown = useRef(false);
  const app = check.data?.app;
  useEffect(() => {
    if (!enabled || shown.current || !app?.update_available) return;
    if (!app.latest_version) return;
    shown.current = true;
    toast.message(strings.settings.updates.startupToast(app.latest_version), {
      action: {
        label: strings.settings.updates.startupToastAction,
        onClick: () => navigate("/settings?tab=updates"),
      },
    });
  }, [enabled, app, navigate]);
  return null;
}
