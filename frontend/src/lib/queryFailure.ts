interface QueryFailureState {
  isError: boolean;
  isFetching: boolean;
  errorUpdatedAt: number;
  dataUpdatedAt: number;
}

/**
 * Whether a page should show its load failure. A retry clears `isError` while
 * it runs, so going by that alone would unmount the Try again button, and the
 * user's focus with it (FP26-V).
 */
export function loadFailed(query: QueryFailureState): boolean {
  return (
    query.isError ||
    (query.isFetching && query.errorUpdatedAt > query.dataUpdatedAt)
  );
}
