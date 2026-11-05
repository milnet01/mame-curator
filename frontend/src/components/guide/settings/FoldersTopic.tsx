/**
 * mame-curator-1147 — where the games are, and where they are copied to.
 * The questions and the large picker are the setup wizard's
 * (mame-curator-1145); the game list stays on the Settings page, where
 * swapping it asks first.
 */
import { useState } from "react";
import { GuideAction } from "../GuideAction";
import { ChoiceLabel, SettingsStep, type TopicProps } from "./SettingsStep";
import { FsBrowser } from "@/components/settings/FsBrowser";
import { strings } from "@/strings";

type Folder = "source_roms" | "dest_roms";

const FOLDERS: Record<
  Folder,
  {
    label: string;
    heading: string;
    saved: (path: string) => string;
    sameAsOther: string;
  }
> = {
  source_roms: {
    label: strings.guide.settings.folders.games,
    heading: strings.guide.setup.games.heading,
    saved: strings.guide.settings.folders.gamesSaved,
    sameAsOther: strings.guide.settings.folders.sameAsDest,
  },
  dest_roms: {
    label: strings.guide.settings.folders.dest,
    heading: strings.guide.setup.dest.heading,
    saved: strings.guide.settings.folders.destSaved,
    sameAsOther: strings.guide.settings.folders.sameAsGames,
  },
};
const OTHER: Record<Folder, Folder> = {
  source_roms: "dest_roms",
  dest_roms: "source_roms",
};

export function FoldersTopic({ config, onChoose, onBack }: TopicProps) {
  const [folder, setFolder] = useState<Folder | null>(null);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [focusKey, setFocusKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const paths = config.paths;

  if (folder === null) {
    return (
      <SettingsStep
        heading={strings.guide.settings.folders.heading}
        onBack={onBack}
      >
        {(Object.keys(FOLDERS) as Folder[]).map((f) => (
          <GuideAction key={f} onClick={() => setFolder(f)}>
            <ChoiceLabel label={FOLDERS[f].label} detail={paths[f]} />
          </GuideAction>
        ))}
      </SettingsStep>
    );
  }

  const about = FOLDERS[folder];
  // As in the setup wizard: with no trigger to return to, the dialog would
  // otherwise drop focus on the page, and this user with it.
  const closePicker = (open: boolean) => {
    setBrowseOpen(open);
    if (!open) setFocusKey((key) => key + 1);
  };
  // mame-curator-1145 INV-11: the server also refuses it, by resolved path.
  const pick = (path: string) => {
    if (path === paths[OTHER[folder]]) {
      setError(about.sameAsOther);
      return;
    }
    onChoose({
      patch: { paths: { ...paths, [folder]: path } },
      saved: about.saved(path),
      same: path === paths[folder],
    });
  };
  const back = () => {
    setError(null);
    setFolder(null);
  };

  return (
    <SettingsStep heading={about.heading} focusKey={focusKey} onBack={back}>
      <p className="break-words text-2xl font-medium">{paths[folder]}</p>
      <p className="text-lg font-semibold">{strings.guide.settings.inUse}</p>
      {error && (
        <p role="alert" className="text-xl text-destructive">
          {error}
        </p>
      )}
      <GuideAction primary onClick={() => setBrowseOpen(true)}>
        {strings.guide.settings.folders.choose}
      </GuideAction>
      {browseOpen && (
        <FsBrowser
          open
          large
          simple
          onOpenChange={closePicker}
          onPick={pick}
          initialPath={paths[folder]}
        />
      )}
    </SettingsStep>
  );
}
