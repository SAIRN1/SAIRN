"""Does the drift sweep find the two defects it was built from, and refuse the ones it should?

    python tests/run_pinned_list_drift_probe.py

THE ARMS THAT MATTER ARE SECTIONS 2 AND 3, and they are the pair. A detector for
a defect shape is worth nothing until it has been shown to find the REAL
instances -- so section 2 replays the two that were found by hand, verbatim, and
requires the tool to classify both as PARTIAL-TIER-A. And a detector that says
yes to everything is worth less than none, so section 3 requires it to stay
quiet on a DERIVED list, on a list that already covers the whole population, and
on a list of names that are not resources at all.

SECTION 4 IS THE FAIL-CLOSED HALF. The tool's whole answer depends on parsing
docs/CRITICALITY-TIERS.md, and the obvious failure of a parse change is an EMPTY
Tier A set -- which would make every list look like a complete cover and print
nothing. That is PR 1.11's defect in the one place it would be invisible, so an
empty parse must exit 2.

NOTHING HERE WRITES A TRACKED FILE. Every fixture is a string handed to
scan_text(), which is split out of scan() for exactly that reason -- a probe that
must write into the repo to test a scanner is a probe that can lose somebody
else's work on a branch four sessions share.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import pinned_list_drift_check as d                              # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


print('\n1. the fixtures are real -- the registry and register both load')
owner, resources = d.registry()
by_app, all_tier_a = d.tier_a_by_app(owner)
check('the registry yields resources (%d)' % len(resources), len(resources) > 300, len(resources))
check('the register yields Tier A rows (%d)' % len(all_tier_a), len(all_tier_a) > 50, len(all_tier_a))
sc = by_app.get('sairncode', set())
check('sairncode has SEVEN Tier A resources, which is the number the '
      'hand-written gate got wrong', len(sc) == 7, sorted(sc))


def classify_one(text, rel='api/fixture.js'):
    rows = d.scan_text(rel, text, resources, owner)
    if not rows:
        return None, []
    r = rows[0]
    return d.classify(r, by_app, resources, owner)


print('\n2. it finds BOTH real defects, replayed verbatim')
# The literal that shipped on 2026-09-14 and left sc_denial_events accepting a
# write from the licence key alone until 2026-09-15.
GATE_OF_SIX = ("const SC_TIER_A_WRITE_GATED = [\n"
               "  'sc_ar', 'sc_claims', 'sc_revenue', 'sc_denial', 'sc_compliance',\n"
               "  'sc_credential_scope'\n];")
cls, missing = classify_one(GATE_OF_SIX)
check('SC_TIER_A_WRITE_GATED as it shipped is PARTIAL-TIER-A',
      cls == 'PARTIAL-TIER-A', '%s %s' % (cls, missing))
check('...and it names sc_denial_events as the one missing',
      missing == ['sc_denial_events'], missing)

# The probe's own copy of the same list, which survived the handler fix by a day.
PROBE_SIX = ("    SIX = ['sc_ar', 'sc_claims', 'sc_revenue', 'sc_denial', "
             "'sc_compliance',\n           'sc_credential_scope']")
cls, missing = classify_one(PROBE_SIX, 'tools/fixture_probe.py')
check('the live probe\'s own SIX is PARTIAL-TIER-A too -- the same list, one '
      'file over, and the reason a green run covered six of seven',
      cls == 'PARTIAL-TIER-A' and missing == ['sc_denial_events'],
      '%s %s' % (cls, missing))

print('\n3. CONTROLS -- it stays quiet on the things it must not flag')
derived = "const SC_TIER_A_WRITE_GATED = SC_TIER_A_SOFT_DELETE_ONLY;"
cls, _ = classify_one(derived)
check('a DERIVED list produces no row at all -- nothing to drift', cls is None, cls)

full = "const ALL = [" + ', '.join("'%s'" % n for n in sorted(sc)) + "];"
cls, missing = classify_one(full)
check('a list covering the whole Tier A set is COVERS-TIER-A, not a finding',
      cls == 'COVERS-TIER-A', '%s %s' % (cls, missing))

notres = "const ROLES = ['admin', 'biller', 'auditor', 'coder'];"
cls, _ = classify_one(notres)
check('a list of ROLES produces no row -- it is out of scope and says so',
      cls is None, cls)

pair = "const TWO = ['sc_ar', 'sc_claims'];"
cls, _ = classify_one(pair)
check('a list of TWO produces no row -- a pair is not a population',
      cls is None, cls)

mixed = "const M = ['sc_ar', 'dnt_charges', 'law_invoices'];"
cls, _ = classify_one(mixed)
check('a cross-app list is MIXED, not a per-app partial', cls == 'MIXED', cls)

partly = "const P = ['sc_ar', 'sc_claims', 'not_a_resource'];"
cls, _ = classify_one(partly)
check('a list that is only PARTLY resource names produces no row', cls is None, cls)

print('\n4. FAIL CLOSED -- an empty Tier A parse is 2, never "nothing to report"')
real = d.REGISTER
tmp = os.path.join(REPO, 'tools', '__probe_empty_register.md')
try:
    io.open(tmp, 'w', encoding='utf-8').write('# no table here\n')
    r = subprocess.run([sys.executable, '-c',
                        'import sys; sys.path.insert(0, %r);'
                        'import pinned_list_drift_check as d;'
                        'd.REGISTER = %r;'
                        'sys.exit(d.main())'
                        % (os.path.join(REPO, 'tools'), tmp)],
                       cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    check('an empty register exits 2, not 0', r.returncode == 2,
          'exit %s\n%s' % (r.returncode, (r.stdout or r.stderr)[:300]))
    check('...and says WHY, naming the empty-set trap',
          'ZERO Tier A rows' in (r.stderr or '') or 'ZERO Tier A rows' in (r.stdout or ''),
          (r.stderr or r.stdout)[:300])
finally:
    d.REGISTER = real
    try:
        os.remove(tmp)
    except OSError:
        pass
check('the temporary fixture is gone', not os.path.exists(tmp), tmp)

print('\n5. the real repo, and the finding it already produced')
r = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                 'pinned_list_drift_check.py')],
                   cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
check('it runs on the real repo and exits 0 (report-only)', r.returncode == 0,
      r.stderr[:300])
out = r.stdout
check('it reports a non-empty set of literal lists -- a zero here would mean '
      'the array pattern had stopped matching, not that the platform was clean',
      'literal lists found            : 0' not in out, out[:200])
check('sc_tier_a_write_gate_live_probe.py is NO LONGER listed -- its SIX was '
      'the first row this tool ever printed and it is derived now',
      'sc_tier_a_write_gate_live_probe' not in out,
      [ln for ln in out.split('\n') if 'sc_tier_a' in ln])
check('the output states it is a READ-LIST rather than a score',
      'not a score' in out or 'correct length is not zero' in out, out[-400:])

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
