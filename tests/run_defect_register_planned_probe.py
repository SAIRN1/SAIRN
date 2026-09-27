"""tests/run_defect_register_planned_probe.py

Run:  python tests/run_defect_register_planned_probe.py

THE CONTROL FOR `defect_register.py --planned`, DRIVEN ON SYNTHETIC FIXTURES.

`--planned` exists because 62 planned actions sat in docs/defect-density-register.json
and nothing read them back. A surface built for that reason has to be right about
the two things it claims, and both are easy to get wrong in a way that still
prints a confident number:

  (1) TWO COUNTS, NOT ONE. A record can carry more than one planned factor, so
      "62 planned actions" and "58 records with one" are different facts. Collapsing
      them either overstates the backlog or understates how many defects it touches.
      Arm A1 uses a fixture where the two numbers DIFFER, so a build that reports
      one figure twice cannot pass.

  (2) REGISTER-ONLY vs TRACKED. The claim is that a planned action whose fix
      commit is named nowhere in the open-work index is reachable from one file
      only. A false "tracked" hides a backlog item; a false "register-only"
      manufactures one. Arms B1-B4 drive both directions including the
      short-sha/long-sha asymmetry.

FIXTURES, NOT THE REAL REGISTER, AND THAT IS THE POINT. Pointing this at the live
file would make every arm depend on today's record set: it would go green for the
wrong reason the day somebody adds a record, and red for the wrong reason the day
somebody edits the index. `planned_facts()` takes `now` and `idx` injectably for
exactly this reason. Arm E1 is the one arm that touches real data, and it asserts
only that the real call runs and agrees with itself.

Exit 0 clean / 1 findings / 2 could not run.
"""
import io
import os
import sys

# DR_MODULE_DIR points this at a MUTATED COPY of the tool, the same convention
# SD_HTML, MECH_HTML and DNT_HTML already carry. Without it a negative control
# has to edit the tracked file and remember to put it back, which is the shape
# that leaves a mutated tool on disk when something interrupts.
sys.path.insert(0, os.environ.get('DR_MODULE_DIR')
                or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import defect_register as dr
except Exception as e:                                          # noqa: BLE001
    print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
    raise SystemExit(2)

PASS = [0]
FAIL = [0]


def check(name, cond, detail=''):
    if cond:
        print('  ok   %s' % name)
        PASS[0] += 1
    else:
        print('  FAIL %s%s' % (name, ('\n       ' + detail) if detail else ''))
        FAIL[0] += 1


def rec(commit, date, app, statuses):
    """A record with one contributing factor per status given."""
    return {
        'commit': commit, 'date': date, 'app': app, 'layer': 'product',
        'severity': 'high', 'detection_method': 'code-review',
        'subject': 'fixture ' + commit,
        'contributing_factors': [
            {'factor': 'f%d' % i, 'kind': 'detection', 'action_status': s,
             'action': 'do the thing %d for %s' % (i, commit)}
            for i, s in enumerate(statuses)
        ],
    }


NOW = '2026-10-01'

print('defect_register --planned -- control')

# ── A. THE TWO COUNTS ─────────────────────────────────────────────────────
print('\nA. planned FACTORS and planned RECORDS are different numbers')
# 3 records; one carries TWO planned factors and one carries none.
FIX_A = [
    rec('aaaaaaaaaaaa', '2026-09-20', 'stonedesk', ['planned', 'planned', 'done']),
    rec('bbbbbbbbbbbb', '2026-09-25', 'sairnbiz', ['done']),
    rec('cccccccccccc', '2026-09-28', 'sairnvet', ['planned']),
]
rows_a, vis_a = dr.planned_facts(FIX_A, now=NOW, idx='')
check('A1. three planned factors across two records, and they are not the same count',
      len(rows_a) == 3 and len({id(r) for _, r, _ in rows_a}) == 2,
      'got %d factor(s) across %d record(s), expected 3 across 2'
      % (len(rows_a), len({id(r) for _, r, _ in rows_a})))
check('A2. a `done` factor is never counted as planned',
      all(f.get('action_status') == 'planned' for _, _, f in rows_a),
      'a non-planned factor leaked in: %r'
      % [f.get('action_status') for _, _, f in rows_a])

# ── B. REGISTER-ONLY vs TRACKED ──────────────────────────────────────────
print('\nB. the index cross-reference, both directions')
IDX = 'a row mentioning aaaaaaa and another mentioning cccccccccccc\n'
rows_b, vis_b = dr.planned_facts(FIX_A, now=NOW, idx=IDX)
by = {str(r['commit']): vis_b(r) for _, r, _ in rows_b}
check('B1. a 7-char prefix in the index counts as TRACKED',
      by.get('aaaaaaaaaaaa') is True,
      'a record whose 7-char sha prefix appears in the index was reported '
      'register-only, which manufactures a backlog item')
check('B2. a 12-char sha in the index counts as TRACKED',
      by.get('cccccccccccc') is True)
check('B3. a sha absent from the index is REGISTER-ONLY',
      dr.planned_facts([rec('dddddddddddd', '2026-09-20', 'x', ['planned'])],
                       now=NOW, idx=IDX)[1](
          rec('dddddddddddd', '2026-09-20', 'x', ['planned'])) is False)
check('B4. AN EMPTY INDEX MAKES EVERYTHING REGISTER-ONLY, not everything tracked',
      all(vis_a(r) is False for _, r, _ in rows_a),
      'with no index text a record was reported TRACKED -- a missing index must '
      'never read as coverage, which is the fail-open direction here')

# ── C. AGEING AND ORDER ──────────────────────────────────────────────────
print('\nC. oldest first, and a missing date does not vanish')
ages = [a for a, _, _ in rows_a]
check('C1. oldest first', ages == sorted(ages, reverse=True),
      'order is %r' % (ages,))
check('C2. the ages are real day counts against the injected `now`',
      ages[0] == 11 and ages[-1] == 3,
      'got %r, expected first 11 (2026-09-20) and last 3 (2026-09-28)' % (ages,))
rows_c, _ = dr.planned_facts(
    [rec('eeeeeeeeeeee', '', 'x', ['planned'])], now=NOW, idx='')
check('C3. a record with an UNUSABLE date is still listed, aged -1 rather than dropped',
      len(rows_c) == 1 and rows_c[0][0] == -1,
      'a planned action with a bad date was silently dropped -- which would make '
      'the backlog smaller than it is, the one direction that must not happen')

# ── D. THE EMPTY CASE SAYS WHAT IT DOES NOT KNOW ─────────────────────────
print('\nD. an empty list is not reported as an all-clear')
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    dr.planned_block([rec('ffffffffffff', '2026-09-20', 'x', ['done'])],
                     full=True, now=NOW, idx='')
empty_out = buf.getvalue()
check('D1. it says an empty list is indistinguishable from nobody using the status',
      'not evidence' in empty_out and 'nobody uses' in empty_out,
      'the empty-case text does not disclaim what it cannot know:\n' + empty_out)

# ── E. AND THE SAME CODE RUNS ON REAL DATA ───────────────────────────────
print('\nE. the real call runs and agrees with itself')
try:
    real = dr.load().get('records', [])
    r1, v1 = dr.planned_facts(real)
    r2, v2 = dr.planned_facts(real)
    check('E1. deterministic on the real register (same input, same answer)',
          [(a, str(r.get('commit')), f.get('action')) for a, r, f in r1]
          == [(a, str(r.get('commit')), f.get('action')) for a, r, f in r2],
          'two identical calls disagreed -- PR 1.9')
    check('E2. every real row really is `planned`',
          all(f.get('action_status') == 'planned' for _, _, f in r1))
    print('       (real register: %d planned factor(s) across %d record(s))'
          % (len(r1), len({id(r) for _, r, _ in r1})))
except Exception as e:                                          # noqa: BLE001
    check('E1. the real call runs', False, '%s: %s' % (type(e).__name__, e))

print('\n%s -- %d passed, %d failed' % ('FAIL' if FAIL[0] else 'ALL', PASS[0], FAIL[0]))
raise SystemExit(1 if FAIL[0] else 0)
