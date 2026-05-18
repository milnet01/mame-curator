/**
 * Shared frontend-test fixtures.
 *
 * Created by the 2026-05-18 test-audit FP05 fold-in. Holds value objects
 * that several test files would otherwise inline byte-for-byte —
 * extracting them lets the test author state intent ("typical filters
 * state") instead of redeclaring 11 fields and forces every consumer to
 * move together if the underlying interface changes.
 */
import type { FilterSidebarState } from '@/components/library/FiltersSidebar'

/**
 * Canonical neutral ``FilterSidebarState`` used as the starting state
 * for tests that don't care about specific filter input (rendering
 * tests, prefs invariant tests, callback-signature tests).
 *
 * Use ``{ ...baseFiltersValue, search: 'pac' }`` to vary one field.
 */
export const baseFiltersValue: FilterSidebarState = {
  search: '',
  yearRange: [1980, 2010],
  letter: null,
  genre: null,
  publisher: null,
  developer: null,
  onlyContested: false,
  onlyOverridden: false,
  onlyChdMissing: false,
  onlyBiosMissing: false,
  reviewState: 'all',
}
