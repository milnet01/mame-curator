/**
 * User-facing string catalogue — re-export facade.
 *
 * **DS02 A3:** the actual catalogue lives in `strings_internal.ts`;
 * `strings.ts` re-exports the public surface so every existing
 * `import { strings, type FeaturedTile, ... } from '@/strings'` call
 * site keeps working unchanged. Keeps the catalogue file at
 * `strings_internal.ts` below the project's 500-line hard cap and
 * leaves `strings.ts` itself as a stable import target for future
 * i18n work (a future `strings.<lang>.ts` swap touches only
 * `strings_internal.ts`).
 */

export { strings, type FeaturedTile, type FeaturedTileQuery } from './strings_internal'
