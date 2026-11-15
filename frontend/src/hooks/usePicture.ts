import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import {
  PictureCandidatesSchema,
  PictureChoiceViewSchema,
  PictureRetrySchema,
  type PictureCandidates,
  type PictureChoice,
  type PictureChoiceView,
  type PictureRetry,
} from "@/api/types";
import { notePictureLook } from "@/lib/pictureLook";
import { useApiQuery } from "./useApi";

const pictureUrl = (shortName: string) =>
  `/api/games/${encodeURIComponent(shortName)}/picture`;

/**
 * mame-curator-1146: every picture the sources hold for ``shortName``.
 * ``further`` also asks the rate-limited sources. Never stale: the guide
 * shows what the server finds now.
 */
export function usePictureCandidates(shortName: string, further: boolean) {
  return useApiQuery<PictureCandidates>(
    ["picture-candidates", shortName, further],
    `${pictureUrl(shortName)}/candidates?further=${further}`,
    PictureCandidatesSchema,
    { staleTime: 0, gcTime: 0 },
  );
}

/**
 * Save (a choice) or clear (``null``) the game's picture. On success the
 * Library and every versions list reload, so the cards show the new
 * address (INV-11). A caller reports failure through ``mutate``'s
 * ``onError``.
 */
export function useSetPicture(shortName: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (choice: PictureChoice | null) =>
      apiRequest<PictureChoiceView>(
        pictureUrl(shortName),
        PictureChoiceViewSchema,
        choice === null
          ? { method: "DELETE" }
          : { method: "PUT", body: choice },
      ),
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["games"] }),
        qc.invalidateQueries({ queryKey: ["alternatives"] }),
      ]),
  });
}

/**
 * mame-curator-1143: forget that the game had no picture and look now.
 * A picture found is a fresh look, so every card showing the game asks
 * for it again.
 */
export function usePictureRetry(shortName: string) {
  return useMutation({
    mutationFn: () =>
      apiRequest<PictureRetry>(
        `/api/media/${encodeURIComponent(shortName)}/retry`,
        PictureRetrySchema,
        { method: "POST" },
      ),
    onSuccess: (result) => {
      if (result.found) notePictureLook(shortName);
    },
  });
}
