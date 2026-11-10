/**
 * mame-curator-1146, picture half — choose the picture one version shows,
 * on the version guide's route. The choice is a (source, kind) pair the
 * server stores; see docs/specs/mame-curator-1146-picture-choice.md §4.6.
 */
import { useState } from "react";
import { PictureChoiceStep } from "@/components/guide/steps/PictureChoiceStep";
import {
  PictureDoneStep,
  type PictureOutcome,
} from "@/components/guide/steps/PictureDoneStep";
import type { PictureCandidate, PictureChoice } from "@/api/types";
import { usePictureCandidates, useSetPicture } from "@/hooks/usePicture";
import type { ReturnToLibrary } from "./libraryPageHelpers";

interface FixPictureGuideProps {
  /** The version in use when the guide opened. */
  name: string;
  /** Absent for a game with one version: there is no step before. */
  onBack?: () => void;
  back: ReturnToLibrary;
}

export function FixPictureGuide({ name, onBack, back }: FixPictureGuideProps) {
  const [further, setFurther] = useState(false);
  const list = usePictureCandidates(name, further);
  const setPicture = useSetPicture(name);
  const [outcome, setOutcome] = useState<PictureOutcome | null>(null);

  const apply = (choice: PictureChoice | null) => {
    setOutcome({ kind: "saving" });
    setPicture.mutate(choice, {
      onSuccess: () => setOutcome({ kind: "done", choice }),
      onError: (error) =>
        setOutcome({ kind: "failed", error, retry: () => apply(choice) }),
    });
  };
  const choose = (c: PictureCandidate) => {
    // The one in use: saving it again would change nothing.
    if (c.in_use) setOutcome({ kind: "unchanged" });
    else apply({ source: c.source, kind: c.kind });
  };

  if (outcome) {
    return (
      <PictureDoneStep
        name={name}
        outcome={outcome}
        onBack={() => setOutcome(null)}
        back={back}
      />
    );
  }
  return (
    <PictureChoiceStep
      name={name}
      list={list}
      onChoose={choose}
      onUseUsual={() => apply(null)}
      // A second press asks again: the places that did not answer may now.
      onLookFurther={() => (further ? void list.refetch() : setFurther(true))}
      onBack={onBack}
      back={back}
    />
  );
}
