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

# ── 11. THE BRANCH REGION IS BOUNDED BY THE NEXT BRANCH, NOT BY A NUMBER ──
# shapes() used to read `api[m.start():m.start() + 2500]`. That arbitrary
# window was wrong in BOTH directions against the real api/sd-data.js on
# 2026-09-12, and the two failures need separate arms because they fail in
# opposite ways. The dangerous one is B: it produced a SILENT EXEMPTION.
def pad(n_chars):
    return '// ' + ('x' * 70) + '\n' * 0 + ('\n// ' + 'x' * 70) * (n_chars // 74)


# A. TOO SMALL. sd_public_shop's own write sits at offset +2499 and the string
#    SINGLE_Q matches runs past 2500, so it missed BY ONE CHARACTER and the
#    resource came back UNRESOLVED -- a false entry in a 321-item queue.
FAR_SINGLE = ("if (resource === '%s' && action === 'write') {\n"
              + pad(3000) + "\n"
              "  await fetch(rest('%s?on_conflict=license_hash'),"
              " { method: 'POST' });\n}\n")
n[0] += 1
_d = os.path.join(tmp, '%02d-farwrite' % n[0])
os.makedirs(_d)
build(_d, names=['a_thing', 'b_far'], extra={},
      sd_data=(KEYED % ('a_thing', 'a_thing')) + (FAR_SINGLE % ('b_far', 'b_far')),
      app_js=APP % "  'a_thing',\n  'b_far',",
      baseline={'a_thing': 'grandfathered fixture'})
rc, out = run(_d, '--full')
check('11A a write 3000 chars into its own branch is still read',
      'b_far' in out and 'single-row' in out.split('b_far')[1][:40], True)
check('11A and it is therefore NOT a finding', rc, 0)

# B. TOO LARGE, AND THIS IS THE ONE THAT HID A REAL DEFECT. msb_food_cost_log's
#    first dispatch is READ-ONLY; 2,322 chars later, inside a DIFFERENT branch,
#    msb_sale_hours does a genuine single-row write. SINGLE_Q is tested first
#    and searches the whole window, so the neighbour's write won -- and a TIER A
#    resource was silently exempted from the stuck list by another resource's
#    code. A false exemption never appears anywhere to be argued with.
READ_ONLY = ("if (resource === '%s' && action === 'read') {\n"
             "  await fetch(rest('%s?license_hash=eq.' + enc(h)));\n}\n")
n[0] += 1
_d = os.path.join(tmp, '%02d-neighbour-single' % n[0])
os.makedirs(_d)
build(_d, names=['a_thing', 'b_log', 'c_hours'], extra={},
      sd_data=(KEYED % ('a_thing', 'a_thing'))
              + (READ_ONLY % ('b_log', 'b_log'))
              + (SINGLE % ('c_hours', 'c_hours'))
              + (KEYED % ('b_log', 'b_log')),
      app_js=APP % "  'a_thing',\n  'b_log',\n  'c_hours',",
      baseline={'a_thing': 'grandfathered fixture'})
rc, out = run(_d, '--full')
check('11B a read-only branch does NOT inherit the next branch\'s single-row '
      'write', 'single-row' in out.split('b_log')[1][:40], False)
check('11B and the resource is reported as the finding it really is', rc, 1)
check('11B and it is named', 'b_log' in out.split('FINDING')[-1], True)
check('11B while the genuine single-row neighbour is still exempt',
      'c_hours' in out.split('FINDING')[-1], False)

# C. The same over-reach in the KEYED direction, and the honest answer is to
#    say NOTHING rather than to borrow. sd_quote_requests' branch holds no
#    on_conflict at all -- staff PATCH by id and the INSERT lives in
#    api/stonedesk-public.js, a different file -- and the first on_conflict
#    within 2500 chars belonged to sd_crm, the NEXT branch. A resource with no
#    readable write of its own must come back UNRESOLVED, which this tool's own
#    header says is "not a finding and not a pass", NOT keyed on a neighbour's
#    id column. Raising the window instead would have made that wrong answer
#    more confident rather than less.
READ_ONLY_ONLY = ("if (resource === '%s' && action === 'read') {\n"
                  "  await fetch(rest('%s?license_hash=eq.' + enc(h)));\n}\n")
n[0] += 1
_d = os.path.join(tmp, '%02d-neighbour-keyed' % n[0])
os.makedirs(_d)
build(_d, names=['a_noread', 'b_keyed'], extra={},
      sd_data=(READ_ONLY_ONLY % ('a_noread', 'a_noread'))
              + (KEYED % ('b_keyed', 'b_keyed')),
      app_js=APP % "  'a_noread',\n  'b_keyed',",
      baseline={'a_noread': 'x', 'b_keyed': 'x'})
rc, out = run(_d, '--full')
_row_a = [l for l in out.splitlines() if ' a_noread ' in l]
check('11C a branch with no write of its own says UNRESOLVED, it does not '
      "borrow the next branch's shape",
      len(_row_a) == 1 and 'UNRESOLVED' in _row_a[0], True)
check('11C and the neighbour is still read correctly',
      any(' b_keyed ' in l and 'keyed' in l for l in out.splitlines()), True)

# D. The grouping that makes the bound safe. `resource === 'a' || resource ===
#    'b'` is ONE dispatch -- five such pairs exist in the real file. Without
#    grouping they would bound each other at zero length and BOTH come back
#    UNRESOLVED, which is a regression dressed as caution. Asserted on the two
#    resource ROWS, not on the word appearing anywhere: the summary prints
#    "shape UNRESOLVED : 0" on every run, so a bare substring test passes on
#    the header and proves nothing.
PAIR_BRANCH = ("if (resource === 'a_left' || resource === 'b_right') {\n"
               "  await fetch(rest('t?on_conflict=license_hash,thing_id'),"
               " { method: 'POST' });\n}\n")
n[0] += 1
_d = os.path.join(tmp, '%02d-pairdispatch' % n[0])
os.makedirs(_d)
build(_d, names=['a_left', 'b_right'], extra={}, sd_data=PAIR_BRANCH,
      app_js=APP % "  'a_left',\n  'b_right',",
      baseline={'a_left': 'x', 'b_right': 'x'})
rc, out = run(_d, '--full')
_rows = [l for l in out.splitlines() if ' a_left ' in l or ' b_right ' in l]
check('11D both halves of a shared dispatch are classified keyed',
      len(_rows) == 2 and all('keyed' in l for l in _rows), True)

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
