/**
 * mame-curator-1147 — change a setting one topic at a time, at
 * /settings/guide. Each choice saves through PATCH /api/config, as the
 * Settings page saves, and the next screen says what changed. The full
 * Settings page keeps every other setting.
 */
import { useState } from "react";
import { GuideAction } from "@/components/guide/GuideAction";
import { FoldersTopic } from "@/components/guide/settings/FoldersTopic";
import { LeaveOutTopic } from "@/components/guide/settings/LeaveOutTopic";
import {
  SettingsStep,
  type Change,
  type TopicProps,
} from "@/components/guide/settings/SettingsStep";
import {
  CartTopic,
  RegionTopic,
} from "@/components/guide/settings/SimpleTopics";
import { useConfig, useConfigPatch } from "@/hooks/useConfig";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

type Topic = keyof typeof strings.guide.settings.topics;

const TOPICS: Record<Topic, (props: TopicProps) => React.JSX.Element> = {
  folders: FoldersTopic,
  leaveOut: LeaveOutTopic,
  region: RegionTopic,
  cart: CartTopic,
};

type Screen =
  | { kind: "menu" }
  | { kind: "topic"; topic: Topic }
  | { kind: "saving" }
  | { kind: "saved"; change: Change }
  | { kind: "unchanged" }
  | { kind: "failed"; error: unknown; change: Change };

/** What happened to a choice: every screen after a topic's question. */
function OutcomeStep({
  screen,
  onMore,
  onRetry,
}: {
  screen: Extract<
    Screen,
    { kind: "saving" | "saved" | "unchanged" | "failed" }
  >;
  onMore: () => void;
  onRetry: (change: Change) => void;
}) {
  const more = (
    <GuideAction primary onClick={onMore}>
      {strings.guide.settings.changeMore}
    </GuideAction>
  );
  switch (screen.kind) {
    case "saving":
      return (
        <SettingsStep heading={strings.guide.settings.savingHeading}>
          {null}
        </SettingsStep>
      );
    case "saved":
      return (
        <SettingsStep heading={screen.change.saved}>
          {screen.change.note && (
            <p className="text-xl">{screen.change.note}</p>
          )}
          {more}
        </SettingsStep>
      );
    case "unchanged":
      return (
        <SettingsStep heading={strings.guide.settings.unchangedHeading}>
          <p className="text-xl">{strings.guide.settings.nothingChanged}</p>
          {more}
        </SettingsStep>
      );
    case "failed":
      return (
        <SettingsStep
          heading={strings.guide.settings.failedHeading}
          onBack={onMore}
        >
          <p role="alert" className="text-xl text-destructive">
            {apiErrorMessage(screen.error)}
          </p>
          <p className="text-xl">{strings.guide.settings.nothingChanged}</p>
          <GuideAction primary onClick={() => onRetry(screen.change)}>
            {strings.guide.settings.tryAgain}
          </GuideAction>
        </SettingsStep>
      );
  }
}

export function SettingsGuidePage() {
  const config = useConfig();
  // quiet: each screen says the outcome itself, so no toast repeats it.
  const patch = useConfigPatch({ quiet: true });
  const [screen, setScreen] = useState<Screen>({ kind: "menu" });
  const toMenu = () => setScreen({ kind: "menu" });

  const choose = (change: Change) => {
    if (change.same) {
      setScreen({ kind: "unchanged" });
      return;
    }
    setScreen({ kind: "saving" });
    patch.mutate(change.patch, {
      onSuccess: () => setScreen({ kind: "saved", change }),
      onError: (error) => setScreen({ kind: "failed", error, change }),
    });
  };

  if (!config.data) {
    return (
      <SettingsStep
        heading={
          config.isError ? strings.guide.loadFailed : strings.guide.loading
        }
      >
        {config.isError && (
          <p role="alert" className="text-xl text-destructive">
            {apiErrorMessage(config.error)}
          </p>
        )}
      </SettingsStep>
    );
  }
  if (screen.kind === "topic") {
    const TopicStep = TOPICS[screen.topic];
    return <TopicStep config={config.data} onChoose={choose} onBack={toMenu} />;
  }
  if (screen.kind !== "menu") {
    return <OutcomeStep screen={screen} onMore={toMenu} onRetry={choose} />;
  }
  return (
    <SettingsStep heading={strings.guide.settings.heading}>
      {(Object.keys(TOPICS) as Topic[]).map((topic) => (
        <GuideAction
          key={topic}
          onClick={() => setScreen({ kind: "topic", topic })}
        >
          {strings.guide.settings.topics[topic]}
        </GuideAction>
      ))}
    </SettingsStep>
  );
}
