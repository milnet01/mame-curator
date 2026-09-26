# Cold-eyes loop log — `src/mame_curator/copy/spec.md`

Review history for the copy module spec, kept outside the spec because the
spec has never carried a loop log and its standard does not require one.

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-09-26 | 2 | 0 | 1 | 1 | 0 | mame-curator-1109 amendment (gated span: cf58686). Two lanes, each holding every question; both lanes found both defects independently. 2 findings, 2 verified / 0 dismissed, both fixed. [Q2] the resolver's absent-name warning read as firing on every popped name; now winners only, and the FP05-B1 test's `missingY in bios` assertion is named as inverting. [Q3] `api/routes/games.py` used chain membership as its "needs a BIOS" signal, which the every-machine rule makes true for all games; the spec now names the predicate (non-empty `resolve_bios_dependencies([short], …)`) and that consumer. Lane B tagged the second Q1; re-tagged Q3. Loop 2 dispatched. |
