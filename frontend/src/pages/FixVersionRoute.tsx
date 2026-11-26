/**
 * mame-curator-1146 — fix a game's version or picture one question at a
 * time, at /fix/:shortName. A game with several versions is first asked
 * which; one with a single version opens at the picture question. Saving goes through mame-curator-1149's
 * `useVersionChoice`, so the cart follows the choice as it does from the
 * Library. The version in use is the server's `in_use`, not `shortName`: a
 * typed address can name any version (mame-curator-1197).
 */
import { useState } from "react";
import { useParams } from "react-router";
import { GuideAction } from "@/components/guide/GuideAction";
import { GuideStep } from "@/components/guide/GuideStep";
import { FixWhatStep } from "@/components/guide/steps/FixWhatStep";
import { useAlternatives, useForgetChoices } from "@/hooks/useAlternatives";
import type { UseCartResult } from "@/hooks/useCart";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";
import type { Alternatives, GameCard } from "@/api/types";
import { FixPictureGuide } from "./FixPictureGuide";
import { useVersionChoice } from "./useVersionChoice";
import type { ReturnToLibrary } from "./libraryPageHelpers";

type Topic = "what" | "version" | "picture";

type Screen =
  | { kind: "choose" }
  | { kind: "saving" }
  | { kind: "saved"; name: string; unusable: string[] }
  | { kind: "unchanged"; name: string }
  | { kind: "failed"; error: unknown; game: GameCard };

interface FixVersionProps {
  cart: UseCartResult;
}

export function FixVersionRoute({ cart }: FixVersionProps) {
  const { shortName = "" } = useParams();
  // A new game starts the guide again, with nothing carried over.
  return <FixVersionGuide key={shortName} shortName={shortName} cart={cart} />;
}

function VersionLabel({ game, inUse }: { game: GameCard; inUse: boolean }) {
  const details = [game.year, game.manufacturer].filter(Boolean).join(" · ");
  return (
    <span className="flex flex-col">
      <span>{game.description}</span>
      {details && (
        <span className="text-lg text-muted-foreground">{details}</span>
      )}
      {inUse && (
        <span className="text-lg font-semibold">{strings.guide.fix.inUse}</span>
      )}
    </span>
  );
}

/** mame-curator-1189: saved choices that cannot be used, and the way to
 *  forget them, so the warning does not come back on every choice. */
function OldChoices({ unusable }: { unusable: string[] }) {
  const forget = useForgetChoices();
  if (forget.isSuccess) {
    return (
      <p role="status" className="text-xl">
        {strings.library.overrideForgotten(unusable.length)}
      </p>
    );
  }
  return (
    <>
      <p className="text-xl">
        {strings.library.overrideOldChoicesUnusable(unusable.length)}
      </p>
      {forget.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(forget.error)}
        </p>
      )}
      <GuideAction
        busy={forget.isPending}
        onClick={() => forget.mutate(unusable)}
      >
        {strings.library.overrideForgetOld(unusable.length)}
      </GuideAction>
    </>
  );
}

/** What happened to a choice: every screen after "Which version?". */
function OutcomeStep({
  screen,
  back,
  onBack,
  onRetry,
}: {
  screen: Exclude<Screen, { kind: "choose" }>;
  back: ReturnToLibrary;
  onBack: () => void;
  onRetry: (game: GameCard) => void;
}) {
  switch (screen.kind) {
    case "saving":
      return (
        <GuideStep
          heading={strings.guide.fix.savingHeading}
          exitLabel={strings.guide.fix.toLibrary}
          exitState={back}
        >
          {null}
        </GuideStep>
      );
    case "saved":
      return (
        <GuideStep
          heading={strings.library.overrideApplied(screen.name)}
          onBack={onBack}
          exitLabel={strings.guide.fix.toLibrary}
          exitState={back}
        >
          {screen.unusable.length > 0 && (
            <OldChoices unusable={screen.unusable} />
          )}
        </GuideStep>
      );
    case "unchanged":
      return (
        <GuideStep
          heading={strings.guide.fix.unchanged(screen.name)}
          onBack={onBack}
          exitLabel={strings.guide.fix.toLibrary}
          exitState={back}
        >
          <p className="text-xl">{strings.guide.fix.nothingChanged}</p>
        </GuideStep>
      );
    case "failed":
      return (
        <GuideStep
          heading={strings.guide.fix.failedHeading}
          onBack={onBack}
          exitLabel={strings.guide.fix.toLibrary}
          exitState={back}
        >
          <p role="alert" className="text-xl text-destructive">
            {apiErrorMessage(screen.error)}
          </p>
          <p className="text-xl">{strings.guide.fix.nothingChanged}</p>
          <GuideAction primary onClick={() => onRetry(screen.game)}>
            {strings.guide.fix.tryAgain}
          </GuideAction>
        </GuideStep>
      );
  }
}

/** Before the versions arrive: waiting, or saying why they did not. */
function LoadingStep({
  family,
  back,
}: {
  family: ReturnType<typeof useAlternatives>;
  back: ReturnToLibrary;
}) {
  return (
    <GuideStep
      heading={
        family.isError ? strings.guide.loadFailed : strings.guide.loading
      }
      exitLabel={strings.guide.fix.toLibrary}
      exitState={back}
    >
      {family.isError && (
        <>
          <p role="alert" className="text-xl text-destructive">
            {apiErrorMessage(family.error)}
          </p>
          <GuideAction
            primary
            busy={family.isFetching}
            onClick={() => void family.refetch()}
          >
            {strings.guide.fix.tryAgain}
          </GuideAction>
        </>
      )}
    </GuideStep>
  );
}

function FixVersionGuide({
  shortName,
  cart,
}: FixVersionProps & { shortName: string }) {
  const family = useAlternatives(shortName);
  const { chooseVersion } = useVersionChoice(cart);
  // useOverride reloads the family before onSaved, so this follows a save.
  const inUse = family.data?.in_use ?? null;
  const [screen, setScreen] = useState<Screen>({ kind: "choose" });
  const [topic, setTopic] = useState<Topic | null>(null);
  const toChoice = () => setScreen({ kind: "choose" });
  // The Library shows the version in use; without one, the address's game.
  const back: ReturnToLibrary = { focusCard: inUse ?? shortName };

  const choose = (game: GameCard, versions: Alternatives) => {
    if (game.short_name === inUse) {
      setScreen({ kind: "unchanged", name: game.description });
      return;
    }
    setScreen({ kind: "saving" });
    chooseVersion(
      { parent: versions.parent, winner: game.short_name },
      versions,
      {
        onSaved: (_warnings, unusable) => {
          setScreen({ kind: "saved", name: game.description, unusable });
        },
        onFailed: (error) => setScreen({ kind: "failed", error, game }),
      },
    );
  };

  if (!family.data) return <LoadingStep family={family} back={back} />;
  const versions = family.data;

  const several = versions.items.length > 1;
  const shown = topic ?? (several ? "what" : "picture");
  if (shown === "what") {
    return (
      <FixWhatStep
        onVersion={() => setTopic("version")}
        onPicture={() => setTopic("picture")}
        back={back}
      />
    );
  }
  if (shown === "picture") {
    // The version in use: after a version save, the reloaded `in_use`.
    const name = inUse ?? shortName;
    return (
      <FixPictureGuide
        key={name}
        name={name}
        onBack={several ? () => setTopic("what") : undefined}
        back={back}
      />
    );
  }
  if (screen.kind !== "choose") {
    return (
      <OutcomeStep
        screen={screen}
        back={back}
        onBack={toChoice}
        onRetry={(game) => choose(game, versions)}
      />
    );
  }
  return (
    <GuideStep
      heading={strings.guide.fix.heading}
      onBack={() => setTopic("what")}
      exitLabel={strings.guide.fix.toLibrary}
      exitState={back}
    >
      {versions.items.map((game) => (
        <GuideAction
          key={game.short_name}
          onClick={() => choose(game, versions)}
        >
          <VersionLabel game={game} inUse={game.short_name === inUse} />
        </GuideAction>
      ))}
    </GuideStep>
  );
}
