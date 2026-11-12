import { useWikipediaExtract } from "@/hooks/useWikipediaExtract";
import { strings } from "@/strings";
import { ExternalLink } from "@/components/ExternalLink";

interface AboutSectionProps {
  shortName: string;
}

/**
 * P10 chunk 11 — a one-paragraph Wikipedia "About" blurb in the Alternatives
 * drawer. Non-essential flavor: it renders nothing while loading, on error, or
 * when there's no Wikipedia page (null). The license line + "read more" link
 * satisfy Wikipedia's CC-BY-SA attribution requirement whenever text shows.
 */
export function AboutSection({ shortName }: AboutSectionProps) {
  const { data, isLoading, isError } = useWikipediaExtract(shortName);
  if (isLoading || isError) return null;
  if (data == null) return null;
  // The server-supplied url is typed `z.string()` — guard the scheme before
  // binding it into an href so a poisoned/MITM `javascript:` URL can't render
  // as a clickable link. Non-https drops the link, keeps the text. (FP32 M2)
  const safeUrl = data.url.startsWith("https://") ? data.url : null;
  return (
    <section className="flex flex-col gap-1 text-sm text-muted-foreground">
      <p>{data.extract}</p>
      {safeUrl && (
        <ExternalLink href={safeUrl}>
          {strings.alternatives.wikipediaReadMore}
        </ExternalLink>
      )}
      <p className="text-xs">{strings.alternatives.wikipediaLicense}</p>
    </section>
  );
}
