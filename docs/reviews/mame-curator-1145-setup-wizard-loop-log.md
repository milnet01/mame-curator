# mame-curator-1145 setup wizard — loop log

## Cold-eyes loop log

| Loop | Date | Trigger | Lanes | Q1 | Q2 | Q3 | Q4 | Outcome |
|------|------|---------|-------|----|----|----|----|---------|
| 1 | 2026-10-30 | New spec, gate before build | 2 neutral lanes, each holding every question | 1 | 4 | 1 | 2 | 8 findings, 7 verified / 1 dismissed. All 7 fixed; loop 2 dispatched. Both lanes raised the re-choice focus, the blamed file, the restart after a bad listxml and the Settings refetch; one raised `large`'s coverage. Packet build found the INV-4 test setup (a PATCH rewrites the file from the world, so a hand-written listxml is lost) and a false "leaves the config as it was" (the picker's grant writes the config): the first fixed, the second dismissed as changing nothing built and corrected by deletion. Settling an open question found INV-13's bat test could not run off Windows. Check-doc-facts found one heading number, fixed outside the tally. Two open questions resolved clean. |
