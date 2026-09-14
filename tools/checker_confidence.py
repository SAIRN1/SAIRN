"""How much is one checker's answer worth? Two signals, fused by CONJUNCTION.

    python tools/checker_confidence.py
    python tools/checker_confidence.py --json
    python tools/checker_confidence.py --self-check   # the corrector's own proof
    python tools/checker_confidence.py --quiet

Exit 0 clean, 1 when a promoted checker lands at LOW, 2 when part of the run did
not happen. REPORT ONLY.

── TWO SIGNALS THAT ARE STRONG IN OPPOSITE PLACES ──────────────────────────
STABILITY, from tools/flaky_checker_quarantine.py: does the checker give the
same verdict on UNCHANGED code, run after run? It is ALWAYS ON and cheap, so it
accumulates evidence continuously -- and it can DRIFT, because it only ever sees
whatever the tree happened to be, and it says nothing at all about whether the
verdict is correct. A checker that always exits 0 has a perfect flip rate.

PROVEN TO FIRE, from tools/checker_control_check.py: is there a control that
plants a defect and asserts the checker REPORTS it, and plants clean code and
asserts it STAYS SILENT? That is accurate -- it is the only thing that
distinguishes a working checker from `checkblocks.py`, which always exited 0 and
looked exactly like a clean codebase -- but it is INFREQUENT, because somebody
has to write the control.

Neither alone is worth much. `checkblocks.py` is the proof: perfectly stable and
completely useless, for months, and nothing noticed.

── THE FUSION IS A MINIMUM, NOT AN AVERAGE, AND THAT IS THE WHOLE DESIGN ───
    confidence = min(stability_band, evidence_band)

AN AVERAGE WOULD RECREATE THE DEFECT THIS EXISTS TO CATCH. A checker with a
perfect flip rate and no control would average out to MEDIUM, and MEDIUM is
exactly the rating `checkblocks.py` did not deserve. Under a minimum it cannot:
one weak input caps the result, always.

THE CORRECTOR CANNOT MAKE THINGS WORSE THAN NOT FUSING, and that is not a claim
about intent -- it is a property of `min` and it is PROVED EXHAUSTIVELY over
every possible pair of inputs by `--self-check`, which is 16 comparisons, not a
sample. If a future edit replaced the rule with something that can exceed either
input, that arm goes red before anything else runs.

── UNKNOWN IS A BAND, NOT A ZERO ───────────────────────────────────────────
A checker with no ledger entry has not been MEASURED; that is not the same as
being unstable, and it is not the same as being fine. It lands at UNKNOWN, which
caps the fused result at UNKNOWN, and the run reports how many. PR 1.11 applied
to a confidence score: could-not-tell is never folded into a pass.
"""
import argparse
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                # noqa: E402
import flaky_checker_quarantine as FLAKY                          # noqa: E402
import checker_control_check as CTRL                              # noqa: E402

UNKNOWN, LOW, MEDIUM, HIGH = 0, 1, 2, 3
NAME = {UNKNOWN: 'UNKNOWN', LOW: 'LOW', MEDIUM: 'MEDIUM', HIGH: 'HIGH'}


def fuse(stability, evidence):
    """The whole corrector. A CONJUNCTION: the weaker input caps the result.

    Proved exhaustively by --self-check rather than argued: for every pair,
    fuse(a, b) <= min(a, b) and fuse(a, b) == fuse(b, a).
    """
    return min(stability, evidence)


def stability_band(entry, quarantined=False):
    """(band, why) from a flip-ledger row.

    THE CLASSIFICATION IS THE LEDGER'S OWN, not a second copy of its thresholds.
    flaky_checker_quarantine.classify() already decides TOO-FEW-RUNS / WATCH /
    QUARANTINE / STABLE against criteria that were locked against fixtures
    before any checker was measured; re-deriving them here would be a second
    place for the bars to live and the two would drift.
    """
    if not entry:
        return UNKNOWN, 'never measured for flip rate'
    verdict, rate, runs = FLAKY.classify(entry)
    if quarantined:
        return LOW, 'QUARANTINED, flip rate %.3f over %d runs' % (rate, runs)
    if verdict == 'TOO-FEW-RUNS':
        # TOO FEW RUNS IS NOT STABILITY. The ledger says so itself; folding it
        # into HIGH would be the flattering read of an absence of evidence.
        return UNKNOWN, 'only %d run(s), below the %d needed to judge' % (
            runs, FLAKY.MIN_RUNS_TO_JUDGE)
    if verdict == 'QUARANTINE':
        return LOW, 'flip rate %.3f is over the quarantine bar' % rate
    if verdict == 'WATCH':
        return MEDIUM, 'flip rate %.3f -- it has disagreed with itself' % rate
    return HIGH, '%d runs, no verdict has ever moved' % runs


def evidence_band(state):
    """(band, why) from the control-pair state."""
    return {
        'BOTH': (HIGH, 'a control plants a defect AND plants clean code'),
        'ONE': (LOW, 'the control only evidences ONE direction -- a checker that '
                     'always fires passes that half on its own'),
        'NONE': (LOW, 'NO declared control: nothing has ever shown this checker '
                      'can fire'),
        'UNPARSED': (UNKNOWN, 'a control is declared but could not be parsed'),
        'EXEMPT': (MEDIUM, 'exempt from the control requirement, with a recorded '
                           'reason -- exempt is not proven'),
    }.get(state, (UNKNOWN, 'no control state'))


def control_states():
    """{tool: state} by reading checker_control_check's own machinery."""
    promoted = CTRL.promoted()
    declared = {}
    for path in CTRL.test_files():
        try:
            src = io.open(path, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for tool in CTRL.declared_controls(CTRL.strip(path, src)):
            declared.setdefault(tool, []).append((path, src))
    out = {}
    for tool in promoted:
        if tool in CTRL.EXEMPT:
            out[tool] = 'EXEMPT'
            continue
        files = declared.get(tool)
        if not files:
            out[tool] = 'NONE'
            continue
        fires = silent = False
        parsed = False
        for path, src in files:
            try:
                # evidence() returns a (fires, silent) TUPLE. Reading it as a
                # dict is what the first version did and it threw on the first
                # real run -- caught before anything was reported, which is the
                # only reason it is a footnote rather than a wrong number.
                f, sl = CTRL.evidence(path, src)
            except Exception:
                continue
            parsed = True
            fires = fires or bool(f)
            silent = silent or bool(sl)
        if not parsed:
            out[tool] = 'UNPARSED'
        elif fires and silent:
            out[tool] = 'BOTH'
        elif fires or silent:
            out[tool] = 'ONE'
        else:
            out[tool] = 'NONE'
    return out


def self_check():
    """Exhaustive proof of the corrector's own safety. 16 pairs, not a sample."""
    bad = []
    for a in (UNKNOWN, LOW, MEDIUM, HIGH):
        for b in (UNKNOWN, LOW, MEDIUM, HIGH):
            f = fuse(a, b)
            if f > a or f > b:
                bad.append('fuse(%s,%s)=%s EXCEEDS an input -- the fusion can '
                           'rate a checker higher than either signal supports'
                           % (NAME[a], NAME[b], NAME[f]))
            if f != fuse(b, a):
                bad.append('fuse is not symmetric at (%s,%s)' % (NAME[a], NAME[b]))
            if a == UNKNOWN or b == UNKNOWN:
                if f != UNKNOWN:
                    bad.append('an UNKNOWN input did not cap the result at '
                               'UNKNOWN: fuse(%s,%s)=%s'
                               % (NAME[a], NAME[b], NAME[f]))
    return bad


def collect():
    led = FLAKY.load_ledger()
    checkers = led.get('checkers') or {}
    quarantined = set(led.get('quarantine') or {})
    rows_by_tool = {}
    for t in FLAKY.registry_tools():
        rows_by_tool[t] = checkers.get(t)
    states = control_states()
    tools = sorted(set(list(rows_by_tool) + list(states)))
    out = []
    for t in tools:
        sb, swhy = stability_band(rows_by_tool.get(t), t in quarantined)
        eb, ewhy = evidence_band(states.get(t))
        out.append({'tool': t, 'stability': NAME[sb], 'stability_why': swhy,
                    'evidence': NAME[eb], 'evidence_why': ewhy,
                    'confidence': NAME[fuse(sb, eb)], '_band': fuse(sb, eb)})
    return out


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--self-check', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args(argv)

    # THE CORRECTOR IS CHECKED BEFORE IT IS USED. A fusion rule that can exceed
    # its inputs would make every number below worse than not fusing at all, and
    # there is no point reporting them if that is true.
    bad = self_check()
    if not args.quiet and not args.json:
        print('CHECKER CONFIDENCE -- report only')
        print('  corrector self-check: %s (16 pairs, exhaustive)'
              % ('SAFE' if not bad else 'UNSAFE'))
    if bad:
        if args.json:
            print(json.dumps({'self_check_failed': bad}, indent=1))
        elif not args.quiet:
            print('\nTHE FUSION RULE IS NOT SAFE, so nothing was fused.')
            for b in bad:
                print('  ? %s' % b)
        return EXIT_COULD_NOT_RUN
    if args.self_check:
        if not args.quiet:
            print('  fuse(a,b) <= min(a,b) for every pair, symmetric, and any '
                  'UNKNOWN caps the result at UNKNOWN.')
        return 0

    try:
        rows = collect()
    except Exception as e:                                   # noqa: BLE001
        print('could not collect: %s: %s' % (type(e).__name__, e))
        return EXIT_COULD_NOT_RUN

    unknown = [r for r in rows if r['confidence'] == 'UNKNOWN']
    low = [r for r in rows if r['confidence'] == 'LOW']

    if args.json:
        print(json.dumps({'rows': rows}, indent=1))
        return EXIT_COULD_NOT_RUN if unknown else (1 if low else 0)

    if not args.quiet:
        print('  checkers scored : %d' % len(rows))
        print('')
        print('  %-34s %-8s %-8s %s' % ('checker', 'STABLE', 'PROVEN', 'CONFIDENCE'))
        for r in sorted(rows, key=lambda x: (x['_band'], x['tool'])):
            print('  %-34s %-8s %-8s %s' % (r['tool'], r['stability'],
                                            r['evidence'], r['confidence']))
        print('')
        print('  THE FUSION IS A MINIMUM, NOT AN AVERAGE. A checker with a')
        print('  perfect flip rate and no control would AVERAGE to MEDIUM --')
        print('  which is exactly the rating checkblocks.py did not deserve when')
        print('  it always exited 0 for months and looked like a clean codebase.')
        print('  One weak signal caps the result. Always.')
        for r in sorted(rows, key=lambda x: x['_band'])[:6]:
            if r['_band'] <= LOW:
                print('')
                print('  %s -- %s' % (r['tool'], r['confidence']))
                print('      stability: %s' % r['stability_why'])
                print('      proven   : %s' % r['evidence_why'])

    return finish(
        ['%s is LOW confidence: %s / %s' % (r['tool'], r['stability_why'],
                                            r['evidence_why']) for r in low],
        ['%s has not been measured on one or both signals' % r['tool']
         for r in unknown],
        quiet=args.quiet,
        clean_line='\n  Every promoted checker is MEDIUM or better on both '
                   'signals. That is a statement about the two signals, not '
                   'about whether any checker is RIGHT.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
