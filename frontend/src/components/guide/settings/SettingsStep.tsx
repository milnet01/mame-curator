/**
 * mame-curator-1147 — the pieces every screen of the Settings guide shares.
 */
import type { ComponentProps } from "react";
import { GuideStep } from "../GuideStep";
import type { AppConfigResponse } from "@/api/types";
import { strings } from "@/strings";

/** A choice made on a topic's screen, and the words that say what it did. */
export interface Change {
  patch: Partial<AppConfigResponse>;
  saved: string;
  /** A second line under `saved`, where one is owed. */
  note?: string;
  /** The choice is the setting in use, so there is nothing to save. */
  same: boolean;
}

export interface TopicProps {
  config: AppConfigResponse;
  onChoose: (change: Change) => void;
  onBack: () => void;
}

/** A guide screen whose way out leads back to Settings. */
export function SettingsStep(
  props: Omit<ComponentProps<typeof GuideStep>, "exitLabel" | "exitTo">,
) {
  return (
    <GuideStep
      {...props}
      exitLabel={strings.guide.settings.toSettings}
      exitTo="/settings"
    />
  );
}

/** A choice's words, with what it holds now and whether it is in use. */
export function ChoiceLabel({
  label,
  detail,
  mark,
}: {
  label: string;
  detail?: string;
  mark?: string;
}) {
  return (
    <span className="flex min-w-0 flex-col">
      <span>{label}</span>
      {detail && (
        <span className="break-words text-lg text-muted-foreground">
          {detail}
        </span>
      )}
      {mark && <span className="text-lg font-semibold">{mark}</span>}
    </span>
  );
}
