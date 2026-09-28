import { useState } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PrefSwitch } from "@/components/settings/PrefSwitch";
import { strings } from "@/strings";
import { Button } from "@/components/ui/button";
import { IniRefreshPanel } from "@/components/settings/IniRefreshPanel";
import { ReleaseNotesDialog } from "@/components/settings/ReleaseNotesDialog";
import type {
  AppConfigResponse,
  AppUpdateInfo,
  IniPreview,
  UpdateApplyResult,
} from "@/api/types";

type UpdatesCfg = AppConfigResponse["updates"];
type UpdateChannel = UpdatesCfg["channel"];

const UPDATE_CHANNEL_VALUES: readonly UpdateChannel[] = ["stable", "dev"];

/** mame-curator-1010 §4.7 — the tab's actions, owned by SettingsRoute. */
export interface UpdateActions {
  onCheckNow: () => void;
  checking: boolean;
  /** The check request itself failed, so there is no banner to show. */
  checkFailed?: boolean;
  onApply: () => void;
  applying: boolean;
  applyResult?: UpdateApplyResult;
  onRollback: () => void;
  rollingBack: boolean;
  rollbackResult?: UpdateApplyResult;
  onIniPreview: () => void;
  iniPreviewing: boolean;
  iniPreview?: IniPreview;
  onIniApply: () => void;
  iniApplying: boolean;
  iniApplied: boolean;
}

interface UpdatesTabProps {
  updates: UpdatesCfg;
  onChange: <K extends keyof UpdatesCfg>(key: K, value: UpdatesCfg[K]) => void;
  /** R36 update-check payload — when present, drives the Updates banner. */
  updateInfo?: AppUpdateInfo;
  actions?: UpdateActions;
}

function CheckNowButton({ actions }: { actions: UpdateActions }) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={actions.onCheckNow}
      disabled={actions.checking}
    >
      {actions.checking
        ? strings.settings.updates.checking
        : strings.settings.updates.checkNow}
    </Button>
  );
}

/** A check with no answer yet, or none at all: keep the way to retry. */
function NoCheckYet({ actions }: { actions: UpdateActions }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <p role="status" className="text-sm">
        {actions.checkFailed
          ? strings.settings.updates.checkFailed
          : strings.settings.updates.checking}
      </p>
      <CheckNowButton actions={actions} />
    </div>
  );
}

function UpdateActionsRow({
  info,
  actions,
}: {
  info: AppUpdateInfo;
  actions: UpdateActions;
}) {
  const [notesOpen, setNotesOpen] = useState(false);
  const busy = actions.applying || actions.rollingBack;
  const result = actions.applyResult;
  const rollback = actions.rollbackResult;
  const restart =
    info.restart_pending ||
    (result?.install_kind === "git" && result.restart_required) ||
    Boolean(rollback?.restart_required);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        <CheckNowButton actions={actions} />
        {info.notes_html && info.latest_version && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setNotesOpen(true)}
          >
            {strings.settings.updates.whatsNew}
          </Button>
        )}
        {info.can_apply && !restart && (
          <Button size="sm" onClick={actions.onApply} disabled={busy}>
            {actions.applying
              ? strings.settings.updates.applying
              : info.install_kind === "bundle"
                ? strings.settings.updates.applyBundle
                : strings.settings.updates.applyGit}
          </Button>
        )}
        {info.install_kind === "package" &&
          info.update_available &&
          info.release_url && (
            <a
              href={info.release_url}
              target="_blank"
              rel="noopener noreferrer"
              className="self-center text-sm underline"
            >
              {strings.settings.updates.packageLink}
            </a>
          )}
        {info.rollback_available && (
          <Button
            variant="outline"
            size="sm"
            onClick={actions.onRollback}
            disabled={busy}
          >
            {actions.rollingBack
              ? strings.settings.updates.rollingBack
              : strings.settings.updates.rollback}
          </Button>
        )}
      </div>
      {result?.rolled_back && (
        <p role="alert" className="text-sm text-destructive">
          {strings.settings.updates.rolledBack}{" "}
          {result.sync_failed ? strings.settings.updates.syncFailed : ""}
        </p>
      )}
      {/* Mounted before any message, so a message appearing is a change a
          screen reader announces (WAI-ARIA live regions). */}
      <div role="status" className="flex flex-col gap-1 text-sm">
        {restart && <p>{strings.settings.updates.restartPending}</p>}
        {rollback?.sync_failed && <p>{strings.settings.updates.syncFailed}</p>}
        {result?.downloaded_path && (
          <p>{strings.settings.updates.downloaded(result.downloaded_path)}</p>
        )}
      </div>
      {info.notes_html && info.latest_version && (
        <ReleaseNotesDialog
          open={notesOpen}
          onOpenChange={setNotesOpen}
          version={info.latest_version}
          notesHtml={info.notes_html}
        />
      )}
    </div>
  );
}

export function UpdatesTab({
  updates,
  onChange,
  updateInfo,
  actions,
}: UpdatesTabProps) {
  return (
    <>
      {/* FP11 § B3: the R36 banner; mame-curator-1010 adds the actions. */}
      {updateInfo && (
        <p
          role="status"
          className="rounded border border-muted bg-muted/30 px-3 py-2 text-sm"
        >
          {updateInfo.update_available && updateInfo.latest_version
            ? strings.settings.banners.updateAvailable(
                updateInfo.current_version,
                updateInfo.latest_version,
              )
            : updateInfo.latest_version
              ? strings.settings.banners.updateCurrent(
                  updateInfo.current_version,
                )
              : strings.settings.banners.updateUnknown(
                  updateInfo.current_version,
                  updateInfo.check_error,
                )}
        </p>
      )}
      {updateInfo && actions && (
        <UpdateActionsRow info={updateInfo} actions={actions} />
      )}
      {!updateInfo && actions && <NoCheckYet actions={actions} />}
      <div className="flex items-center justify-between">
        <Label htmlFor="updates-channel">
          {strings.settings.updatesLabels.channel}
        </Label>
        <Select
          value={updates.channel}
          onValueChange={(v) => onChange("channel", v as UpdateChannel)}
        >
          <SelectTrigger
            id="updates-channel"
            aria-label={strings.settings.updatesLabels.channel}
            className="w-32"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {UPDATE_CHANNEL_VALUES.map((v) => (
              <SelectItem key={v} value={v}>
                {strings.settings.updateChannelOptions[v]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <PrefSwitch
        id="updates-check-on-startup"
        label={strings.settings.updatesLabels.check_on_startup}
        checked={updates.check_on_startup}
        onChange={(v) => onChange("check_on_startup", v)}
      />
      <PrefSwitch
        id="updates-ini-check-on-startup"
        label={strings.settings.updatesLabels.ini_check_on_startup}
        checked={updates.ini_check_on_startup}
        onChange={(v) => onChange("ini_check_on_startup", v)}
      />
      {actions && (
        <IniRefreshPanel
          onPreview={actions.onIniPreview}
          previewing={actions.iniPreviewing}
          preview={actions.iniPreview}
          onApply={actions.onIniApply}
          applying={actions.iniApplying}
          applied={actions.iniApplied}
        />
      )}
    </>
  );
}
