"""The removal-path check must catch what it exists to catch.

    python tests/run_removal_path_probe.py

A checker that has only ever returned CLEAN is not evidence. This drives the
real `tools/removal_path_check.py` against throwaway fixture repos in a temp
directory -- never against this repo.

The arm that matters most is section 6. A comment block in these registries
often covers SEVERAL resources and distinguishes between them -- SAIRNroofing's
says *"rf_claims is a MUTABLE claim record ...; rf_claim_photos is APPEND-ONLY
tagged evidence"*. The first version of the append-only reader attributed such a
block wholesale, which labelled `rf_claims` -- a money record its own comment
calls MUTABLE -- as append-only and SILENTLY EXEMPTED it. **A false exemption is
worse than a false finding: one gets read and argued with, the other never
appears.** That arm asserts the mutable sibling still fails.

Also covered: a NEW resource with no removal verb must fail (the whole point of
a grandfathered baseline); a removal verb, a single-row collection, and a real
single-resource append-only label must each clear it; and a MISSING baseline
file must turn every stuck resource into a finding rather than pass quietly.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'removal_path_check.py')

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  ok    %s' % label)
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r'
          % (label, expected, actual))
    return False


REG_TEMPLATE = """// fixture registry
const RESOURCE_NAMES = %(names)s;
const OWNER_BY_RESOURCE = %(owner)s;
const EXTRA_ACTIONS = %(extra)s;
module.exports = { RESOURCE_NAMES, OWNER_BY_RESOURCE, EXTRA_ACTIONS };
"""


def build(tmp, names, extra, sd_data, app_js, baseline=None):
    """A throwaway repo just real enough: the tool, a registry, a handler."""
    for d in ('tools', os.path.join('api', '_resources')):
        os.makedirs(os.path.join(tmp, d), exist_ok=True)
    shutil.copy(TOOL, os.path.join(tmp, 'tools', 'removal_path_check.py'))
    io.open(os.path.join(tmp, 'api', '_resources', 'index.js'), 'w',
            encoding='utf-8').write(REG_TEMPLATE % {
                'names': json.dumps(names),
                'owner': json.dumps({n: 'fixtureapp' for n in names}),
                'extra': json.dumps(extra)})
    io.open(os.path.join(tmp, 'api', '_resources', 'fixtureapp.js'), 'w',
            encoding='utf-8').write(app_js)
    io.open(os.path.join(tmp, 'api', 'sd-data.js'), 'w',
            encoding='utf-8').write(sd_data)
    if baseline is not None:
        io.open(os.path.join(tmp, 'tools', 'removal_path_baseline.json'), 'w',
                encoding='utf-8').write(json.dumps(
                    {'generated': 'fixture', 'grandfathered': baseline}))


def run(tmp, *args):
    r = subprocess.run([sys.executable,
                        os.path.join(tmp, 'tools', 'removal_path_check.py')]
                       + list(args), cwd=tmp, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


tmp = tempfile.mkdtemp(prefix='removalpath-')
n = [0]


def case(name, **kw):
    n[0] += 1
    d = os.path.join(tmp, '%02d-%s' % (n[0], name))
    os.makedirs(d)
    build(d, **kw)
    return run(d)


KEYED = ("if (resource === '%s' && action === 'write') {\n"
         "  await fetch(rest('%s?on_conflict=license_hash,thing_id'),"
         " { method: 'POST' });\n}\n")
SINGLE = ("if (resource === '%s' && action === 'write') {\n"
          "  await fetch(rest('%s?on_conflict=license_hash'),"
          " { method: 'POST' });\n}\n")
APP = "module.exports = { app: 'fixtureapp', resources: [\n%s\n] };\n"

# ── 1. the control: one keyed resource, grandfathered ─────────────────────
rc, out = case('clean',
               names=['a_thing'], extra={},
               sd_data=KEYED % ('a_thing', 'a_thing'),
               app_js=APP % "  'a_thing',",
               baseline={'a_thing': 'grandfathered fixture'})
check('a grandfathered keyed resource is CLEAN', rc, 0)
check('and it says so', 'CLEAN' in out, True)

# ── 2. a NEW resource with no removal verb -- the whole point ─────────────
rc, out = case('new',
               names=['a_thing', 'b_new'], extra={},
               sd_data=(KEYED % ('a_thing', 'a_thing')) + (KEYED % ('b_new', 'b_new')),
               app_js=APP % "  'a_thing',\n  'b_new',",
               baseline={'a_thing': 'grandfathered fixture'})
check('a NEW resource with no removal path FAILS', rc, 1)
check('and it is named', 'b_new' in out, True)
check('and the grandfathered one is NOT re-reported', out.count('a_thing') == 0, True)

# ── 3. a removal verb clears it ───────────────────────────────────────────
rc, out = case('hasverb',
               names=['a_thing', 'b_new'], extra={'b_new': ['delete']},
               sd_data=(KEYED % ('a_thing', 'a_thing')) + (KEYED % ('b_new', 'b_new')),
               app_js=APP % "  'a_thing',\n  'b_new',",
               baseline={'a_thing': 'grandfathered fixture'})
check('a new resource declaring delete is CLEAN', rc, 0)
rc, out = case('hasverb-soft',
               names=['a_thing', 'b_new'], extra={'b_new': ['soft_delete']},
               sd_data=(KEYED % ('a_thing', 'a_thing')) + (KEYED % ('b_new', 'b_new')),
               app_js=APP % "  'a_thing',\n  'b_new',",
               baseline={'a_thing': 'grandfathered fixture'})
check('soft_delete counts as a removal path too', rc, 0)

# ── 4. a single-row collection needs no delete verb ───────────────────────
rc, out = case('singlerow',
               names=['a_thing', 'b_coll'], extra={},
               sd_data=(KEYED % ('a_thing', 'a_thing')) + (SINGLE % ('b_coll', 'b_coll')),
               app_js=APP % "  'a_thing',\n  'b_coll',",
               baseline={'a_thing': 'grandfathered fixture'})
check('a single-row collection is CLEAN without a delete verb', rc, 0)
check('and the shape is reported as single-row', 'single-row' in out, True)

# ── 5. a real single-resource APPEND-ONLY label clears it ─────────────────
rc, out = case('appendonly',
               names=['a_thing', 'b_evidence'], extra={},
               sd_data=(KEYED % ('a_thing', 'a_thing'))
                       + (KEYED % ('b_evidence', 'b_evidence')),
               app_js=APP % ("  'a_thing',\n"
                             "  // Signed evidence. APPEND-ONLY: a correction is a second row.\n"
                             "  'b_evidence',"),
               baseline={'a_thing': 'grandfathered fixture'})
check('a single-resource APPEND-ONLY comment clears it', rc, 0)

# ── 6. THE FALSE-EXEMPTION ARM. A shared comment must not label the sibling
#       it explicitly calls MUTABLE. This is the real SAIRNroofing shape.
rc, out = case('mutable-sibling',
               names=['a_thing', 'b_claims', 'b_photos'], extra={},
               sd_data=(KEYED % ('a_thing', 'a_thing'))
                       + (KEYED % ('b_claims', 'b_claims'))
                       + (KEYED % ('b_photos', 'b_photos')),
               app_js=APP % ("  'a_thing',\n"
                             "  // b_claims is a MUTABLE claim record (it evolves over a\n"
                             "  // 45-90 day lifecycle); b_photos is APPEND-ONLY tagged evidence.\n"
                             "  'b_claims',\n"
                             "  'b_photos',"),
               baseline={'a_thing': 'grandfathered fixture'})
check('the MUTABLE sibling under a shared comment still FAILS', rc, 1)
check('and it is the mutable one that is named', 'b_claims' in out, True)
check('and the APPEND-ONLY one is NOT named', 'b_photos' in out, False)

# ── 7. a MISSING baseline must not pass quietly ───────────────────────────
rc, out = case('nobaseline',
               names=['a_thing'], extra={},
               sd_data=KEYED % ('a_thing', 'a_thing'),
               app_js=APP % "  'a_thing',",
               baseline=None)
check('with NO baseline file every stuck resource is a finding', rc, 1)
check('and it is named rather than silently passed', 'a_thing' in out, True)

# ── 8. an unreadable registry is a hard error, not a clean run ────────────
n[0] += 1
d = os.path.join(tmp, '%02d-badreg' % n[0])
os.makedirs(d)
build(d, names=['a_thing'], extra={}, sd_data=KEYED % ('a_thing', 'a_thing'),
      app_js=APP % "  'a_thing',", baseline={'a_thing': 'x'})
io.open(os.path.join(d, 'api', '_resources', 'index.js'), 'w',
        encoding='utf-8').write('this is not javascript {{{\n')
rc, out = run(d)
check('a registry that will not load is an ERROR, not CLEAN', rc != 0, True)
check('and it says why', 'could not load' in out, True)

# ── 9. the criticality tier is READ, and a missing register is not a tier ─
n[0] += 1
d = os.path.join(tmp, '%02d-tiers' % n[0])
os.makedirs(os.path.join(d, 'docs'))
build(d, names=['a_money', 'b_pref', 'c_absent'], extra={},
      sd_data=(KEYED % ('a_money', 'a_money')) + (KEYED % ('b_pref', 'b_pref'))
              + (KEYED % ('c_absent', 'c_absent')),
      app_js=APP % "  'a_money',\n  'b_pref',\n  'c_absent',",
      baseline={'a_money': 'x', 'b_pref': 'x', 'c_absent': 'x'})
io.open(os.path.join(d, 'docs', 'CRITICALITY-TIERS.md'), 'w',
        encoding='utf-8').write(
    '| Resource | Tier | Worst | Evidence |\n|---|---|---|---|\n'
    '| `a_money` | **A** | money billed wrongly | fixture |\n'
    '| `b_pref` | C | a preference resets | fixture |\n')
rc, out = run(d, '--burn-down')
check('tiers are read from the register', rc, 0)
check('and the counts are reported', 'A=1' in out and 'C=1' in out, True)
check('a resource ABSENT from the register is UNTIERED, not mis-tiered',
      'UNTIERED=1' in out, True)
check('and Tier A is listed FIRST in the burn-down',
      out.index('Tier A') < out.index('Tier C'), True)

n[0] += 1
d2 = os.path.join(tmp, '%02d-notiers' % n[0])
os.makedirs(d2)
build(d2, names=['a_money'], extra={}, sd_data=KEYED % ('a_money', 'a_money'),
      app_js=APP % "  'a_money',", baseline={'a_money': 'x'})
rc, out = run(d2, '--burn-down')
check('a MISSING tier register does not crash and does not invent a tier',
      (rc, 'UNTIERED=1' in out), (0, True))

# ── 10. and the REAL repo is clean, since that is what it is for ──────────
r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True)
check('the real SAIRN baseline currently accounts for every one', r.returncode, 0)

print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- a new resource the product cannot delete from cannot be '
      'added silently.')
