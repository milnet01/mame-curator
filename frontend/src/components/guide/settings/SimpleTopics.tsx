/**
 * mame-curator-1147 — the Settings guide's one-question topics: which
 * region's versions to favour, and what a copy does to the cart.
 */
import { GuideAction } from "../GuideAction";
import { ChoiceLabel, SettingsStep, type TopicProps } from "./SettingsStep";
import type { AppConfigResponse } from "@/api/types";
import { strings } from "@/strings";

type CartPolicy = AppConfigResponse["ui"]["cart_clear_on_copy"];
const CART_POLICIES: readonly CartPolicy[] = ["always", "on_success", "never"];

export function RegionTopic({ config, onChoose, onBack }: TopicProps) {
  const regions = config.filters.region_priority;
  // The picker reads the list in order, so the chosen region goes first.
  const choose = (region: string) =>
    onChoose({
      patch: {
        filters: {
          ...config.filters,
          region_priority: [region, ...regions.filter((r) => r !== region)],
        },
      },
      saved: strings.guide.settings.region.saved(region),
      note: strings.guide.settings.region.yoursStay,
      same: region === regions[0],
    });
  return (
    <SettingsStep
      heading={strings.guide.settings.region.heading}
      onBack={onBack}
    >
      <p className="text-xl">
        {regions.length > 0
          ? strings.guide.settings.region.help
          : strings.guide.settings.region.none}
      </p>
      {regions.map((region, index) => (
        <GuideAction key={region} onClick={() => choose(region)}>
          <ChoiceLabel
            label={region}
            mark={
              index === 0 ? strings.guide.settings.region.firstNow : undefined
            }
          />
        </GuideAction>
      ))}
    </SettingsStep>
  );
}

export function CartTopic({ config, onChoose, onBack }: TopicProps) {
  const inUse = config.ui.cart_clear_on_copy;
  const choose = (policy: CartPolicy) =>
    onChoose({
      patch: { ui: { ...config.ui, cart_clear_on_copy: policy } },
      saved: strings.guide.settings.cart.saved[policy],
      same: policy === inUse,
    });
  return (
    <SettingsStep heading={strings.guide.settings.cart.heading} onBack={onBack}>
      {CART_POLICIES.map((policy) => (
        <GuideAction key={policy} onClick={() => choose(policy)}>
          <ChoiceLabel
            label={strings.guide.settings.cart.options[policy]}
            mark={policy === inUse ? strings.guide.settings.inUse : undefined}
          />
        </GuideAction>
      ))}
    </SettingsStep>
  );
}
