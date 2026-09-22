"""Does the defect budget forbid anything right now? Item 20's missing half.

    python tools/defect_budget_gate.py          # the band, and whether it binds
    python tools/defect_budget_gate.py --why    # the full policy output too

Exit 0  the band permits the work in hand, OR the budget is not yet calibrated
        and therefore binds nothing (see below -- this is reported, not hidden)
Exit 1  the band FORBIDS new-vertical work and the budget IS calibrated
Exit 2  COULD NOT RUN -- the policy module or the register could not be read.
        Never folded into 0: an unreadable budget is not a permissive one.

── WHY THIS IS SEPARATE FROM defect_budget_policy.py ──────────────────────────
That module MEASURES and states a band. Its own header is explicit that it
"cannot stop anybody doing anything -- it states the band; the humans hold to
it", and until now nothing consulted it: the band was printed and no code
anywhere read it. This is the part that reads it.

── AND IT DELIBERATELY DOES NOT BIND YET, WHICH IS THE WHOLE POINT ────────────
Michael decided the WINDOW on 2026-09-22 (rolling, 30-day, recorded through
the tool's own --decide path with the reason). THE BUDGET NUMBER IS STILL
UNDECIDED, and defect_budget_policy.py says so in as many words:
BUDGET_PER_WINDOW "is a judgement and is written here to be argued with, not
derived."

The measured consequence, today: BUDGET_PER_WINDOW is 60 and the OBSERVED rate
is ~317 weighted defects per 30 days. Both windows therefore read ALL HANDS on
the first reading -- which means THE BUDGET IS WRONG, not that the platform is
in crisis, and the policy tool prints exactly that sentence.

SO WIRING THIS TO REFUSE TODAY WOULD HALT EVERY PUSH ON THE PLATFORM, on a
number its own author calls uncalibrated. That is not enforcement, it is an
outage with a policy label on it. The mechanism is built and wired; it binds
the moment a budget is recorded, and until then it reports the band and exits
0 while saying loudly that it is not binding.

THE DISTINCTION IS THE FAMILIAR ONE: "does not forbid anything" and "could not
tell whether it should" are different states, and folding the second into the
first is how a gate reports a pass it never performed (PR 1.11). An
uncalibrated budget is the first, stated; an unreadable register is the second,
exit 2.

── WHAT IT WILL FORBID, ONCE CALIBRATED ───────────────────────────────────────
The graduated response item 20 describes: at the tightest band, new-vertical
work yields to reliability work. This gate answers that question for a caller
that declares what KIND of work it is doing (--kind new-vertical|reliability),
and only new-vertical work can be refused -- refusing reliability work when
the defect budget is exhausted would forbid the only thing that refills it.
"""

import importlib.util
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = os.path.join(REPO, 'tools', 'defect_budget_policy.py')
DECISIONS = os.path.join(REPO, 'docs', 'defect-budget-decisions.json')

# ── THE BAND VOCABULARY IS READ FROM THE POLICY MODULE, NOT RESTATED ───────
# A first draft of this file hardcoded HEALTHY / WATCH / SLOW DOWN / ALL HANDS
# and every one of the first three was INVENTED -- the real bands are NORMAL,
# INCREASED REVIEW, FEATURE FREEZE and ALL HANDS. The gate would have treated
# three of four real bands as unknown and answered COULD NOT TELL for ever.
#
# defect_budget_policy.py already publishes both the band list and the set in
# which new work proceeds (NEW_WORK_ALLOWED), so this reads them. A gate that
# restates its subject's vocabulary is a second copy kept in step by nobody,
# and this one was wrong before it ever ran.


def load_policy():
    spec = importlib.util.spec_from_file_location('dbp', POLICY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main(argv):
    kind = 'new-vertical'
    if '--kind' in argv:
        i = argv.index('--kind')
        if len(argv) <= i + 1:
            print('--kind takes new-vertical or reliability')
            return 2
        kind = argv[i + 1]
    if kind not in ('new-vertical', 'reliability'):
        print('COULD NOT RUN -- unknown --kind %r. A work kind this gate has '
              'not been taught is not a permitted one.' % kind)
        return 2

    if not os.path.isfile(POLICY):
        print('COULD NOT RUN -- %s is absent. An unreadable budget is not a '
              'permissive one.' % POLICY)
        return 2
    try:
        pol = load_policy()
        records = pol.load_register()
    except Exception as e:
        print('COULD NOT RUN -- the policy module or register could not be '
              'read: %s: %s' % (type(e).__name__, e))
        return 2

    # The WINDOW decision is recorded; the BUDGET is not. Read both from the
    # file rather than assuming, so this reports the real state of the policy
    # and not the state it had when this was written.
    decided = {}
    if os.path.isfile(DECISIONS):
        try:
            decided = json.load(io.open(DECISIONS, encoding='utf-8'))
        except Exception as e:
            print('COULD NOT RUN -- %s is unreadable (%s). A corrupt decision '
                  'file is not an absent one.' % (DECISIONS, e))
            return 2

    window = decided.get('window_mode')
    budget_decided = bool(decided.get('budget_per_window_reason'))

    # THE POLICY MODULE OWNS THE ARITHMETIC AND THIS GATE DOES NOT REDO IT.
    # remaining_pct() and raw_band() are its own functions; re-deriving the
    # band here would be a second implementation of one rule kept in step by
    # nobody, which is the duplication this platform keeps paying for.
    try:
        pct, total, counted = pol.remaining_pct(records, window or 'rolling')
        band, _action = pol.raw_band(pct)
        pct = round(pct, 1)
    except Exception as e:
        print('COULD NOT RUN -- the policy module did not yield a band: '
              '%s: %s. A band that could not be computed is not a permissive '
              'one.' % (type(e).__name__, e))
        return 2

    print('DEFECT BUDGET GATE -- item 20')
    print('  window decided : %s' % (window or 'NOT DECIDED'))
    print('  budget decided : %s' % ('yes' if budget_decided else 'NO'))
    if band:
        print('  band           : %-12s %s%% remaining, %s record(s)'
              % (band, pct, counted))
    print('  work kind      : %s' % kind)
    print('')

    if not window:
        print('NOT BINDING -- the window question is undecided, so there is no')
        print('band to hold anyone to. This is the policy tool refusing to pick')
        print('for a reason, not an omission:')
        print('    python tools/defect_budget_policy.py --decide rolling "<why>"')
        return 0

    if not budget_decided:
        print('NOT BINDING -- and this is the state the platform is in today.')
        print('')
        print('The WINDOW is decided. THE BUDGET NUMBER IS NOT, and')
        print('defect_budget_policy.py says BUDGET_PER_WINDOW "is a judgement')
        print('and is written here to be argued with, not derived". It is 60')
        print('against an observed rate several times that, so every band reads')
        print('ALL HANDS -- which means the BUDGET is wrong, not that the')
        print('platform is in crisis. The policy tool prints that sentence')
        print('itself.')
        print('')
        print('ENFORCING ON IT WOULD HALT EVERY PUSH on a number its own author')
        print('calls uncalibrated. That is an outage with a policy label on it,')
        print('not enforcement. This gate binds the moment a budget is')
        print('recorded, and reports until then.')
        print('')
        print('FOR MICHAEL -- the remaining decision, same shape as the window:')
        print('  record a BUDGET_PER_WINDOW with its reason, and this starts')
        print('  refusing new-vertical work at ALL HANDS on the next run.')
        return 0

    known = tuple(n for _f, n, _a in pol.BANDS)
    if band not in known:
        print('COULD NOT TELL -- the policy module reported band %r, which is '
              'not in its own BANDS list %s. A band nobody mapped is not a '
              'pass.' % (band, list(known)))
        return 2

    if kind == 'reliability':
        print('PERMITTED -- reliability work is never refused by this gate.')
        print('Refusing it when the budget is exhausted would forbid the only')
        print('kind of work that refills it.')
        return 0

    if band not in pol.NEW_WORK_ALLOWED:
        print('REFUSED -- the band is %s and this work is new-vertical.' % band)
        print('The policy module permits new work in %s only.'
              % ', '.join(sorted(pol.NEW_WORK_ALLOWED)))
        print('Reliability work is still permitted: --kind reliability.')
        return 1

    print('PERMITTED -- the band is %s.' % band)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
