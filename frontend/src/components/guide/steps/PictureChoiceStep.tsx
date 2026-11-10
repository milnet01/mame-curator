import { GuideAction } from "@/components/guide/GuideAction";
import { GuideStep } from "@/components/guide/GuideStep";
import type { PictureCandidate, PictureCandidates } from "@/api/types";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

/** "Title screen, from your ES-DE pictures"; an unknown source shows its name. */
function pictureLabel({ source, kind }: PictureCandidate): string {
  const place =
    strings.guide.fix.picture.places[source] ??
    strings.guide.fix.picture.unknownPlace(source);
  return strings.guide.fix.picture.label(
    strings.guide.fix.picture.kinds[kind] ?? kind,
    place,
  );
}

/** One candidate's preview: only that source's picture, never a fallback. */
const previewSrc = (name: string, c: PictureCandidate) =>
  `/media/${encodeURIComponent(name)}/${c.kind}?source=${encodeURIComponent(c.source)}`;

interface PictureChoiceStepProps {
  /** The version the choice is for. */
  name: string;
  list: {
    data?: PictureCandidates;
    isError: boolean;
    isFetching: boolean;
    error: unknown;
    refetch: () => unknown;
  };
  onChoose: (candidate: PictureCandidate) => void;
  onUseUsual: () => void;
  onLookFurther: () => void;
  onBack?: () => void;
  back: unknown;
}

/** The pictures found, one large action each, with the extras §4.6 lists. */
function PictureList({
  name,
  data,
  onChoose,
  onUseUsual,
  onLookFurther,
}: Omit<PictureChoiceStepProps, "list" | "onBack" | "back"> & {
  data: PictureCandidates;
}) {
  const offerFurther =
    data.not_asked.length > 0 || data.not_answered.length > 0;
  return (
    <>
      {!data.chosen_found && (
        <p className="text-xl">{strings.guide.fix.picture.chosenMissing}</p>
      )}
      {data.not_answered.length > 0 && (
        <p className="text-xl">{strings.guide.fix.picture.notAnswered}</p>
      )}
      {data.candidates.length === 0 && (
        <p className="text-xl">{strings.guide.fix.picture.none}</p>
      )}
      {data.candidates.map((c) => (
        <GuideAction key={`${c.source}.${c.kind}`} onClick={() => onChoose(c)}>
          <span className="flex w-full flex-col gap-2 py-2">
            {/* Empty alt: the label beside it says the same. */}
            <img src={previewSrc(name, c)} alt="" className="w-full" />
            <span>{pictureLabel(c)}</span>
            {c.in_use && (
              <span className="text-lg font-semibold">
                {strings.guide.fix.inUse}
              </span>
            )}
          </span>
        </GuideAction>
      ))}
      {offerFurther && (
        <GuideAction onClick={onLookFurther}>
          {strings.guide.fix.picture.lookFurther}
        </GuideAction>
      )}
      {data.chosen && (
        <GuideAction onClick={onUseUsual}>
          {strings.guide.fix.picture.useUsual}
        </GuideAction>
      )}
    </>
  );
}

/** mame-curator-1146 §4.6 step 2: which picture the game should show. */
export function PictureChoiceStep({
  list,
  onBack,
  back,
  ...rest
}: PictureChoiceStepProps) {
  const body = (() => {
    if (list.isFetching || (!list.data && !list.isError)) {
      return (
        <p role="status" className="text-xl">
          {strings.guide.fix.picture.looking}
        </p>
      );
    }
    if (!list.data) {
      return (
        <>
          <p role="alert" className="text-xl text-destructive">
            {apiErrorMessage(list.error)}
          </p>
          <GuideAction primary onClick={() => void list.refetch()}>
            {strings.guide.fix.tryAgain}
          </GuideAction>
        </>
      );
    }
    return <PictureList data={list.data} {...rest} />;
  })();
  return (
    <GuideStep
      heading={strings.guide.fix.picture.heading}
      onBack={onBack}
      exitLabel={strings.guide.fix.toLibrary}
      exitState={back}
    >
      <p className="text-xl">{strings.guide.fix.picture.thisVersionOnly}</p>
      {body}
    </GuideStep>
  );
}
