import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { FsBrowser } from "@/components/settings/FsBrowser";
import { apiRequest } from "@/api/client";
import { DatCheckSchema } from "@/api/schemas";
import type { SetupCheck } from "@/api/types";
import {
  refreshEverything,
  useConfig,
  useConfigPatch,
} from "@/hooks/useConfig";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { folderOf } from "@/lib/folderOf";
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
  const patch = useConfigPatch({ quiet: true });
  const queryClient = useQueryClient();
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<Partial<Record<Answer, string>>>({});
  const [focusKey, setFocusKey] = useState(0);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // mame-curator-1208: the list step asks the server whether a file starts as
  // a game list, so a wrong one is refused here, not after the last step.
  const datCheck = useMutation({
    mutationFn: (path: string) =>
      apiRequest(
        `/api/setup/dat-check?path=${encodeURIComponent(path)}`,
        DatCheckSchema,
      ),
  });

  const step = STEPS[stepIndex]!;
  const words = step.words;
  const chosen = answers[step.answer];
  const saving = patch.isPending;
  const checking = datCheck.isPending;
  const paths = config.data?.paths;

  // A choice moves focus to the heading, which says what was chosen. Cancel
  // leaves it to the picker, which gives it back to the button that opened it
  // (mame-curator-1206).
  const choose = (path: string) => {
    const answer = step.answer;
    setError(null);
    if (answer !== "source_dat") {
      setAnswers((prev) => ({ ...prev, [answer]: path }));
      setFocusKey((key) => key + 1);
      return;
    }
    datCheck.mutate(path, {
      onSuccess: ({ parses }) => {
        if (parses) setAnswers((prev) => ({ ...prev, [answer]: path }));
        else setError(strings.guide.setup.notAGameList);
      },
      onError: (err) => setError(apiErrorMessage(err)),
      onSettled: () => setFocusKey((key) => key + 1),
    });
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
        onSuccess: async (next) => {
          if (next.restart_required) {
            setAnswers((prev) => ({ ...prev, source_dat: undefined }));
            setStepIndex(LIST_STEP);
            setError(strings.guide.setup.notAGameList);
            return;
          }
          // A repeat press after the alert below: the server had nothing left
          // to end, so the hook did not refresh, and the page must still catch up.
          if (!next.setup_ended) await refreshEverything(queryClient);
          // Read the cache, not this render: the check can have its new answer
          // while React has not yet heard, and this page is about to leave.
          const check = queryClient.getQueryData<SetupCheck>([
            "setup",
            "check",
          ]);
          if (check?.setup_required) setError(strings.guide.loadFailed);
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
      {chosen === undefined && <p className="text-xl">{words.help}</p>}
      {/* On the page before the choice, so a screen reader hears the first. */}
      <p role="status" className="break-words text-2xl font-medium">
        {chosen}
      </p>
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
        {saving
          ? strings.guide.setup.reading
          : checking
            ? strings.guide.setup.checking
            : ""}
      </p>
      {chosen !== undefined && (
        <GuideAction
          primary
          busy={saving || checking}
          disabled={stepIndex === LAST_STEP && !paths}
          onClick={stepIndex === LAST_STEP ? finish : () => goTo(stepIndex + 1)}
        >
          {words.yes}
        </GuideAction>
      )}
      <GuideAction
        primary={chosen === undefined}
        busy={saving || checking}
        onClick={() => setBrowseOpen(true)}
      >
        {chosen === undefined ? words.choose : words.chooseAnother}
      </GuideAction>
      {browseOpen && (
        <FsBrowser
          open
          large
          simple
          onOpenChange={setBrowseOpen}
          onPick={choose}
          mode={step.answer === "source_dat" ? "file" : "directory"}
          // mame-curator-1208: the list step starts beside the list already
          // chosen, else in the games folder, where many keep it. The picker
          // draws only the rows near the window, so a big folder is fine.
          initialPath={
            step.answer === "source_dat"
              ? ((chosen && folderOf(chosen)) ?? answers.source_roms)
              : chosen
          }
        />
      )}
    </GuideStep>
  );
}
