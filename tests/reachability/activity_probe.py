"""Control pair for R4 (--activity) in tools/sairn_reachability_check.py.

Run: python tests/reachability/activity_probe.py

R4 asks whether a route still serves a purpose in the RUNNING system, using
days-since-last-observed-invocation against a declared cadence. Two things about
it need proving in both directions, and neither is provable by running it once
on the real snapshot:

  THE DENOMINATOR GATE FIRES when the snapshot saw too few routes to
  discriminate -- which is the real tree's state today, so a single real run
  only ever exercises that half.

  THE DENOMINATOR GATE LIFTS when coverage is adequate. WITHOUT THIS ARM THE
  GATE COULD BE PERMANENTLY STUCK AND NOBODY WOULD KNOW: a check that always
  says UNKNOWN looks exactly like a platform that is always unmeasurable, which
  is the `checkblocks.py`-always-exits-0 shape one layer up.

And the property the whole design rests on:

  R4 NEVER CHANGES THE EXIT CODE. It is report-only by construction, not by
  convention, because a silence over a 72-hour window on a platform with almost
  no customers is not permission to delete a disaster-recovery path.

OFFLINE. Synthetic snapshots in memory, one subprocess run of the real tool.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import sairn_reachability_check as R                           # noqa: E402

CONTROLS_FOR = ['sairn_reachability_check.py']

FAILED = []


def check(label, got, want):
    ok = got == want
    print('  %s %s' % ('ok  ' if ok else 'FAIL', label))
    if not ok:
        print('       expected %r, got %r' % (want, got))
        FAILED.append(label)
    return ok


def capture(snapshot):
    """Run report_activity and return what it printed."""
    buf = io.StringIO()
    real = sys.stdout
    sys.stdout = buf
    try:
        R.report_activity(snapshot)
    finally:
        sys.stdout = real
    return buf.getvalue()


def main():
    print('R4 activity control pair\n')
    routes = R.routed_api_paths()
    crons = R.declared_crons()

    # ── 0. THE INPUTS ARE DERIVED, NOT WRITTEN DOWN ──────────────────────────
    print('0. derived inputs')
    check('routed api/ paths come from the tree and are non-empty',
          len(routes) > 0, True)
    check('...and exclude _lib/ and _resources/, which are imported not routed',
          any(p.startswith('/api/_lib') or p.startswith('/api/_resources')
              for p in routes), False)
    check('...and exclude *.test.js',
          any(p.endswith('.test') for p in routes), False)
    with io.open(os.path.join(REPO, 'vercel.json'), encoding='utf-8') as fh:
        want_crons = {c['path'] for c in (json.load(fh).get('crons') or [])}
    check('cron paths are read out of vercel.json, not listed in the tool',
          crons, want_crons)

    # ── 1. THE GATE FIRES on a thin snapshot ─────────────────────────────────
    print('\n1. FIRES -- an under-covered snapshot classifies NOTHING')
    thin = {'captured_at': '2026-01-01', 'window_hours': 72, 'source': 'fixture',
            'counts': {routes[0]: 5}}
    out_thin = capture(thin)
    check('says UNKNOWN', 'VERDICT: UNKNOWN' in out_thin, True)
    check('and says nothing is classified',
          'NOTHING IS CLASSIFIED' in out_thin, True)
    check('and refuses to call anything dead',
          'No route is called dead here' in out_thin, True)
    check('so no per-route SERVED/SILENT tally is printed at all',
          'SILENT, NO CADENCE ROW' in out_thin, False)

    # ── 2. THE GATE LIFTS on a broad one ─────────────────────────────────────
    print('\n2. SILENT (gate lifts) -- adequate coverage DOES classify')
    n = int(len(routes) * 0.8) + 1
    broad = {'captured_at': '2026-01-01', 'window_hours': 72, 'source': 'fixture',
             'counts': {p: 3 for p in routes[:n]}}
    out_broad = capture(broad)
    check('no longer says UNKNOWN', 'VERDICT: UNKNOWN' in out_broad, False)
    check('now prints a per-route tally',
          'SILENT, NO CADENCE ROW' in out_broad, True)
    check('and the SERVED count is what was planted',
          ('SERVED                    : %d' % n) in out_broad, True)

    # ── 3. A DECLARED CADENCE EXPLAINS A SILENCE ─────────────────────────────
    print('\n3. rare-but-real is a DECLARED class, never inferred')
    cron_path = sorted(want_crons)[0]
    # Cover enough routes to lift the gate, but leave the cron SILENT.
    covered = [p for p in routes if p != cron_path][:n]
    with_cadence = {'captured_at': '2026-01-01', 'window_hours': 72,
                    'source': 'fixture',
                    'counts': {p: 3 for p in covered}}
    out_c = capture(with_cadence)
    check('the silent cron is listed as cadence-declared, not as a question',
          ('-- %-44s' % cron_path) in out_c, True)
    check('...and it is NOT in the no-cadence bucket',
          ('?  %-44s no cadence declared' % cron_path) in out_c, False)
    check('a silent route with no row IS in the no-cadence bucket',
          'no cadence declared' in out_c, True)
    check('and the advice is to write a row, never to delete code',
          'NOT delete the' in out_c and 'never votes for removal' in out_c, True)

    # ── 4. A BROKEN SNAPSHOT FAILS CLOSED ────────────────────────────────────
    print('\n4. an unreadable snapshot is a could-not-tell, not an empty one')
    tmp = tempfile.mkdtemp(prefix='activity_probe_')
    bad = os.path.join(tmp, 'broken.json')
    io.open(bad, 'w', encoding='utf-8').write('{ this is not json')
    snap, err = R.load_activity(bad)
    check('load_activity reports the error', bool(err), True)
    check('...and returns no snapshot', snap, None)
    incomplete = os.path.join(tmp, 'incomplete.json')
    io.open(incomplete, 'w', encoding='utf-8').write('{"counts": {}}')
    _s, err2 = R.load_activity(incomplete)
    check('a snapshot with no captured_at is refused, not read as empty',
          'captured_at' in (err2 or ''), True)

    # ── 5. R4 CANNOT CHANGE THE EXIT CODE ────────────────────────────────────
    print('\n5. report-only by construction')

    def run(extra):
        p = subprocess.run(
            [sys.executable, os.path.join(REPO, 'tools',
                                          'sairn_reachability_check.py')]
            + extra + ['sairnvet.html'],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            cwd=REPO, env=dict(os.environ, PYTHONIOENCODING='utf-8',
                               PYTHONUTF8='1'))
        return p.returncode, (p.stdout or '')

    rc_without, out_without = run([])
    rc_with, out_with = run(['--activity'])
    check('the exit code is identical with and without --activity',
          rc_with, rc_without)
    check('...and the R4 section really did run in the second one',
          'R4: STILL SERVED IN PRODUCTION?' in out_with, True)
    check('...and really did not in the first',
          'R4: STILL SERVED IN PRODUCTION?' in out_without, False)
    check('--activity did not consume the html target as a snapshot path',
          'unreadable' in out_with, False)

    # ── 6. THE COMMITTED SNAPSHOT IS THE STATE IT CLAIMS ─────────────────────
    print('\n6. the committed snapshot parses and is under the bar today')
    real, err3 = R.load_activity(R.ACTIVITY_FILE)
    check('tools/production_activity_snapshot.json parses', err3, None)
    out_real = capture(real)
    check('and today it is UNKNOWN -- 13 of 64 routes observed',
          'VERDICT: UNKNOWN' in out_real, True)

    print('')
    if FAILED:
        print('FAILED  activity probe: %d failed' % len(FAILED))
        for f in FAILED:
            print('  - %s' % f)
        return 1
    print('ALL R4 ACTIVITY PROBE ASSERTIONS PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
