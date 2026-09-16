"""Item 84: four separately-tracked risks share one worst case. This is the tree.

    python tools/risk_event_tree.py
    python tools/risk_event_tree.py --json
    python tools/risk_event_tree.py --self-check

Exit 0 always unless the tree could not be evaluated (2). REPORT ONLY.

── THE POINT, AND WHY FOUR OPEN ITEMS ARE ONE RISK ─────────────────────────
Items 6, 19, 35 and 65 are carried separately and each reads as a moderate gap
on its own. They are four BARRIERS IN SERIES against the same initiating event
-- a Tier A write that goes wrong -- and the exposure that matters is the
probability that ALL FOUR fail together, which no one of them can show.

  B1  the INVARIANT refuses the bad value          (item 6)
  B2  the LOCK prevents the corrupting interleave  (item 19)
  B3  the AUDIT CHAIN reveals it happened          (item 35)
  B4  the BACKUP restores the state before it      (item 65)

B1 and B2 PREVENT. B3 and B4 RECOVER. The worst end state is the one where
prevention failed, nobody noticed, and nothing can be restored -- a corrupted
Tier A record that is now the only version there is.

── THE NUMBERS ARE ESTIMATES AND THE TOOL REFUSES TO HIDE IT ───────────────
There is no incident data on this platform to fit a failure rate to. Every
per-barrier probability below is a JUDGEMENT with a stated basis and a band,
never a point, and the output is a RANGE. A single number here would be read as
measured within a week of being written.

WHAT IS ROBUST TO ROUGH NUMBERS IS THE RANKING, and that is the deliverable.
An importance measure asks how much the worst-case probability moves when one
barrier goes from its best to its worst assumed value. That ordering is often
stable even when the absolute figures are not -- and STABILITY IS MEASURED
HERE rather than assumed: the ranking is recomputed at every corner of the
band space and reported STABLE only if it does not change. Accuracy and
stability are two numbers and never one.

── WHAT THIS DOES NOT CLAIM ────────────────────────────────────────────────
  * NOT a frequency. The tree is CONDITIONAL on the initiating event; it says
    nothing about how often a Tier A write goes wrong, because nothing measures
    that.
  * NOT independence. The barriers are treated as independent and THEY ARE NOT
    -- a session that skips the invariant is a session that skips the audit
    review too. Common-cause dependence makes the real worst-case probability
    HIGHER than the product, so the figures here are a FLOOR. Stated, because
    an event tree that quietly assumes independence reads as conservative and
    is the opposite.
  * NOT a licence to stop at the first barrier. The ranking says where the next
    hour is best spent, not which barriers can be dropped.
"""
import argparse
import itertools
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN                       # noqa: E402

# ── THE BARRIERS ────────────────────────────────────────────────────────────
# p_fail is the probability the barrier does NOT stop / does NOT reveal / does
# NOT restore, GIVEN the initiating event. Each band is a judgement anchored to
# something measured, and the anchor is written down so the number can be
# argued with rather than inherited.
BARRIERS = [
    {
        'id': 'B1', 'item': 'item 6', 'role': 'prevent',
        'name': 'the INVARIANT refuses the bad value',
        'p_fail': (0.55, 0.90),
        'basis': 'tools/invariant_runner.js runs clean, and its own output '
                 'states the coverage: FOUR engines are classified by hand and '
                 'THIRTY other money-named Tier A resources are UNCOVERED. So '
                 'for a randomly chosen Tier A write the invariant layer is '
                 'absent far more often than present. The band is wide because '
                 '4-of-34 is a coverage ratio, not a failure rate, and using it '
                 'as one is a substitution this file is making knowingly.',
        'measured': '4 of 34 money-named Tier A resources covered',
    },
    {
        'id': 'B2', 'item': 'item 19', 'role': 'prevent',
        'name': 'the LOCK prevents the corrupting interleave',
        'p_fail': (0.10, 0.60),
        'basis': 'nine advisory-lock functions were swept 2026-09-15; three '
                 'were UNGUARDED against the REPEATABLE READ snapshot hole and '
                 'were fixed IN FILES. The repository is not the database: none '
                 'of those guards does anything until the migration is re-run, '
                 'and nothing in a clone can confirm it was. The low end assumes '
                 'the migrations ran; the high end assumes they did not. The '
                 'band is wide BECAUSE THAT QUESTION IS OPEN, not because the '
                 'code is unclear.',
        'measured': '3 of 9 lock functions were unguarded; fixes unverified live',
    },
    {
        'id': 'B3', 'item': 'item 35', 'role': 'recover',
        'name': 'the AUDIT CHAIN reveals that it happened',
        'p_fail': (0.15, 0.45),
        'basis': 'the daily chained digest is an independently computed '
                 'fingerprint of history, which is the strongest of the four by '
                 'construction: it needs no baseline capture. Against it -- one '
                 'confirmed defect was found in the checkpoint pager (its '
                 'completeness guard vanished when its input did), it has a '
                 'First Article Inspection with 8 claims and 0 unverified, and '
                 'IT ONLY REVEALS WHAT IS INSIDE THE WINDOW IT CHECKPOINTS. A '
                 'write and its corruption inside one open window are invisible '
                 'to it until that window closes.',
        'measured': 'FAI 8 claims / 0 unverified; 1 confirmed defect found and fixed',
    },
    {
        'id': 'B4', 'item': 'item 65', 'role': 'recover',
        'name': 'the BACKUP restores the state before it',
        'p_fail': (0.30, 0.95),
        'basis': 'the nightly job restores the dump it just took and runs a '
                 'coherence check against it, which is a real restore test and '
                 'is why the low end is not higher. THE HIGH END IS 0.95 '
                 'BECAUSE COMPLETENESS IS UNVERIFIED: whether the backup reader '
                 'can SEE every Tier A table depends on a default ACL per '
                 'creating role, and verify 2c and 2d in '
                 'sql/backup_reader_role.sql HAVE NEVER BEEN RUN. A backup that '
                 'restores perfectly and was missing the table is a restore '
                 'that returns the wrong state confidently. This is the widest '
                 'band in the tree and the cheapest to close: two queries.',
        'measured': 'restore test runs nightly; default-ACL completeness NEVER RUN',
    },
]

# End states, read off the four success/failure branches in order.
# True = the barrier FAILED.
def end_state(f1, f2, f3, f4):
    if not (f1 and f2):
        return 'PREVENTED'
    if not f3 and not f4:
        return 'CORRUPTED, DETECTED, RECOVERABLE'
    if not f3 and f4:
        return 'CORRUPTED, DETECTED, NOT RECOVERABLE'
    if f3 and not f4:
        return 'CORRUPTED, UNDETECTED, restorable but nobody knows to'
    return 'CORRUPTED, UNDETECTED, UNRECOVERABLE'


WORST = 'CORRUPTED, UNDETECTED, UNRECOVERABLE'


def tree(ps):
    """{end_state: probability} for one vector of per-barrier failure probs."""
    out = {}
    for bits in itertools.product([False, True], repeat=4):
        p = 1.0
        for bit, pf in zip(bits, ps):
            p *= pf if bit else (1.0 - pf)
        out[end_state(*bits)] = out.get(end_state(*bits), 0.0) + p
    return out


def worst_case_range(barriers):
    """(low, high, low_vector, high_vector) over every corner of the bands.

    EXACT, not sampled. The worst-state probability is monotone increasing in
    every p_fail, so its extremes sit at the corners -- no Monte Carlo, and no
    seed for anybody to wonder about.
    """
    best = None
    worst = None
    for corner in itertools.product(*[b['p_fail'] for b in barriers]):
        p = tree(list(corner)).get(WORST, 0.0)
        if best is None or p < best[0]:
            best = (p, corner)
        if worst is None or p > worst[0]:
            worst = (p, corner)
    return best[0], worst[0], best[1], worst[1]


def importance(barriers):
    """How much the worst-case probability moves when ONE barrier swings across
    its band with the others held at their band midpoint.

    This is the Birnbaum-style question -- how sensitive is the outcome to this
    component -- and it is the part that survives rough inputs.
    """
    mids = [(b['p_fail'][0] + b['p_fail'][1]) / 2.0 for b in barriers]
    out = []
    for i, b in enumerate(barriers):
        lo = list(mids)
        hi = list(mids)
        lo[i], hi[i] = b['p_fail'][0], b['p_fail'][1]
        d = tree(hi).get(WORST, 0.0) - tree(lo).get(WORST, 0.0)
        out.append({'id': b['id'], 'name': b['name'], 'swing': d})
    out.sort(key=lambda r: -r['swing'])
    return out


def ranking_stable(barriers):
    """Is the importance ORDER the same at every corner of the band space?

    A ranking that flips depending on where the other barriers sit is a ranking
    nobody should act on, and saying it is stable without checking is the
    single-number habit this platform keeps finding.
    """
    orders = set()
    for corner in itertools.product(*[b['p_fail'] for b in barriers]):
        ranked = []
        for i, b in enumerate(barriers):
            lo = list(corner)
            hi = list(corner)
            lo[i], hi[i] = b['p_fail'][0], b['p_fail'][1]
            ranked.append((tree(hi).get(WORST, 0.0) - tree(lo).get(WORST, 0.0),
                           b['id']))
        ranked.sort(key=lambda r: (-r[0], r[1]))
        orders.add(tuple(r[1] for r in ranked))
    return (len(orders) == 1), sorted(orders)


def self_check():
    fails = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            fails.append(name)

    # ── THE TREE IS A PROBABILITY DISTRIBUTION ──────────────────────────
    t = tree([0.5, 0.5, 0.5, 0.5])
    ck('the end-state probabilities sum to 1', abs(sum(t.values()) - 1.0) < 1e-9,
       sum(t.values()))
    ck('every one of the five end states is reachable', len(t) == 5, sorted(t))

    # ── THE EXTREMES, IN BOTH DIRECTIONS ────────────────────────────────
    ck('a barrier set that never fails leaves ZERO worst-case exposure',
       tree([0.0, 0.0, 0.0, 0.0]).get(WORST, 0.0) == 0.0)
    ck('...and one that always fails puts ALL of it there',
       abs(tree([1.0, 1.0, 1.0, 1.0]).get(WORST, 0.0) - 1.0) < 1e-9)
    ck('EITHER prevention barrier holding is enough to prevent',
       abs(tree([0.0, 1.0, 1.0, 1.0]).get('PREVENTED', 0.0) - 1.0) < 1e-9
       and abs(tree([1.0, 0.0, 1.0, 1.0]).get('PREVENTED', 0.0) - 1.0) < 1e-9,
       'B1 or B2 alone must stop it')
    ck('detection alone does NOT recover -- it moves the end state, not the loss',
       abs(tree([1.0, 1.0, 0.0, 1.0]).get(
           'CORRUPTED, DETECTED, NOT RECOVERABLE', 0.0) - 1.0) < 1e-9)

    # ── MONOTONICITY, which is what makes the corner search exact ───────
    base = tree([0.5, 0.5, 0.5, 0.5]).get(WORST, 0.0)
    worse = tree([0.6, 0.5, 0.5, 0.5]).get(WORST, 0.0)
    ck('the worst case is MONOTONE in each p_fail, so the corners are the '
       'extremes and no sampling is needed', worse > base, (base, worse))

    # ── IMPORTANCE DISCRIMINATES ────────────────────────────────────────
    fake = [dict(b) for b in BARRIERS]
    for b in fake:
        b['p_fail'] = (0.5, 0.5)
    imp = importance(fake)
    ck('a barrier with NO band has zero swing -- importance is about the '
       'uncertainty, not the level',
       all(abs(r['swing']) < 1e-12 for r in imp), imp)
    fake[3]['p_fail'] = (0.1, 0.9)
    imp2 = importance(fake)
    ck('...and widening one band puts it top of the ranking',
       imp2[0]['id'] == 'B4' and imp2[0]['swing'] > 0, imp2)

    stable, orders = ranking_stable(fake)
    ck('the stability check really compares orders rather than returning True',
       isinstance(stable, bool) and len(orders) >= 1, orders)

    # ── THE DECLARED BARRIERS ARE HONEST ────────────────────────────────
    ck('every barrier states a BASIS for its band, at length',
       all(len(b['basis']) > 150 for b in BARRIERS),
       [(b['id'], len(b['basis'])) for b in BARRIERS])
    ck('every barrier is a BAND, never a point -- a point would be read as '
       'measured', all(b['p_fail'][0] < b['p_fail'][1] for b in BARRIERS),
       [(b['id'], b['p_fail']) for b in BARRIERS])
    ck('every barrier cites what was actually MEASURED, separately from the '
       'judgement', all(len(b.get('measured') or '') > 20 for b in BARRIERS))
    ck('two barriers PREVENT and two RECOVER, or the tree shape is wrong',
       sorted(b['role'] for b in BARRIERS)
       == ['prevent', 'prevent', 'recover', 'recover'])

    print('\n%d failure(s)' % len(fails))
    return 1 if fails else 0


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                            # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    args = ap.parse_args(argv)
    if args.selfcheck:
        return self_check()

    try:
        lo, hi, lo_v, hi_v = worst_case_range(BARRIERS)
        mids = [(b['p_fail'][0] + b['p_fail'][1]) / 2.0 for b in BARRIERS]
        mid_tree = tree(mids)
        imp = importance(BARRIERS)
        stable, orders = ranking_stable(BARRIERS)
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        return EXIT_COULD_NOT_RUN

    if args.json:
        print(json.dumps({
            'initiating_event': 'a Tier A write goes wrong',
            'barriers': [{k: v for k, v in b.items()} for b in BARRIERS],
            'worst_state': WORST,
            'worst_case_range': {'low': lo, 'high': hi,
                                 'low_vector': lo_v, 'high_vector': hi_v},
            'end_states_at_band_midpoint': mid_tree,
            'importance': imp, 'ranking_stable': stable,
            'orders_seen': [list(o) for o in orders]}, indent=1))
        return 0

    if not args.quiet:
        print('PROBABILISTIC RISK ASSESSMENT -- item 84, report only')
        print('  INITIATING EVENT: a Tier A write goes wrong.')
        print('  Four barriers in series, carried as four separate open items.')
        print('')
        for b in BARRIERS:
            print('  %-3s %-8s p(fail) %.2f - %.2f   %s'
                  % (b['id'], b['item'], b['p_fail'][0], b['p_fail'][1],
                     b['name']))
            print('      MEASURED: %s' % b['measured'])
        print('')
        print('  END STATES, at the band midpoint:')
        for k, v in sorted(mid_tree.items(), key=lambda kv: -kv[1]):
            print('    %6.1f%%  %s' % (100 * v, k))
        print('')
        print('  WORST CASE -- %s' % WORST)
        print('    %.1f%% to %.1f%% conditional on the initiating event.'
              % (100 * lo, 100 * hi))
        print('    THAT IS A RANGE FROM JUDGEMENTS, NOT A MEASUREMENT. There is')
        print('    no incident data on this platform to fit a rate to, and a')
        print('    single number here would read as measured within a week.')
        print('    IT IS ALSO A FLOOR: the barriers are treated as independent')
        print('    and they are not, so common-cause dependence pushes the real')
        print('    figure UP, not down.')
        print('')
        print('  WHERE THE NEXT HOUR GOES -- how much the worst case moves when')
        print('  one barrier swings across its band, others held at midpoint:')
        for r in imp:
            print('    %-3s  %+.1f pp   %s' % (r['id'], 100 * r['swing'],
                                               r['name']))
        print('')
        print('  RANKING IS %s across every corner of the band space%s'
              % ('STABLE' if stable else 'NOT STABLE',
                 '.' if stable else ' -- %d different orders seen, so the '
                 'ranking is NOT something to act on.' % len(orders)))
        print('')
        # THE READING FOLLOWS THE COMPUTATION, NOT THE OTHER WAY ROUND. The
        # first version of this block asserted "the absolute probability is
        # soft and the ORDER is not" as fixed text -- and the stability check
        # sitting three lines above it had just reported five different orders.
        # A conclusion printed regardless of the number it claims to be drawn
        # from is the fabricated-KPI shape wearing a sentence.
        top = imp[0]
        widest = max(BARRIERS, key=lambda b: b['p_fail'][1] - b['p_fail'][0])
        print('  THE ACTIONABLE READING:')
        if stable:
            print('    The absolute probability is soft; the ORDER is not. %s '
                  'dominates' % top['id'])
            print('    at every corner, so it is where the next hour goes.')
        else:
            print('    NEITHER the absolute probability NOR the ranking is firm')
            print('    enough to act on directly -- the order changes with the')
            print('    assumptions, which is what %d distinct orderings means.'
                  % len(orders))
            print('    SO THE TREE DOES NOT PICK THE WORK. What it does say is')
            print('    which band is WIDEST, and that is a fact about what is')
            print('    unmeasured rather than about what is risky:')
        print('    %s (%s) spans %.2f-%.2f, the widest in the tree.'
              % (widest['id'], widest['item'], widest['p_fail'][0],
                 widest['p_fail'][1]))
        print('    ITS UNCERTAINTY IS TWO QUERIES WIDE: verify 2c and 2d in')
        print('    sql/backup_reader_role.sql have never been run. Running them')
        print('    does not reduce the risk -- it narrows the band, and a')
        print('    narrower band is what would let this tree rank at all.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
