"""Control pair for tools/benford_check.py, and the shape pre-check is most of it.

Run: python tests/run_benford_probe.py

A Benford check is the easiest kind of tool to make useless in either
direction. Set the bars loose and it flags everything, which is the same as
flagging nothing. Set them tight and it never fires, which looks exactly like a
clean set of books. So both directions are required, and the arms that matter
most are the REFUSALS: applying the law to data that cannot satisfy it produces
a confident false positive every single time.

OFFLINE. Every arm runs on generated fixtures or calls a function directly.
Nothing reads the network and nothing writes to the repo.
"""
import io
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import benford_check as B                                      # noqa: E402
import checker_kit as K                                        # noqa: E402

CONTROLS_FOR = ['benford_check.py']

FAILED = []


def check(label, got, want):
    ok = got == want
    print('  %s %s' % ('ok  ' if ok else 'FAIL', label))
    if not ok:
        print('       expected %r, got %r' % (want, got))
        FAILED.append(label)


def main():
    print('benford_check control pair\n')

    # ── 1. FIRES ─────────────────────────────────────────────────────────────
    print('1. FIRES -- data with evenly-spread leading digits is flagged')
    typed = B.report_corpus('t', B._typed_sample(), 'fixture')
    check('the typed sample is not refused by the shape pre-check',
          typed.get('skipped'), None)
    check('...and it IS flagged', typed.get('flagged'), True)
    check('...as NONCONFORMITY on the first digit',
          typed['first']['band'], 'NONCONFORMITY')
    check('a flagged corpus exits 1, not 0',
          K.finish(['x'], [], quiet=True), K.EXIT_FINDING)

    # ── 2. SILENT ────────────────────────────────────────────────────────────
    print('\n2. SILENT -- Benford-by-construction data is not flagged')
    good = B.report_corpus('g', B._benford_sample(), 'fixture')
    check('the Benford sample is not refused', good.get('skipped'), None)
    check('...and is NOT flagged', good.get('flagged'), False)
    check('...and lands in close conformity', good['first']['band'], 'close conformity')
    # CONTROL ON THE CONTROL: if the expected table were wrong, both arms above
    # could still pass on a table that is merely self-consistent.
    check('the expected first-digit table is the law, not a copied constant',
          round(B.FIRST_EXPECTED[1], 4), round(math.log10(2.0), 4))
    check('...and it sums to 1', round(sum(B.FIRST_EXPECTED.values()), 6), 1.0)
    check('the second-digit table sums to 1',
          round(sum(B.SECOND_EXPECTED.values()), 6), 1.0)

    # ── 3. THE REFUSALS, one arm each ────────────────────────────────────────
    print('\n3. the shape pre-check refuses what cannot satisfy the law')
    small = B.report_corpus('s', [10 ** (3.0 * i / 50) for i in range(50)], 'f')
    check('TOO FEW VALUES', small.get('skipped'), 'TOO FEW VALUES')

    narrow = B.report_corpus('n', [10.0 + (i % 90) for i in range(400)], 'f')
    check('TOO NARROW A SPREAD', narrow.get('skipped'), 'TOO NARROW A SPREAD')

    rounded = B.report_corpus('r', [100.0 * (i % 500 + 1) for i in range(400)], 'f')
    check('TOO ROUNDED', rounded.get('skipped'), 'TOO ROUNDED')

    fewvals = B.report_corpus('d', [199.0, 2999.0, 49999.0] * 200, 'f')
    check('TOO FEW DISTINCT VALUES', fewvals.get('skipped'), 'TOO FEW DISTINCT VALUES')

    # CAPPED sits in the GAP BETWEEN the two guards either side of it, so this
    # fixture is built to clear both of them and be catchable only by the mode
    # guard: a copay pinned at 50 for 60% of rows, with the other 40% spread
    # over three decades. Distinct share lands at 0.40 (over MIN_DISTINCT_SHARE
    # of 0.30) and 50 is not a multiple of 100 (under MAX_ROUND_SHARE).
    capped = [50.0] * 600 + [10.0 + 7.3 * i for i in range(400)]
    capped_row = B.report_corpus('c', capped, 'f')
    check('CAPPED OR DEFAULTED', capped_row.get('skipped'), 'CAPPED OR DEFAULTED')
    # CONTROL ON THAT FIXTURE: if it were being caught by one of its neighbours
    # the arm above would pass while the new guard did nothing.
    _pos = [v for v in capped if v > 0]
    check('...and the capped fixture CLEARS the distinct-share bar, so the '
          'refusal is the mode guard and not its neighbour',
          len(set(_pos)) / float(len(_pos)) > B.MIN_DISTINCT_SHARE, True)
    check('...and CLEARS the round-share bar too',
          sum(1 for v in _pos if v == int(v) and int(v) % 100 == 0)
          / float(len(_pos)) <= B.MAX_ROUND_SHARE, True)
    check('...and the reason names the value and its share, not a bare label',
          '50' in capped_row['why'] and '60%' in capped_row['why'], True)
    # THE OTHER DIRECTION: a spread column with no pile-up must NOT be refused,
    # or the guard is just refusing everything.
    spread = B.report_corpus('cs', [10.0 + 7.3 * i for i in range(1000)], 'f')
    check('a column with NO pile-up is not refused as CAPPED',
          spread.get('skipped') != 'CAPPED OR DEFAULTED', True)
    # ORDER, ASSERTED RATHER THAN ASSUMED: three values repeated trips the mode
    # guard too (33% > 25%), and the more informative answer is the distinct
    # one. Without this arm the ordering could be reversed and only the wording
    # of an unrelated arm would change.
    check('a three-value column is reported as TOO FEW DISTINCT, not CAPPED -- '
          'the more informative of the two reasons wins',
          fewvals.get('skipped'), 'TOO FEW DISTINCT VALUES')

    # ── 4. THE REFUSALS DO NOT SWALLOW GOOD DATA ─────────────────────────────
    # Without this the pre-check could be refusing everything and arms 1-3 would
    # all still pass. It is the same argument the metamorphic harness makes for
    # its identity relation.
    print('\n4. CONTROL -- the refusals do not swallow data that IS testable')
    check('the Benford fixture survives every refusal', good.get('skipped'), None)
    check('...and so does the typed one', typed.get('skipped'), None)
    check('a refused corpus carries its measured reason, not a bare label',
          bool(str(small.get('why') or '').strip()), True)
    check('...and names the bar it missed', str(B.MIN_N) in small['why'], True)

    # ── 5. THE BLIND LOCK REFUSES A BROKEN BAR ───────────────────────────────
    print('\n5. an unusable bar FAILS the lock and refuses the real run')
    ok_now, _rows, problems = B.blind_lock()
    check('the shipped bars lock clean', (ok_now, problems), (True, []))
    real_min = B.MIN_N
    try:
        B.MIN_N = 100000          # nothing can ever be tested
        ok2, _r2, p2 = B.blind_lock()
        check('with an impossible MIN_N the lock FAILS', ok2, False)
        check('...and says the fixture was refused, not that the fleet is clean',
              any('shape pre-check' in x for x in p2), True)
    finally:
        B.MIN_N = real_min
    real_mad = B.FIRST_MAD
    try:
        B.FIRST_MAD = ((float('inf'), 'close conformity'),)   # nothing ever fires
        ok3, _r3, p3 = B.blind_lock()
        check('with a bar that can never fire the lock FAILS', ok3, False)
        check('...and says the test cannot fire',
              any('cannot fire' in x for x in p3), True)
    finally:
        B.FIRST_MAD = real_mad

    # ── 6. THE PRODUCTION QUESTION IS COULD-NOT-RUN, NOT CLEAN ───────────────
    print('\n6. PR 1.11 -- no export means the real tables were not examined')
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'benford_check.py'),
                        '--json'], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    doc = json.loads(p.stdout)
    check('a run with no --data reports could-not-run',
          bool(doc['could_not_run']), True)
    check('...and the exit code is 2, not 0 and not 1', p.returncode, 2)
    check('...and it names the tables it did NOT look at',
          'ledger_entries' in doc['could_not_run'][0], True)
    check('...and says the repo corpora say nothing about production',
          'say nothing about production' in doc['could_not_run'][0], True)

    # ── 7. AN EXPORT IS READ, AND A BROKEN ONE FAILS CLOSED ──────────────────
    print('\n7. --data reads a real export, and refuses a broken one')
    tmp = tempfile.mkdtemp(prefix='benford_probe_')
    good_path = os.path.join(tmp, 'amounts.json')
    io.open(good_path, 'w', encoding='utf-8').write(
        json.dumps([{'amount': v} for v in B._benford_sample()]))
    name, vals, err = B.load_data(good_path)
    check('an array of objects with an amount field is read', err, None)
    check('...and every value came through', len(vals), 600)
    bad_path = os.path.join(tmp, 'broken.json')
    io.open(bad_path, 'w', encoding='utf-8').write('{ not json')
    _n2, _v2, err2 = B.load_data(bad_path)
    check('an unreadable export is an ERROR, not an empty dataset',
          bool(err2), True)
    empty_path = os.path.join(tmp, 'empty.json')
    io.open(empty_path, 'w', encoding='utf-8').write('[{"name":"x"}]')
    _n3, _v3, err3 = B.load_data(empty_path)
    check('an export with no numeric field is refused rather than read as zero rows',
          bool(err3), True)

    # ── 8. IT NEVER CLAIMS MORE THAN A POINTER ───────────────────────────────
    print('\n8. the wording is a pointer, never a verdict')
    out = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'benford_check.py')],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', cwd=REPO,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                  PYTHONUTF8='1')).stdout
    check('it says LOOK HERE', 'LOOK HERE' in out, True)
    check('it never says fabricated', 'fabricated' in out.lower(), False)
    check('it says a conforming distribution is not evidence of honesty, or '
          'flags something',
          ('not evidence of honesty' in out) or ('LOOK HERE' in out), True)
    check('and it states that seed corpora are expected to fail',
          'SEED CORPORA ARE OPENLY INVENTED' in out, True)

    print('')
    if FAILED:
        print('FAILED  benford probe: %d failed' % len(FAILED))
        for f in FAILED:
            print('  - %s' % f)
        return 1
    print('ALL BENFORD PROBE ASSERTIONS PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
