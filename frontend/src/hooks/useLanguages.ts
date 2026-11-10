import { LanguageChoicesSchema, type LanguageChoices } from "@/api/types";
import { useApiQuery } from "./useApi";

/**
 * mame-curator-1217 — GET /api/languages: each language languages.ini names,
 * most games first, for choosing `filters.keep_languages`.
 */
export function useLanguages() {
  return useApiQuery<LanguageChoices>(
    ["languages"],
    "/api/languages",
    LanguageChoicesSchema,
    { staleTime: 60_000 },
  );
}
