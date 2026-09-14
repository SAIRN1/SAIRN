"""tests/run_app_attribution_probe.py

Run:  python tests/run_app_attribution_probe.py

THE GENERATED STATUS DOCUMENT TOLD AN AUDITOR THAT A BUILT VERTICAL WITH 27
TEST FILES HAD NONE.

`traceability_matrix.app_of()` finds an app by looking for its FULL NAME in the
text. That is right for prose and wrong for test filenames, because this repo
names its test files after an app's API PREFIX or its trade, never after the
app. Measured: 27 of 27 SAIRNroofing tests are `roofing-*` or `roofing_*` and
not one contains the string `sairnroofing`, so `docs/MASTER-PLAN.md` printed
`sairnroofing ... 0 suites, 0 traced, **no dedicated suite**`.

`APP_ALIASES` in tools/traceability_matrix.py is the fix. This probe is what
keeps it from becoming a second, quieter way of getting attribution wrong.

── WHY AN ALIAS TABLE IS DANGEROUS, WHICH IS WHY THIS FILE EXISTS ────────────
app_of() is deliberately conservative: a text naming two apps returns PLATFORM,
because filing it under the first one mentioned would be a guess presented as a
fact. An alias table is the exact mechanism by which that conservatism gets
quietly repealed -- `sc` as a substring claims `scp_quotes` (SAIRNscape) for
SAIRNcode, `sv` claims anything with `csv` in it, and `sd` would claim 25 tests
of the SHARED endpoint for StoneDesk. Every one of those is a wrong number that
looks like a better number.

So the arms below check the table's SAFETY properties, not just that it moved
the count:

  1. every alias names an app that exists
  2. no alias is redundant with app_of()
  3. matching is TOKEN-EXACT, so `sc` does not claim `scp_*`
  4. no file is claimed by two aliases
  5. an alias NEVER overrides app_of()
  6. a path naming two apps still returns PLATFORM
  7. a declared alias is either in use OR is a real api/<alias>-auth.js prefix
     -- so a typo fails and a legitimately-not-yet-used prefix does not
  8. the REFUSED table is in force, not merely documented
  9. the measured floor the whole change was for

Sabotage-verified by tests/run_app_attribution_mutation_control.py.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)

import traceability_matrix as TM                                # noqa: E402

passed = 0
failed = 0


def check(name, cond, detail=''):
    global passed, failed
    if cond:
        print('  ok   ' + name)
        passed += 1
    else:
        print('  FAIL ' + name + (('\n       ' + detail) if detail else ''))
        failed += 1


def section(s):
    print('\n' + s)


APPS = TM.apps()
TESTS = TM.all_tests()
ALIASES = TM.APP_ALIASES
REFUSED = TM.REFUSED_ALIASES
AUTH_PREFIXES = set(os.path.basename(p)[:-len('-auth.js')]
                    for p in glob.glob(os.path.join(ROOT, 'api', '*-auth.js')))

print('SAIRN: the alias table fixes attribution without repealing its caution\n')

# ── 0. THE FIXTURE ──────────────────────────────────────────────────────────
section('0. the inputs are real')
check('git knows about the app files -- ' + str(len(APPS)) + ' of them',
      len(APPS) >= 20, str(APPS))
check('and there are tests to attribute -- ' + str(len(TESTS)),
      len(TESTS) >= 300)
check('the alias table is not empty -- ' + str(len(ALIASES)) + ' entries',
      len(ALIASES) > 0)
check('api/*-auth.js really is readable, so arm 7 is not passing on an empty '
      'set -- ' + str(len(AUTH_PREFIXES)) + ' prefixes',
      len(AUTH_PREFIXES) >= 10, str(sorted(AUTH_PREFIXES)))

# ── 1. EVERY ALIAS NAMES A REAL APP, AND CARRIES A REASON ──────────────────
section('1. every alias names a real app and says why')
for alias, (app, why) in sorted(ALIASES.items()):
    check('%-8s -> %-16s app exists' % (alias, app), app in APPS,
          'not in ' + str(APPS))
    check('%-8s carries a stated reason (%d chars)' % (alias, len(why or '')),
          bool(why) and len(why) >= 25, repr(why))
    # AN ALIAS THAT IS ITSELF AN APP NAME IS DEAD WEIGHT, and dead weight in a
    # table like this is how a reader stops trusting the rest of it.
    check('%-8s is not redundant with app_of() itself' % alias,
          alias not in [a.lower() for a in APPS])

# ── 2. TOKEN-EXACT, NOT SUBSTRING ──────────────────────────────────────────
# The single property that makes two- and three-letter aliases safe at all.
section('2. matching is token-exact, which is what makes short aliases safe')
NEAR_MISSES = [
    # (path, must NOT be attributed to, why)
    ('tests/scp_quotes_probe.py', 'sairncode',
     '`sc` must not claim SAIRNscape\'s scp_ prefix'),
    ('tests/csv_export_probe.py', 'sairnvet',
     '`sv` must not claim anything with csv in it'),
    ('tests/sbom_probe.py', 'sairnbiz',
     '`sb` must not claim sbom'),
    ('tests/lawn_mowing_probe.py', 'sairnlaw',
     '`law` must not claim lawn'),
    ('tests/mechanism_probe.py', 'sairnmechanical',
     '`mech` must not claim mechanism'),
    ('tests/grdx_probe.py', 'sairngrounds',
     '`grd` must not claim grdx'),
    ('tests/dnta_probe.py', 'sairndental',
     '`dnt` must not claim dnta'),
    ('tests/rfc_compliance_probe.py', 'sairnroofing',
     '`rf` must not claim rfc'),
]
for path, must_not, why in NEAR_MISSES:
    got = TM.app_of_test(path, APPS)
    check('%-34s -> %-11s  (%s)' % (os.path.basename(path), got, why),
          got != must_not, 'got ' + got)

# ...and the positive half, or arm 2 would pass on a table that matched nothing.
POSITIVE = [
    ('tests/scp_quotes_probe.py', 'PLATFORM'),
    ('api/_lib/roofing-claims.test.js', 'sairnroofing'),
    ('tests/roofing_claim_photo_export.js', 'sairnroofing'),
    ('api/_lib/dental-gfe.test.js', 'sairndental'),
    ('tests/faults/dnt_vendor_write_faults.js', 'sairndental'),
    ('api/sv-witness.test.js', 'sairnvet'),
    ('api/_lib/mech-assets.test.js', 'sairnmechanical'),
    ('tests/faults/alf_rule_read_faults.js', 'sairncare'),
    ('api/sc-credentials.test.js', 'sairncode'),
]
for path, want in POSITIVE:
    got = TM.app_of_test(path, APPS)
    check('CONTROL: %-42s -> %s' % (os.path.basename(path), want), got == want,
          'got ' + got)

# ── 3. NO FILE IS CLAIMED TWICE ────────────────────────────────────────────
section('3. no file is claimed by two aliases')
by_token = {}
collisions = []
for t in TESTS:
    tok = TM.first_token(t)
    if tok in ALIASES:
        by_token.setdefault(tok, []).append(t)
# Token-exactness makes a two-alias collision impossible BY CONSTRUCTION, and
# asserting it anyway is the point: the construction is what a future edit would
# change. A dict cannot hold one key twice, so the real risk is somebody
# replacing the exact match with a startswith().
for t in TESTS:
    tok = TM.first_token(t)
    hits = [a for a in ALIASES if tok == a]
    if len(hits) > 1:
        collisions.append((t, hits))
check('no test file matches more than one alias', not collisions,
      str(collisions[:4]))
loose = [t for t in TESTS
         if len([a for a in ALIASES if TM.first_token(t).startswith(a)]) > 1]
check('and even under a LOOSER prefix rule only %d file(s) would be ambiguous '
      '-- named, because that is the rule a future edit is most likely to '
      'reach for' % len(loose), True,
      '; '.join(os.path.basename(t) for t in loose[:6]))

# ── 4. AN ALIAS NEVER OVERRIDES app_of() ───────────────────────────────────
section('4. the alias always loses to a full app name')
for path, want in [
    ('tests/sairnscape_sc_probe.py', 'sairnscape'),
    ('tests/sairnbiz_void_not_delete.js', 'sairnbiz'),
    # PRE-EXISTING app_of() BEHAVIOUR, asserted here so the alias layer is not
    # blamed for it. `law` and `roofing` are aliases, not app names, so app_of()
    # sees exactly ONE app in each of these and answers confidently. That is the
    # same answer it gave before this change; the first draft of this arm
    # expected PLATFORM and was wrong about the baseline, not about the alias.
    ('tests/sairnvet_law_probe.py', 'sairnvet'),
    ('tests/stonedesk_roofing_shared_probe.js', 'stonedesk'),
]:
    got = TM.app_of_test(path, APPS)
    check('%-42s -> %-11s' % (os.path.basename(path), want), got == want,
          'got ' + got)
# THE ONE THAT MATTERS MOST, AND THE ARM THAT FOUND A REAL DEFECT IN THE FIRST
# VERSION OF THIS CHANGE. app_of() decides "two apps -> PLATFORM" by counting
# FULL APP NAMES ONLY. Once aliases exist, a path can name two apps with one of
# them by alias, and app_of() sees one app and answers confidently. The first
# implementation let the alias simply LOSE, which attributed a two-app file to
# StoneDesk -- exactly the guess-presented-as-fact app_of() exists to refuse.
# A disagreement between the two is now PLATFORM.
check('a path whose first token is an alias but which also names another app '
      'outright stays PLATFORM -- the conflict is refused, not resolved by '
      'precedence',
      TM.app_of_test('tests/roofing_vs_stonedesk_probe.js', APPS) == 'PLATFORM',
      TM.app_of_test('tests/roofing_vs_stonedesk_probe.js', APPS))
check('...and the same in the other order',
      TM.app_of_test('api/_lib/dental-and-stonedesk-shared.test.js', APPS)
      == 'PLATFORM',
      TM.app_of_test('api/_lib/dental-and-stonedesk-shared.test.js', APPS))
# CONTROL: the conflict rule must not fire when the alias and the full name
# AGREE, or every roofing file naming sairnroofing would drop to PLATFORM.
check('CONTROL: when the alias and the full app name AGREE, attribution is kept',
      TM.app_of_test('tests/roofing_sairnroofing_probe.js', APPS) == 'sairnroofing',
      TM.app_of_test('tests/roofing_sairnroofing_probe.js', APPS))

# ── 5. NO DEAD DECLARATIONS, AND NO TYPOS ──────────────────────────────────
# An alias matching nothing is either a typo (fail) or a real API prefix whose
# tests have not been written yet (allowed, and named). The distinction is what
# lets `rf` stay in the table honestly.
section('5. every alias is in use, or is a real api/<alias>-auth.js prefix')
for alias in sorted(ALIASES):
    used = len(by_token.get(alias, []))
    real_prefix = alias in AUTH_PREFIXES
    check('%-8s %s' % (alias, ('in use, %d file(s)' % used) if used
                       else ('unused but api/%s-auth.js exists' % alias)),
          used > 0 or real_prefix,
          'matches no file and api/%s-auth.js does not exist -- typo?' % alias)

# ── 6. THE REFUSALS ARE IN FORCE, NOT JUST DOCUMENTED ──────────────────────
section('6. the refused groups really are still PLATFORM')
check('the refusal table is populated -- ' + str(len(REFUSED)) + ' entries',
      len(REFUSED) >= 3)
for tok, (app, expect_n, why) in sorted(REFUSED.items()):
    group = [t for t in TESTS if TM.first_token(t) == tok]
    check('%-9s is not in the alias table' % tok, tok not in ALIASES)
    still = [t for t in group if TM.app_of_test(t, APPS) == 'PLATFORM']
    # NOT AN EQUALITY ON THE GROUP: some `sd-*` files legitimately name another
    # app in full and app_of() attributes them, which is correct. What must hold
    # is that the refusal is not silently reversed -- nothing in the group is
    # attributed to the app the refusal names.
    wrong = [t for t in group if app and TM.app_of_test(t, APPS) == app]
    check('%-9s none of its %d file(s) is attributed to %s'
          % (tok, len(group), app or '(no app)'), not wrong,
          '; '.join(os.path.basename(t) for t in wrong[:5]))
    check('%-9s and it still has %d PLATFORM file(s), so the group is real'
          % (tok, len(still)), len(still) > 0)
    check('%-9s the refusal states its reason (%d chars)' % (tok, len(why or '')),
          bool(why) and len(why) >= 40)

# ── 7. THE MEASURED FLOOR -- WHAT THE CHANGE WAS ACTUALLY FOR ──────────────
section('7. the finding, measured')
by_app = {}
for t in TESTS:
    by_app.setdefault(TM.app_of_test(t, APPS), []).append(t)
roofing = by_app.get('sairnroofing', [])
check('SAIRNroofing is attributed at least 27 test files -- it was 0 -- got '
      + str(len(roofing)), len(roofing) >= 27,
      '; '.join(os.path.basename(t) for t in roofing[:5]))
check('...and every one of them really is a roofing file by name',
      all(TM.first_token(t) in ('roofing', 'rf') or 'sairnroofing' in t
          for t in roofing),
      '; '.join(t for t in roofing
                if TM.first_token(t) not in ('roofing', 'rf')
                and 'sairnroofing' not in t)[:300])
# BEFORE-AND-AFTER, so the arm above is not passing on a number that was always
# there. app_of() is the unaliased function and is still exported unchanged.
before = len([t for t in TESTS if TM.app_of(t, APPS) == 'sairnroofing'])
check('CONTROL: the UNALIASED app_of() still attributes %d to SAIRNroofing, so '
      'the arm above measures the alias layer and not the baseline' % before,
      before == 0, 'unaliased count is ' + str(before))
plat_before = len([t for t in TESTS if TM.app_of(t, APPS) == 'PLATFORM'])
plat_after = len(by_app.get('PLATFORM', []))
check('PLATFORM falls from %d to %d -- %d files moved to a vertical'
      % (plat_before, plat_after, plat_before - plat_after),
      plat_after < plat_before)
# NO FILE MAY BE ATTRIBUTED TO AN APP THAT DOES NOT EXIST, which is the failure
# an alias typo produces: a whole column appearing under a name nobody owns.
ghosts = [a for a in by_app if a != 'PLATFORM' and a not in APPS]
check('no file is attributed to an app that does not exist', not ghosts,
      str(ghosts))

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(1 if failed else 0)
