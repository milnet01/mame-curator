import { useState } from "react";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { FsBrowser } from "@/components/settings/FsBrowser";
import { useConfig, useConfigPatch } from "@/hooks/useConfig";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { playlistIn } from "@/lib/playlistPath";
import { strings } from "@/strings";

type Answer = "source_roms" | "source_dat" | "dest_roms";

const STEPS: readonly {
  answer: Answer;
  words: typeof strings.guide.setup.games;
}[] = [
  { answer: "source_roms", words: strings.guide.setup.games },
  { answer: "source_dat", words: strings.guide.setup.list },
  { answer: "dest_roms", words: strings.guide.setup.dest },
];
const LIST_STEP = 1;
const LAST_STEP = STEPS.length - 1;

/**
 * mame-curator-1145 — three questions, then one save, then the guide. See
 * docs/specs/mame-curator-1145-setup-wizard.md. Nothing is pre-filled, because
 * the starter config's folders are empty ones the app made.
 */
export function SetupWizard() {
  const config = useConfig();
  const patch = useConfigPatch();
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<Partial<Record<Answer, string>>>({});
  const [focusKey, setFocusKey] = useState(0);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const step = STEPS[stepIndex]!;
  const words = step.words;
  const chosen = answers[step.answer];
  const saving = patch.isPending;
  const paths = config.data?.paths;

  const choose = (path: string) => {
    setError(null);
    setAnswers((prev) => ({ ...prev, [step.answer]: path }));
  };

  // Every way out of the picker, Cancel too. With no trigger to return to, the
  // dialog would otherwise drop focus on the page, and this user with it.
  const closePicker = (open: boolean) => {
    setBrowseOpen(open);
    if (!open) setFocusKey((key) => key + 1);
  };

  const goTo = (index: number) => {
    setError(null);
    setStepIndex(index);
  };

  const finish = () => {
    const { source_roms, source_dat, dest_roms } = answers;
    if (!paths || !source_roms || !source_dat || !dest_roms) return;
    if (dest_roms === source_roms) {
      setError(strings.guide.setup.sameFolder);
      return;
    }
    setError(null);
    patch.mutate(
      {
        paths: {
          ...paths,
          source_roms,
          source_dat,
          dest_roms,
          // A user repairing a working setup keeps a playlist they placed.
          retroarch_playlist:
            dest_roms === paths.dest_roms
              ? paths.retroarch_playlist
              : playlistIn(dest_roms),
        },
      },
      {
        onSuccess: (next) => {
          if (next.restart_required) {
            setAnswers((prev) => ({ ...prev, source_dat: undefined }));
            setStepIndex(LIST_STEP);
            setError(strings.guide.setup.notAGameList);
          } else {
            // Good save, but the setup check could not say so: this page
            // would have left otherwise. Pressing again is safe.
            setError(strings.guide.loadFailed);
          }
        },
        onError: (err) => setError(apiErrorMessage(err)),
      },
    );
  };

  return (
    <GuideStep
      heading={chosen === undefined ? words.heading : words.chosenHeading}
      stepNumber={stepIndex + 1}
      stepCount={STEPS.length}
      focusKey={focusKey}
      onBack={stepIndex > 0 && !saving ? () => goTo(stepIndex - 1) : undefined}
      exitLabel={saving ? undefined : strings.guide.exit}
    >
      {chosen === undefined ? (
        <p className="text-xl">{words.help}</p>
      ) : (
        <p role="status" className="break-words text-2xl font-medium">
          {chosen}
        </p>
      )}
      {config.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(config.error)}
        </p>
      )}
      {error && (
        <p role="alert" className="text-xl text-destructive">
          {error}
        </p>
      )}
      {/* On the page before the save, so a screen reader hears it. */}
      <p role="status" className="text-xl">
        {saving ? strings.guide.setup.reading : ""}
      </p>
      {chosen !== undefined && (
        <GuideAction
          primary
          busy={saving}
          disabled={stepIndex === LAST_STEP && !paths}
          onClick={stepIndex === LAST_STEP ? finish : () => goTo(stepIndex + 1)}
        >
          {words.yes}
        </GuideAction>
      )}
      <GuideAction
        primary={chosen === undefined}
        busy={saving}
        onClick={() => setBrowseOpen(true)}
      >
        {chosen === undefined ? words.choose : words.chooseAnother}
      </GuideAction>
      {browseOpen && (
        <FsBrowser
          open
          large
          simple
          onOpenChange={closePicker}
          onPick={choose}
          mode={step.answer === "source_dat" ? "file" : "directory"}
          // The games folder can hold tens of thousands of files, and file
          // mode draws a row for each, so the list step starts at home.
          initialPath={step.answer === "source_dat" ? undefined : chosen}
        />
      )}
    </GuideStep>
  );
}
