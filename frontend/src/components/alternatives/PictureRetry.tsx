import { useState } from "react";

import { Button } from "@/components/ui/button";
import { usePictureRetry } from "@/hooks/usePicture";
import { usePictureLook } from "@/lib/pictureLook";
import { pictureSrc } from "@/lib/pictureSrc";
import { strings } from "@/strings";
import type { PictureChoice } from "@/api/types";

/**
 * mame-curator-1143: "Look for a picture again", for a game with no picture.
 *
 * The server remembers a missing picture for 7 days. This asks it to forget
 * and look now. A hidden copy of the card's picture tells whether the game
 * has one: the button shows only when it fails to load.
 */
export function PictureRetry({
  shortName,
  picture,
}: {
  shortName: string;
  picture: PictureChoice | null;
}) {
  const src = pictureSrc(
    { short_name: shortName, picture },
    usePictureLook(shortName),
  );
  // Failed for this address only: a fresh look is a new address.
  const [missingSrc, setMissingSrc] = useState<string | null>(null);
  const retry = usePictureRetry(shortName);
  const missing = missingSrc === src;

  let status: string | null = null;
  if (missing) {
    if (retry.isError) status = strings.alternatives.pictureRetryFailed;
    else if (retry.data?.found === false)
      status = strings.alternatives.pictureStillMissing;
    else status = strings.alternatives.pictureMissing;
  } else if (retry.data?.found) {
    status = strings.alternatives.pictureFound;
  }

  return (
    <>
      <img
        src={src}
        alt=""
        hidden
        data-testid="picture-probe"
        onError={() => setMissingSrc(src)}
      />
      {missing && (
        <Button
          size="lg"
          variant="outline"
          className="h-auto min-h-11 whitespace-normal py-2 text-base"
          onClick={() => retry.mutate()}
          disabled={retry.isPending}
        >
          {retry.isPending
            ? strings.alternatives.pictureRetrying
            : strings.alternatives.pictureRetry}
        </Button>
      )}
      {status !== null && (
        <p role="status" className="text-sm text-muted-foreground">
          {status}
        </p>
      )}
    </>
  );
}
