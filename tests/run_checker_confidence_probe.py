"""Control pair for tools/checker_confidence.py, and the corrector's own proof.

Run: python tests/run_checker_confidence_probe.py

The instruction that produced this tool asked for a sanity check on the
CORRECTOR, so that a bad fusion cannot make things worse than no fusion at all.
That is arms 1 and 2, and arm 2 is the half that matters: it replaces the fusion
rule with an AVERAGE -- the obvious alternative, and the one that recreates the
exact defect this exists to catch -- and asserts the self-check goes RED.

Without that mutation, "the self-check passes" is a statement about `min` being
`min`, which nobody doubted.

OFFLINE.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import checker_confidence as C                                  # noqa: E402
import flaky_checker_quarantine as FLAKY                        # noqa: E402

CONTROLS_FOR = ['checker_confidence.py']

FAILED = []


def check(label, got, want):
    ok = got == want
    print('  %s %s' % ('ok  ' if ok else 'FAIL', label))
    if not ok:
        print('       expected %r, got %r' % (want, got))
        FAILED.append(label)


def main():
    print('checker confidence control pair\n')

    # ── 1. THE CORRECTOR IS SAFE ─────────────────────────────────────────────
    print('1. the fusion cannot rate a checker above either input')
    check('the exhaustive self-check passes', C.self_check(), [])
    check('a perfect flip rate with NO control is LOW, not MEDIUM',
          C.fuse(C.HIGH, C.LOW), C.LOW)
    check('...which is the checkblocks.py case: stable and useless',
          C.NAME[C.fuse(C.HIGH, C.LOW)], 'LOW')
    check('any UNKNOWN caps the result at UNKNOWN',
          C.fuse(C.HIGH, C.UNKNOWN), C.UNKNOWN)
    check('two HIGHs are HIGH -- the rule is not simply always-low',
          C.fuse(C.HIGH, C.HIGH), C.HIGH)

    # ── 2. THE MUTATION, and this is the arm that earns the rest ─────────────
    print('\n2. MUTATION -- an AVERAGE instead of a minimum must FAIL the check')
    real = C.fuse
    try:
        C.fuse = lambda a, b: int(round((a + b) / 2.0))
        bad = C.self_check()
        check('an averaging corrector is REJECTED', bool(bad), True)
        check('...and the reason names the exceeded input',
              any('EXCEEDS an input' in x for x in bad), True)
        check('...and specifically that HIGH+LOW averages to MEDIUM',
              C.NAME[C.fuse(C.HIGH, C.LOW)], 'MEDIUM')
        # And the tool REFUSES TO REPORT under a broken corrector rather than
        # publishing numbers derived from it.
        r = subprocess.run([sys.executable, '-c',
                            'import sys;sys.path.insert(0,r"%s");'
                            'import checker_confidence as C;'
                            'C.fuse=lambda a,b:int(round((a+b)/2.0));'
                            'sys.exit(C.main([]))' % os.path.join(REPO, 'tools')],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
        check('a broken corrector makes the tool exit 2, not report', r.returncode, 2)
        check('...and it says nothing was fused',
              'nothing was fused' in (r.stdout or ''), True)
    finally:
        C.fuse = real
    check('CONTROL: the real corrector is restored and passes', C.self_check(), [])

    # ── 3. THE BANDS COME FROM THE LEDGER'S OWN CLASSIFIER ───────────────────
    print('\n3. stability is the ledger\'s verdict, not a second copy of its bars')
    check('no entry at all is UNKNOWN',
          C.stability_band(None)[0], C.UNKNOWN)
    few = {'observations': [{'digest': 'a', 'tree': 't'}] * (FLAKY.MIN_RUNS_TO_JUDGE - 1)}
    check('below the ledger\'s own MIN_RUNS_TO_JUDGE is UNKNOWN, not HIGH',
          C.stability_band(few)[0], C.UNKNOWN)
    stable = {'observations': [{'digest': 'a', 'tree': 't'}] * 8}
    check('eight identical verdicts is HIGH', C.stability_band(stable)[0], C.HIGH)
    flaky = {'observations': [{'digest': 'a', 'tree': 't'}] * 6
                             + [{'digest': 'b', 'tree': 't'}] * 2}
    check('a verdict that has moved is not HIGH',
          C.stability_band(flaky)[0] < C.HIGH, True)
    check('an explicitly QUARANTINED checker is LOW whatever its rate',
          C.stability_band(stable, True)[0], C.LOW)

    # ── 4. THE EVIDENCE BANDS ────────────────────────────────────────────────
    print('\n4. one direction of a control is not two')
    check('BOTH directions evidenced is HIGH', C.evidence_band('BOTH')[0], C.HIGH)
    check('ONE direction is LOW -- a checker that always fires passes that half',
          C.evidence_band('ONE')[0], C.LOW)
    check('no control at all is LOW', C.evidence_band('NONE')[0], C.LOW)
    check('a declared control that will not parse is UNKNOWN, not LOW',
          C.evidence_band('UNPARSED')[0], C.UNKNOWN)
    check('EXEMPT is MEDIUM -- exempt is not proven', C.evidence_band('EXEMPT')[0], C.MEDIUM)

    # ── 5. THE REAL RUN ──────────────────────────────────────────────────────
    print('\n5. the real fleet')
    r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'checker_confidence.py'),
                        '--json'], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    doc = json.loads(r.stdout)
    rows = doc['rows']
    check('every promoted checker is scored', len(rows) > 20, True)
    check('no row is rated above either of its inputs',
          [x['tool'] for x in rows
           if {'UNKNOWN': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}[x['confidence']]
           > min({'UNKNOWN': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}[x['stability']],
                 {'UNKNOWN': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}[x['evidence']])],
          [])
    unknown = [x for x in rows if x['confidence'] == 'UNKNOWN']
    check('unmeasured checkers are UNKNOWN, not silently fine',
          all(x['stability'] == 'UNKNOWN' or x['evidence'] == 'UNKNOWN'
              for x in unknown), True)
    check('...and an UNKNOWN makes the run exit 2 rather than clean',
          r.returncode, 2 if unknown else r.returncode)

    out = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'checker_confidence.py')],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', cwd=REPO,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                  PYTHONUTF8='1')).stdout
    check('the report states the fusion is a minimum, not an average',
          'MINIMUM, NOT AN AVERAGE' in out, True)
    check('...and names checkblocks.py as why',
          'checkblocks.py' in out, True)
    # A NEAR-TAUTOLOGY REMOVED. This asserted `'not' in out.lower()`, which is
    # true of almost any English text and proved nothing -- the same class of
    # green tick as an always-true ok(). Pinned to the actual sentence instead.
    check('...and says one weak signal caps the result',
          'One weak signal caps the result' in out, True)

    print('')
    if FAILED:
        print('FAILED  confidence probe: %d failed' % len(FAILED))
        for f in FAILED:
            print('  - %s' % f)
        return 1
    print('ALL CHECKER CONFIDENCE PROBE ASSERTIONS PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
