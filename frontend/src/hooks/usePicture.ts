import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import {
  PictureCandidatesSchema,
  PictureChoiceViewSchema,
  type PictureCandidates,
  type PictureChoice,
  type PictureChoiceView,
} from "@/api/types";
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
