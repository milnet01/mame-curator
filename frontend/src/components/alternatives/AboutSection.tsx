import { useWikipediaExtract } from '@/hooks/useWikipediaExtract'
import { strings } from '@/strings'

interface AboutSectionProps {
  shortName: string
}

/**
 * P10 chunk 11 — a one-paragraph Wikipedia "About" blurb in the Alternatives
 * drawer. Non-essential flavor: it renders nothing while loading, on error, or
 * when there's no Wikipedia page (null). The license line + "read more" link
 * satisfy Wikipedia's CC-BY-SA attribution requirement whenever text shows.
 */
export function AboutSection({ shortName }: AboutSectionProps) {
  const { data, isLoading, isError } = useWikipediaExtract(shortName)
  if (isLoading || isError) return null
  if (data == null) return null
  return (
    <section className="flex flex-col gap-1 text-sm text-muted-foreground">
      <p>{data.extract}</p>
      <a
        href={data.url}
        target="_blank"
        rel="noopener noreferrer"
        className="underline"
      >
        {strings.alternatives.wikipediaReadMore}
      </a>
      <p className="text-xs">{strings.alternatives.wikipediaLicense}</p>
    </section>
  )
}
