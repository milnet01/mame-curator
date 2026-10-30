/**
 * User-facing string catalogue — re-export facade.
 *
 * **DS02 A3:** the actual catalogue lives in `strings_internal.ts`;
 * `strings.ts` re-exports the public surface so every existing
 * `import { strings, type FeaturedTile, ... } from '@/strings'` call
 * site keeps working unchanged. Leaves `strings.ts` itself as a stable
 * import target for future i18n work: a future `strings.<lang>.ts` swap
 * touches only the catalogue modules, which are `strings_internal.ts` and
 * `strings_guide.ts`.
 */
import { guideStrings } from "./strings_guide";
import { strings as catalogue } from "./strings_internal";

export const strings = { ...catalogue, guide: guideStrings };

export { type FeaturedTile, type FeaturedTileQuery } from "./strings_internal";
