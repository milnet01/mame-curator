/**
 * mame-curator-1147 — which kinds of games the library leaves out: first
 * the kind, then yes or no. Only the switches whose effect is plain.
 */
import { useState } from "react";
import { GuideAction } from "../GuideAction";
import { ChoiceLabel, SettingsStep, type TopicProps } from "./SettingsStep";
import { strings } from "@/strings";

type Kind = keyof typeof strings.guide.settings.leaveOut.kinds;
const KINDS = Object.keys(strings.guide.settings.leaveOut.kinds) as Kind[];

export function LeaveOutTopic({ config, onChoose, onBack }: TopicProps) {
  const [kind, setKind] = useState<Kind | null>(null);
  const filters = config.filters;

  if (kind === null) {
    return (
      <SettingsStep
        heading={strings.guide.settings.leaveOut.heading}
        onBack={onBack}
      >
        {KINDS.map((k) => (
          <GuideAction key={k} onClick={() => setKind(k)}>
            <ChoiceLabel
              label={strings.guide.settings.leaveOut.kinds[k].name}
              mark={
                filters[k]
                  ? strings.guide.settings.leaveOut.leftOutNow
                  : strings.guide.settings.leaveOut.includedNow
              }
            />
          </GuideAction>
        ))}
      </SettingsStep>
    );
  }

  const about = strings.guide.settings.leaveOut.kinds[kind];
  const choose = (leaveOut: boolean) =>
    onChoose({
      patch: { filters: { ...filters, [kind]: leaveOut } },
      saved: leaveOut
        ? strings.guide.settings.leaveOut.leftOut(about.name)
        : strings.guide.settings.leaveOut.included(about.name),
      same: leaveOut === filters[kind],
    });
  const inUse = (leaveOut: boolean) =>
    leaveOut === filters[kind] ? strings.guide.settings.inUse : undefined;
  return (
    <SettingsStep
      heading={strings.guide.settings.leaveOut.question(about.inSentence)}
      onBack={() => setKind(null)}
    >
      <p className="text-xl">{about.help}</p>
      <GuideAction onClick={() => choose(true)}>
        <ChoiceLabel
          label={strings.guide.settings.leaveOut.yes}
          mark={inUse(true)}
        />
      </GuideAction>
      <GuideAction onClick={() => choose(false)}>
        <ChoiceLabel
          label={strings.guide.settings.leaveOut.no}
          mark={inUse(false)}
        />
      </GuideAction>
    </SettingsStep>
  );
}
