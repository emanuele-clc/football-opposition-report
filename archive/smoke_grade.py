"""ARCHIVE (run before the protocols, 19 and 28 Oct 2026): smoke tests of the evidence grade. They only check that the code runs:
2 teams x 8 matches, they print counts of forecast rows, never a value, a skill or a grade.
    python archive/smoke_grade.py statsbomb <data_dir> <work_dir>     (Leicester City and Arsenal)
    python archive/smoke_grade.py wyscout   <wy_dir> <work_dir>       (Barcelona and Napoli, put in one 'league' so the baseline exists)
Moved here from evidence_grade.py and evidence_grade_wyscout.py on 6 Nov 2026 (same code)."""

import os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "analysis"))
ARGV = sys.argv
import evidence_grade as E

if len(ARGV) != 4 or ARGV[1] not in ("statsbomb", "wyscout"):
    sys.exit(__doc__)
data, work = ARGV[2], os.path.join(ARGV[3], "smoke")

if ARGV[1] == "statsbomb":
    T = [t for t in E.all_teams(data) if t["team"] in ("Leicester City", "Arsenal")]
    E.extract(data, work, T, max_matches=8)
    TEAMS = E.load_teams(work)
else:
    import evidence_grade_wyscout as W  # also keeps only the statements Wyscout supports

    T = []
    for t in W.all_teams(data):
        if t["team"] in W.DEV:
            T.append(dict(t, league="smoke"))
    W.extract(work, T, max_matches=8)
    TEAMS = W.load_teams(work)

fr = E.all_forecasts(TEAMS, list(TEAMS))
print("forecast rows per statement:", dict(fr.groupby("claim").size()))
print("statements without forecast rows:", sorted(set(E.CLAIMS) - set(fr.claim)))
for c in E.SCALAR + list(E.LEAD):
    E.discrimination(TEAMS, list(TEAMS), c, np.random.default_rng(7))
print(f"smoke test passed: {len(E.CLAIMS)} statements (no values printed)")
