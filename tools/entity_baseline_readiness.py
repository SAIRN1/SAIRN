"""Item 51: is a PER-ENTITY defect baseline buildable yet, and on which entity?

    python tools/entity_baseline_readiness.py
    python tools/entity_baseline_readiness.py --json
    python tools/entity_baseline_readiness.py --self-check

Exit 0 when at least one entity is ready, 1 when none is, 2 when the question
could not be answered. REPORT ONLY -- nothing gates on this, and it does not
compute a baseline. It answers whether computing one would mean anything.

── WHY THIS IS A TOOL AND NOT A THIRD PARAGRAPH IN A FINDINGS DOC ──────────
Item 51 has now been measured by hand twice (2026-09-14 at 68 records, again on
2026-09-15 at 77) and both times the answer was NOT YET. "Not yet" is a claim
with an expiry date and nothing was watching it -- which is the eighth standing
discipline in CLAUDE.md: nothing announces the day a check stops testing
anything, and nothing announces the day a refusal stops being true either. The
register grows every session. This re-answers the question from the register on
every run, so the day it flips, something says so.

── TWO BARS, AND A DIMENSION MUST CLEAR BOTH ───────────────────────────────
A per-entity baseline is a RATE: defects per unit of exposure, per entity. Both
halves have to exist.

  1. ENOUGH RECORDS PER UNIT. A baseline needs a distribution. You cannot
     compute one from n=1, and a threshold set from n=1 is that single value
     wearing a decision. The bar is MIN_RECORDS_PER_UNIT and it is A JUDGEMENT,
     PRE-REGISTERED AND STATED AS ONE -- nothing here derives it, and it is
     printed with every verdict so it can be argued with rather than inherited.

  2. A MEASURABLE DENOMINATOR. Without exposure a "baseline" is a COUNT wearing
     a rate, and the count is then driven by how much attention the entity got.
     This is the same denominator trap `tools/defect_dispersion.py` exists to
     close, applied one level up: there it was the zero units missing from a
     Gini, here it is the exposure missing from a rate.

A dimension that clears bar 1 and fails bar 2 is NOT ready, and saying so is the
whole point -- it is the case that looks ready and is not.

── THE CATCH-ALL BUCKET IS NOT AN ENTITY ───────────────────────────────────
`PLATFORM` holds the majority of the register and is not an app. Counting it as
a unit would make the `app` dimension look nearly ready off the strength of one
bucket that no baseline could ever be set for. It is excluded by name and the
exclusion is PRINTED, because a silent exclusion is a different tool from a
declared one.
"""
import argparse
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                # noqa: E402

REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')

# ── PRE-REGISTERED, AND A JUDGEMENT. Stated so it can be argued with. ───────
# The 2026-09-14 findings put the honest bar "somewhere around 20-30 records per
# entity". The low end is taken, deliberately: a readiness check that is too
# strict reports NOT YET forever and stops being read, which is the failure mode
# that matters more here than admitting one entity a fortnight early.
MIN_RECORDS_PER_UNIT = 20
MIN_READY_UNITS = 2        # one unit is not a comparison, and a baseline is one

# Buckets that are not entities. Excluded by name, never by a rule that could
# quietly grow to cover a real app.
NOT_AN_ENTITY = ('PLATFORM',)

# Whether an exposure denominator EXISTS for each candidate dimension. This is
# the half that is not about volume and cannot be fixed by waiting.
EXPOSURE = {
    'app': (True, 'commits and lines touching that app file, already computed '
                  'by tools/defect_dispersion.py'),
    'layer': (False, 'product / tooling / test is a CLASSIFICATION, not a '
                     'surface -- there is no "amount of layer" at risk, so a '
                     'per-layer figure is a COUNT and a count is driven by how '
                     'much attention the layer got'),
    'detection_method': (False, 'the population is the methods that EXIST, '
                                'which is a judgement rather than a count -- '
                                'defect_dispersion.py already refuses the '
                                'over-population figures on this dimension for '
                                'the same reason'),
}


def units(recs, field):
    """{unit: n}, with the declared non-entity buckets removed."""
    out = {}
    for r in recs:
        v = r.get(field)
        if not v or v in NOT_AN_ENTITY:
            continue
        out[v] = out.get(v, 0) + 1
    return out


def assess(recs, field):
    """One dimension, both bars, and which one it failed."""
    tally = units(recs, field)
    excluded = sum(1 for r in recs if r.get(field) in NOT_AN_ENTITY)
    ready = sorted([u for u, n in tally.items() if n >= MIN_RECORDS_PER_UNIT],
                   key=lambda u: -tally[u])
    has_exp, exp_note = EXPOSURE.get(field, (None, 'not assessed'))
    volume_ok = len(ready) >= MIN_READY_UNITS

    if has_exp is None:
        verdict, why = 'NOT ASSESSED', 'no exposure judgement recorded for this dimension'
    elif volume_ok and has_exp:
        verdict = 'READY'
        why = ('%d units clear %d records and an exposure denominator exists'
               % (len(ready), MIN_RECORDS_PER_UNIT))
    elif not volume_ok and not has_exp:
        verdict = 'NOT READY -- BOTH BARS'
        why = ('only %d unit(s) clear %d records, AND there is no exposure '
               'denominator: %s' % (len(ready), MIN_RECORDS_PER_UNIT, exp_note))
    elif not volume_ok:
        verdict = 'NOT READY -- VOLUME'
        why = ('only %d of %d unit(s) clear %d records; the largest has %d. '
               'This one is a matter of TIME and the register grows.'
               % (len(ready), len(tally), MIN_RECORDS_PER_UNIT,
                  max(tally.values()) if tally else 0))
    else:
        verdict = 'NOT READY -- NO DENOMINATOR'
        why = ('%d units clear the record bar, SO THIS DIMENSION LOOKS READY '
               'AND IS NOT: %s. Waiting will not fix it.'
               % (len(ready), exp_note))
    return {
        'dimension': field, 'units': len(tally), 'records': sum(tally.values()),
        'excluded_records': excluded, 'excluded_buckets': list(NOT_AN_ENTITY),
        'largest': max(tally.values()) if tally else 0,
        'ready_units': ready, 'volume_ok': volume_ok,
        'has_exposure': has_exp, 'exposure_note': exp_note,
        'verdict': verdict, 'why': why,
        'tally': dict(sorted(tally.items(), key=lambda kv: -kv[1])),
    }


def assess_all(recs):
    return [assess(recs, f) for f in ('app', 'layer', 'detection_method')]


def _fixtures():
    """Both directions on every bar, built to isolate ONE failure each."""
    def rec(app, layer='product', method='code-review'):
        return {'app': app, 'layer': layer, 'detection_method': method}

    # VOLUME FAILS, exposure exists: many apps, none big enough.
    thin = [rec('app%d' % (i % 12)) for i in range(36)]
    # VOLUME PASSES and exposure exists -> the only shape that is READY.
    fat = [rec('app%d' % (i % 3)) for i in range(90)]
    # VOLUME PASSES on a dimension with NO denominator. This is the fixture
    # that proves the second bar is load-bearing: without it, a tool checking
    # only volume would score identically on every other arm here.
    no_denom = [rec('app%d' % (i % 3), layer=('product', 'tooling', 'test')[i % 3])
                for i in range(90)]
    # The catch-all bucket alone must not make a dimension ready.
    bucket = [rec('PLATFORM') for _ in range(200)] + [rec('real1') for _ in range(5)]
    return {'thin': thin, 'fat': fat, 'no_denom': no_denom, 'bucket': bucket}


def self_check():
    f = _fixtures()
    fails = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            fails.append(name)

    a = assess(f['thin'], 'app')
    ck('too few records per unit is NOT READY -- VOLUME',
       a['verdict'] == 'NOT READY -- VOLUME', a)
    ck('...and it says so is a matter of TIME, because it is',
       'matter of TIME' in a['why'], a['why'])

    b = assess(f['fat'], 'app')
    ck('enough records on a dimension WITH a denominator is READY -- the check '
       'can pass', b['verdict'] == 'READY', b)

    c = assess(f['no_denom'], 'layer')
    ck('a dimension that clears the RECORD bar but has NO denominator is NOT '
       'READY', c['verdict'] == 'NOT READY -- NO DENOMINATOR', c)
    ck('...and its volume bar is recorded as PASSED, so the refusal is about '
       'the denominator and not a disguised volume failure',
       c['volume_ok'] is True and c['has_exposure'] is False, c)
    ck('...and it says waiting will not fix it',
       'Waiting will not fix it' in c['why'], c['why'])

    d = assess(f['bucket'], 'app')
    ck('the PLATFORM bucket does not make a dimension ready',
       d['verdict'].startswith('NOT READY'), d)
    ck('...and its 200 records are reported as EXCLUDED, not silently dropped',
       d['excluded_records'] == 200 and 'PLATFORM' in d['excluded_buckets'], d)
    ck('...and it is not counted as a unit',
       'PLATFORM' not in d['tally'], d['tally'])

    # CONTROL ON THE BAR ITSELF: a bar of 1 would call the thin fixture ready,
    # so the arms above would pass on a tool that had no bar at all.
    real = MIN_RECORDS_PER_UNIT
    try:
        globals()['MIN_RECORDS_PER_UNIT'] = 1
        ck('with the bar at 1 the thin fixture WOULD be ready -- so the arms '
           'above are testing the bar, not the fixture',
           assess(f['thin'], 'app')['verdict'] == 'READY',
           assess(f['thin'], 'app'))
    finally:
        globals()['MIN_RECORDS_PER_UNIT'] = real

    ck('the bar is pre-registered at the LOW end of the stated 20-30 judgement',
       MIN_RECORDS_PER_UNIT == 20, MIN_RECORDS_PER_UNIT)
    ck('one ready unit is not enough -- a baseline needs a comparison',
       MIN_READY_UNITS >= 2, MIN_READY_UNITS)

    print('\n%d failure(s)' % len(fails))
    return 1 if fails else 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    args = ap.parse_args(argv)

    if args.selfcheck:
        return self_check()

    try:
        recs = json.load(io.open(REGISTER, encoding='utf-8'))['records']
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        return EXIT_COULD_NOT_RUN

    rows = assess_all(recs)
    ready = [r for r in rows if r['verdict'] == 'READY']

    if args.json:
        print(json.dumps({'records': len(recs),
                          'min_records_per_unit': MIN_RECORDS_PER_UNIT,
                          'min_ready_units': MIN_READY_UNITS,
                          'not_an_entity': list(NOT_AN_ENTITY),
                          'dimensions': rows,
                          'any_ready': bool(ready)}, indent=1))
        return 0 if ready else 1

    if not args.quiet:
        print('PER-ENTITY BASELINE READINESS -- item 51, report only')
        print('  %d records in the register' % len(recs))
        print('  BAR: %d records per unit, %d units minimum. A JUDGEMENT, '
              'pre-registered,' % (MIN_RECORDS_PER_UNIT, MIN_READY_UNITS))
        print('  not derived -- argue with it rather than inheriting it.')
        print('  NOT AN ENTITY, excluded by name: %s' % ', '.join(NOT_AN_ENTITY))
        print('')
        for r in rows:
            print('  %-18s %2d units  %3d records  largest %2d   %s'
                  % (r['dimension'], r['units'], r['records'], r['largest'],
                     r['verdict']))
            print('      %s' % r['why'])
            if r['excluded_records']:
                print('      %d record(s) excluded as a catch-all bucket, not '
                      'dropped silently' % r['excluded_records'])
            if r['ready_units']:
                print('      clears the record bar: %s'
                      % ', '.join('%s (%d)' % (u, r['tally'][u])
                                  for u in r['ready_units']))
            print('')
        print('  A BASELINE IS A RATE, SO BOTH BARS ARE REQUIRED. A dimension')
        print('  with enough records and no exposure denominator produces a')
        print('  COUNT wearing a rate, and the count is then driven by how much')
        print('  attention the entity got rather than by how defective it is.')
        print('  Waiting fixes a VOLUME failure and never a denominator one.')

    if ready:
        return finish([], [], quiet=args.quiet,
                      clean_line='\n  READY: %s'
                                 % ', '.join(r['dimension'] for r in ready))
    if not args.quiet:
        print('')
        print('  NO ENTITY IS READY. This is a measured NOT YET, not a refusal')
        print('  to look, and it is re-answered from the register every run.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
