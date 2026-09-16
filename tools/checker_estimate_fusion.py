"""Item 52: FUSE the always-on drifting measurement with the accurate infrequent one.

    python tools/checker_estimate_fusion.py
    python tools/checker_estimate_fusion.py --json
    python tools/checker_estimate_fusion.py --quiet

Exit 0 clean · 1 at least one estimate is UNCORRECTED because its corrector
failed its own sanity check · 2 part of the run did not happen. REPORT ONLY.

── THE TWO SIGNALS, AND WHY FUSING THEM IS NOT THE SAME AS THE MIN ─────────
tools/checker_confidence.py already combines these two inputs BY CONJUNCTION --
`confidence = min(stability_band, evidence_band)` -- and that is the right
answer to ITS question, which is "what is this checker's verdict worth as a
rating". Its header argues the case and the argument holds: under a minimum, one
weak input caps the result and `checkblocks.py` cannot average its way to
MEDIUM.

THIS IS A DIFFERENT QUESTION AND A DIFFERENT SHAPE. Item 52 asks for a single
weighted ESTIMATE that TRACKS, in the inertial-navigation sense:

  THE INS  the flip rate from tools/flaky_checker_quarantine.py. Always on,
           cheap, accumulating every run -- and it DRIFTS, in a known
           direction: it measures only whether the verdict MOVED, so a checker
           that always exits 0 has a perfect flip rate forever. The drift is
           optimistic and it grows the longer the checker runs unchallenged.

  THE GPS  the control evidence from tools/checker_control_check.py. Does a
           control plant a defect and assert the checker REPORTS it, and plant
           clean code and assert it STAYS SILENT? Accurate, absolute -- and
           INFREQUENT, because a human has to write it.

A minimum throws away the tracking. The INS's value is that it moves between
fixes; the GPS's value is that it anchors the level. Fusing them keeps both:
the correction sets where the estimate sits, the flip rate moves it, and the
weight says how much to trust each.

── THE CAVEAT THAT SHAPES THIS FILE MORE THAN THE FUSION DOES ──────────────
A COMPROMISED CORRECTOR MAKES A FUSED ESTIMATE WORSE THAN NO FUSION AT ALL.
That is not a hypothetical borrowed from GPS spoofing. It is measured here:

  * tools/sabotage_control_check.py exists precisely because controls were
    found that NEVER VERIFY THEIR OWN SABOTAGE APPLIED. A control anchored on
    a string that no longer matches mutates nothing, the suite stays green, and
    the control reports "the checker fired" having tested nothing.
  * tools/mutation_anchor_check.py records that four of six probes could not be
    swept at all.

A control in that state is a GPS reporting a confident fix from a spoofed
satellite. Fusing it in does not add information, it REPLACES a known-biased
signal with a wrong one and hides the bias.

So the corrector is SANITY-CHECKED BEFORE IT IS ALLOWED TO CORRECT, and when it
fails the fusion REFUSES: weight goes to zero, the output is labelled
UNCORRECTED, and the exit code is 1. It does not silently fall back to the
drifting estimate wearing a fused name.

── WHAT THE NUMBER IS, STATED SO IT CANNOT BE OVER-READ ────────────────────
`fused` is NOT a probability and is not calibrated against anything. It is a
defined score in [0,1]:

    ins        = 1 - flip_rate                     (drifting, optimistic)
    gps        = 1.0 control fires BOTH ways
                 0.0 a control exists and does NOT fire both ways
                 None no control exists -- NOT 0, and not fused
    w          = gps_validity x ins_confidence_complement
    fused      = w*gps + (1-w)*ins

Nothing gates on it. It exists to put two numbers that were being read side by
side into one, with the weight visible, and to make a compromised corrector
LOUD instead of invisible.
"""
import argparse
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_UNCORRECTED = 1
EXIT_COULD_NOT_RUN = 2

# ── PRE-REGISTERED, AND THE POINT OF PRE-REGISTERING THEM IS THAT THEY ARE
#    NOT TUNED AFTER SEEING THE OUTPUT (convention 1). ────────────────────────
# The floor the corrector must clear before it may correct at all. 1.0 means a
# control must be verified in BOTH directions -- there is no partial credit,
# because a control that plants a defect and never plants clean code cannot
# tell a working checker from one that always reports.
CORRECTOR_FLOOR = 1.0
# The run count at which the flip rate is worth anything. Taken from
# flaky_checker_quarantine's own derivation rather than picked here: below the
# run count at which a single disagreement is EXPRESSIBLE, the rate is too
# coarse to carry weight.
MIN_RUNS_FOR_INS = 20


def load_confidence():
    """The two signals, from the tool that already computes both."""
    import checker_confidence as CC
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        CC.main(['--json'])
    text = buf.getvalue()
    i = text.find('{')
    if i < 0:
        raise RuntimeError('checker_confidence --json produced no object')
    return json.loads(text[i:])['rows']


def corrector_validity():
    """Which controls are SANITY-CHECKED, from the tool that measures exactly
    that. Returns (set_of_guarded_probe_paths, total_seen) or (None, None) when
    it could not be read -- which is COULD NOT TELL and never "all valid"."""
    # analyse() IS PER-FILE, and the walk below is taken from that tool's own
    # main() rather than invented differently -- two definitions of "which
    # probes exist" is the pinned-list-drift shape one more time. If its
    # interface moves, this returns COULD NOT TELL and every estimate goes
    # UNCORRECTED: the safe direction, and a loud one.
    try:
        import sabotage_control_check as S
        guarded, unguarded = set(), set()
        for root, _d, files in os.walk(os.path.join(REPO, 'tests')):
            for f in sorted(files):
                if not (f.endswith('.py') or f.endswith('.js')):
                    continue
                path = os.path.join(root, f)
                rel = os.path.relpath(path, REPO).replace(os.sep, '/')
                a = S.analyse(rel, io.open(path, encoding='utf-8',
                                           errors='replace').read())
                if not a:
                    continue
                (guarded if a['guarded'] else unguarded).add(a['file'])
    except Exception as e:                                      # noqa: BLE001
        return None, 'sabotage_control_check could not be read: %s: %s' % (
            type(e).__name__, e)
    # A READER THAT RECOGNISES NOTHING IS NOT A CLEAN FLEET. That distinction is
    # the one this whole file is about, so it is made here rather than assumed.
    if not guarded and not unguarded:
        return None, ('sabotage_control_check recognised NO probe at all, which '
                      'is not a clean fleet -- it is a reader that stopped '
                      'matching. Refusing to correct with it.')
    return {'guarded': guarded, 'unguarded': unguarded,
            'criteria': getattr(S, 'CRITERIA_VERSION', None)}, None


def ins_from(row):
    """(value, confidence, why). Parsed from the stability reason, which is the
    only place the run count is published."""
    why = row.get('stability_why') or ''
    runs = None
    for tok in why.split():
        if tok.isdigit():
            runs = int(tok)
            break
    band = row.get('stability')
    # The flip rate itself is not in the JSON; the band and the reason are. HIGH
    # with "no verdict has ever moved" is a flip rate of 0.
    if band == 'HIGH' and 'never' in why:
        val = 1.0
    elif band == 'HIGH':
        val = 0.95
    elif band == 'MEDIUM':
        val = 0.7
    elif band == 'LOW':
        val = 0.3
    else:
        return None, 0.0, 'no stability band -- %s' % (why or 'no reason given')
    if runs is None:
        return val, 0.0, 'the run count is not published in the reason, so this ' \
                         'carries no weight'
    conf = min(1.0, runs / float(MIN_RUNS_FOR_INS))
    return val, conf, '%d runs, %s' % (runs, band)


def gps_from(row):
    """(value, why). None when no control exists -- which is NOT zero."""
    band = row.get('evidence')
    why = row.get('evidence_why') or ''
    if band == 'HIGH':
        return 1.0, why
    if band in ('MEDIUM', 'LOW'):
        # A control that exists and does not prove BOTH directions cannot
        # distinguish a working checker from one that always reports.
        return 0.0, why
    return None, why or 'no control declared'


def fuse(rows, validity):
    out = []
    for row in rows:
        ins, ins_conf, ins_why = ins_from(row)
        gps, gps_why = gps_from(row)

        rec = {'tool': row.get('tool'), 'ins': ins, 'ins_confidence': ins_conf,
               'ins_why': ins_why, 'gps': gps, 'gps_why': gps_why}

        if ins is None:
            rec.update(fused=None, weight=None, state='COULD NOT TELL',
                       why='no usable continuous signal')
            out.append(rec)
            continue

        if gps is None:
            # NO CORRECTION IS NOT A CORRECTION OF ZERO. The estimate is the
            # drifting one and it is labelled as such, with the direction of its
            # bias named so nobody reads it as neutral.
            rec.update(fused=ins, weight=0.0, state='UNCORRECTED -- NO CONTROL',
                       why='no control exists, so the estimate is the drifting '
                           'signal alone. Its bias is OPTIMISTIC: a checker that '
                           'always exits 0 scores 1.0 here.')
            out.append(rec)
            continue

        # ── THE CORRECTOR'S OWN SANITY CHECK, and it gates the weight ──────
        vw, vwhy = 1.0, 'the corrector is sanity-checked'
        if validity is None:
            vw, vwhy = 0.0, 'the corrector\'s own validity COULD NOT BE READ, ' \
                            'so it is not trusted to correct'
        else:
            # A control among the UNGUARDED set is one that does not verify its
            # own sabotage applied. Matching is by tool name appearing in the
            # unguarded probe paths, which is coarse and is stated as such.
            name = (row.get('tool') or '').replace('.py', '').replace('.js', '')
            if name and any(name in u for u in validity['unguarded']):
                vw = 0.0
                vwhy = ('its control is in sabotage_control_check\'s UNGUARDED '
                        'set -- it does not verify its own sabotage applied, so '
                        'correcting with it would replace a known-biased signal '
                        'with a wrong one')
        if vw < CORRECTOR_FLOOR:
            rec.update(fused=ins, weight=0.0,
                       state='UNCORRECTED -- CORRECTOR REFUSED',
                       why=vwhy)
            out.append(rec)
            continue

        # The correction carries more weight the LESS the continuous signal has
        # earned. A flip rate from 6 runs cannot outvote a control.
        w = vw * (1.0 - ins_conf) if ins_conf < 1.0 else vw * 0.5
        # A WEIGHT OF ~1 MEANS THE DRIFTING SIGNAL CONTRIBUTED NOTHING, and
        # calling that "FUSED" would let a pure correction be read as two
        # independent signals agreeing. It happens whenever the continuous
        # signal has earned no confidence at all -- too few runs -- and that is
        # exactly when a reader most needs to know only one thing was measured.
        state = 'FUSED' if w < 0.99 else 'CORRECTION ONLY -- the continuous '                                          'signal has earned no weight'
        rec.update(fused=round(w * gps + (1 - w) * ins, 4), weight=round(w, 4),
                   state=state, why=vwhy)
        out.append(rec)
    return out


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args(argv)

    try:
        rows = load_confidence()
    except Exception as e:                                      # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        print('Nothing was fused. This is exit 2, not a pass.')
        return EXIT_COULD_NOT_RUN

    validity, verr = corrector_validity()
    fused = fuse(rows, validity)
    refused = [r for r in fused if (r['state'] or '').startswith('UNCORRECTED')]
    cnt = [r for r in fused if r['state'] == 'COULD NOT TELL']

    if args.json:
        print(json.dumps({'rows': fused, 'corrector_readable': validity is not None,
                          'corrector_error': verr,
                          'min_runs_for_ins': MIN_RUNS_FOR_INS,
                          'corrector_floor': CORRECTOR_FLOOR}, indent=1))
        return EXIT_COULD_NOT_RUN if cnt else (EXIT_UNCORRECTED if refused else 0)

    if not args.quiet:
        print('CHECKER ESTIMATE FUSION -- item 52, report only')
        print('  %d checkers · corrector readable: %s'
              % (len(fused), 'yes' if validity is not None else 'NO -- ' + str(verr)))
        print('')
        # THE WEIGHT IS IN THE TABLE, not only in --json. The paragraph below
        # says the weight is visible on purpose; a first version printed that
        # sentence and then omitted the column, which is a tool asserting a
        # property it does not have.
        print('  %-38s %5s %5s %6s %6s  %s'
              % ('tool', 'INS', 'GPS', 'w', 'fused', 'state'))
        for r in sorted(fused, key=lambda x: (x['fused'] is None, x['fused'])):
            print('  %-38s %5s %5s %6s %6s  %s'
                  % (r['tool'],
                     '--' if r['ins'] is None else '%.2f' % r['ins'],
                     '--' if r['gps'] is None else '%.2f' % r['gps'],
                     '--' if r['weight'] is None else '%.2f' % r['weight'],
                     '--' if r['fused'] is None else '%.3f' % r['fused'],
                     r['state']))
        print('')
        print('  THE WEIGHT IS VISIBLE ON PURPOSE. A fused number whose weight')
        print('  is hidden is two numbers pretending to be one.')
        print('')
        print('  INS is 1 - flip_rate: ALWAYS ON, CHEAP, AND OPTIMISTICALLY')
        print('  BIASED -- a checker that always exits 0 scores 1.00.')
        print('  GPS is the control: accurate and infrequent.')
        print('  A correction is applied ONLY when the corrector passes its own')
        print('  sanity check, because a compromised corrector makes the')
        print('  estimate WORSE than no fusion at all.')
        if refused:
            print('')
            print('  UNCORRECTED (%d) -- the estimate is the DRIFTING signal '
                  'alone:' % len(refused))
            for r in refused:
                print('    %-38s %s' % (r['tool'], r['why']))
        if cnt:
            print('')
            print('  COULD NOT TELL (%d) -- NOT a pass:' % len(cnt))
            for r in cnt:
                print('    %-38s %s' % (r['tool'], r['why']))

    return EXIT_COULD_NOT_RUN if cnt else (EXIT_UNCORRECTED if refused else 0)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
