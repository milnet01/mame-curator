import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { useFacets } from "@/hooks/useFacets";
import { strings } from "@/strings";

interface ChooseStepProps {
  stepNumber: number;
  stepCount: number;
  onBack: () => void;
}

export function ChooseGroupStep({
  stepNumber,
  stepCount,
  onBack,
  onChoose,
}: ChooseStepProps & { onChoose: (tileId: string) => void }) {
  return (
    <GuideStep
      heading={strings.guide.chooseGroup.heading}
      stepNumber={stepNumber}
      stepCount={stepCount}
      onBack={onBack}
      exitLabel={strings.guide.exit}
    >
      {strings.library.featured.tiles.map((tile) => (
        <GuideAction key={tile.id} onClick={() => onChoose(tile.id)}>
          {tile.title}
        </GuideAction>
      ))}
    </GuideStep>
  );
}

export function ChooseTypeStep({
  stepNumber,
  stepCount,
  onBack,
  onChoose,
}: ChooseStepProps & { onChoose: (genre: string) => void }) {
  const facets = useFacets();
  const genres = facets.data?.genres ?? [];
  return (
    <GuideStep
      heading={strings.guide.chooseType.heading}
      stepNumber={stepNumber}
      stepCount={stepCount}
      onBack={onBack}
      exitLabel={strings.guide.exit}
    >
      {facets.isPending && <p className="text-xl">{strings.guide.loading}</p>}
      {facets.isError && (
        <p role="alert" className="text-xl text-destructive">
          {strings.guide.loadFailed}
        </p>
      )}
      {facets.isSuccess && genres.length === 0 && (
        <p className="text-xl">{strings.guide.chooseType.none}</p>
      )}
      {genres.map((genre) => (
        <GuideAction key={genre} onClick={() => onChoose(genre)}>
          {genre}
        </GuideAction>
      ))}
    </GuideStep>
  );
}
