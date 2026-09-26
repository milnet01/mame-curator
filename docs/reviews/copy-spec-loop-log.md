# Cold-eyes loop log — `src/mame_curator/copy/spec.md`

Review history for the copy module spec, kept outside the spec because the
spec has never carried a loop log and its standard does not require one.

## Cold-eyes loop log

| Loop | Date | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|-------|----|----|----|----|---------|
| 1 | 2026-09-26 | 2 | 0 | 1 | 1 | 0 | mame-curator-1109 amendment (gated span: cf58686). Two lanes, each holding every question; both lanes found both defects independently. 2 findings, 2 verified / 0 dismissed, both fixed. [Q2] the resolver's absent-name warning read as firing on every popped name; now winners only, and the FP05-B1 test's `missingY in bios` assertion is named as inverting. [Q3] `api/routes/games.py` used chain membership as its "needs a BIOS" signal, which the every-machine rule makes true for all games; the spec now names the predicate (non-empty `resolve_bios_dependencies([short], …)`) and that consumer. Lane B tagged the second Q1; re-tagged Q3. Loop 2 dispatched. |
| 2 | 2026-09-26 | 2 | 0 | 0 | 1 | 0 | Two lanes, each holding every question. Lane B read the packet only in part (reported 506 of its 820 lines, missing the `games.py` windows); its subject read was complete. 1 finding, 1 verified / 0 dismissed, fixed: [Q3] the loop-1 sentence said the `only_bios_missing` filter "uses that predicate" without its polarity, while the live filter keeps the games NOT in the chain; the spec now says the filter keeps exactly the badged games. Two open questions resolved clean by lookup: the test fixture already carries `isbios="yes"`, and the configured source set is non-merged (`MAME 0.284 ROMs (non-merged)`). **Capped (spec cap 2).** Final-loop share on this run's own text: 1 of 1, but an unpropagated consequence of the pre-existing inverted filter rather than a repair of a repair, so calm; ship. Share inside the gated span (cf58686): 3 of 3 verified findings. |
