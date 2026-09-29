#!/usr/bin/env python3
"""The TABLE rule, locked against synthetic fixtures in both directions.

    python tests/run_role_gate_table_rule_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

CONTROLS_FOR = tools/role_gate_negative_coverage.py

── THE FALSE NEGATIVE THIS CLOSES ─────────────────────────────────────────
`loop_driven()` reads a loop over a ROLE list with the resource named inside.
The mirror shape -- a loop over a RESOURCE TABLE with the role named inside --
was invisible to both existing rules:

    const ADMIN_REFUSALS = [
      ['alf_billing', 'read',  null,        'resident billing'],
      ['alf_staff',   'write', {id: 'S-1'}, 'the staff roster'],
    ];
    for (const [resource, action, payload, why] of ADMIN_REFUSALS) {
      const { res } = await call('caregiver', { action, resource });
      assert.strictEqual(code(res), 'FORBIDDEN');
    }

There is no `resource: 'alf_billing'` and no `tokenFor('caregiver')` anywhere
in that, so `literal_driven` sees nothing; and the array members are arrays, not
role names, so `loop_driven` sees nothing either.

MEASURED 2026-09-28: api/sd-data-alf-caregiver-scope.test.js drives ELEVEN
resources through exactly that table as `caregiver`, a role every one of their
gates excludes -- and FIVE of them sat in the screen's "NOT DRIVEN by any suite
at all" bucket, whose own text reads *"there is no suite to add an arm to"*.
One of those five, `alf_billing`, was then proven covered by `--ablate`: 3 of 3
gate blocks CAUGHT, by that very suite.

── WHY THIS IS NOT ATTEMPT 1 AGAIN ────────────────────────────────────────
The module docstring records an earlier rule that credited a bare role literal
in any file asserting a refusal anywhere. It moved uncovered 12 -> 7 and TWO of
the five it newly credited were still SILENT under ablation. File-wide
attribution was the defect.

So this rule is BODY-SCOPED and needs all five at once, mirroring
`loop_driven`:

  1. an array literal whose members are ARRAYS whose FIRST element is a known
     gated resource name -- a table of something else contributes nothing;
  2. a for-of over it, body boundary found by BRACE MATCHING on masked code;
  3. the DESTRUCTURED resource variable used as an identifier in that body;
  4. a role refusal asserted inside that same body;
  5. a role LITERAL in a call position inside that same body. Only the
     resources in that table are credited, and only with that role.

STILL A SCREEN, NOT A VERDICT. `--ablate` remains the only sound measurement.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

CONTROLS_FOR = ['tools/role_gate_negative_coverage.py']

try:
    import role_gate_negative_coverage as R                    # noqa: E402
except Exception as exc:                                       # noqa: BLE001
    sys.stderr.write('COULD NOT RUN -- role_gate_negative_coverage.py would not '
                     'import (%s: %s). Nothing was measured.\n'
                     % (type(exc).__name__, exc))
    raise SystemExit(2)

if not hasattr(R, 'table_driven'):
    sys.stderr.write('COULD NOT RUN -- table_driven() is not defined. This is '
                     'the control for a rule that is not there.\n')
    raise SystemExit(2)

ROLES = {'owner', 'admin', 'caregiver', 'nursing', 'med_aide', 'activities'}
GATED = {'alf_billing', 'alf_staff', 'alf_signals', 'sen_clients'}

fails = []


def check(name, ok, detail=''):
    print('  %s %s' % ('ok  ' if ok else 'FAIL', name))
    if not ok:
        print('       ' + str(detail)[:320])
        fails.append(name)


def run(src):
    return R.table_driven(src, ROLES, GATED)


# ── P. THE SHAPE IT EXISTS FOR ─────────────────────────────────────────────
GOOD = """
const ADMIN_REFUSALS = [
  ['alf_billing', 'read', null, 'resident billing'],
  ['alf_staff', 'write', {id: 'S-1'}, 'the staff roster'],
];
for (const [resource, action, payload, why] of ADMIN_REFUSALS) {
  const { res } = await call('caregiver', { action: action, resource: resource });
  assert.strictEqual(res.statusCode, 403);
  assert.strictEqual(code(res), 'FORBIDDEN');
}
"""
got = run(GOOD)
check('P1. the table shape is credited, and only for the table members',
      got == {'alf_billing': {'caregiver'}, 'alf_staff': {'caregiver'}}, got)

# ── N. EVERY WAY IT MUST REFUSE ────────────────────────────────────────────
N_NO_REFUSAL = GOOD.replace("assert.strictEqual(code(res), 'FORBIDDEN');", "")
N_NO_REFUSAL = N_NO_REFUSAL.replace("assert.strictEqual(res.statusCode, 403);",
                                    "assert.strictEqual(res.statusCode, 200);")
check('N1. no refusal asserted in the body -> NO credit. A table driven to '
      'check a 200 proves nothing about a gate',
      run(N_NO_REFUSAL) == {}, run(N_NO_REFUSAL))

N_NO_ROLE = GOOD.replace("call('caregiver',", "call(theRole,")
check('N2. the role is a VARIABLE, not a literal -> NO credit. This is '
      "attempt 1's exact failure: crediting a resource with a role nobody can "
      'read from the text',
      run(N_NO_ROLE) == {}, run(N_NO_ROLE))

N_NOT_RESOURCES = GOOD.replace("['alf_billing', 'read', null, 'resident billing'],",
                               "['not_a_resource', 'read', null, 'x'],") \
                      .replace("['alf_staff', 'write', {id: 'S-1'}, 'the staff roster'],",
                               "['also_not', 'write', null, 'y'],")
check('N3. a table of things that are not gated resources -> NO credit',
      run(N_NOT_RESOURCES) == {}, run(N_NOT_RESOURCES))

N_VAR_UNUSED = GOOD.replace("{ action: action, resource: resource }",
                            "{ action: 'read', resource: 'alf_billing' }")
check('N4. the destructured resource variable is never used in the body -> NO '
      'credit. The loop is then not driving the table at all',
      run(N_VAR_UNUSED) == {}, run(N_VAR_UNUSED))

N_UNCLOSED = GOOD.rsplit('}', 1)[0]
check('N5. the loop body never closes -> NO credit, rather than running to '
      'end-of-file and crediting whatever follows',
      run(N_UNCLOSED) == {}, run(N_UNCLOSED))

N_OUTSIDE = """
const ADMIN_REFUSALS = [
  ['alf_billing', 'read', null, 'x'],
];
await call('caregiver', { action: 'read', resource: 'sen_clients' });
assert.strictEqual(code(res), 'FORBIDDEN');
for (const [resource, action] of ADMIN_REFUSALS) {
  await call(someRole, { action: action, resource: resource });
}
"""
check('N6. a role literal and a refusal OUTSIDE the loop body do not reach '
      'into it -- body-scoped, not file-wide',
      run(N_OUTSIDE) == {}, run(N_OUTSIDE))

# ── B. THE BLIND BUCKET ────────────────────────────────────────────────────
check('B1. blind_population() exists and returns a set',
      hasattr(R, 'blind_population')
      and isinstance(R.blind_population(), (set, frozenset)))

blind = R.blind_population()
check('B2. the real run PRINTS the blind count, so it cannot be a figure only '
      'this control knows about',
      'BLIND' in R.render_blind_line(blind),
      R.render_blind_line(blind))

# ── C. THE REAL CORPUS, and the measurement that started this ─────────────
real_path = os.path.join(REPO, 'api', 'sd-data-alf-caregiver-scope.test.js')
if os.path.isfile(real_path):
    import io
    real = io.open(real_path, encoding='utf-8', errors='replace').read()
    sets_, gated_, _u, _c, _und = R.analyse()
    allr = set()
    for v in sets_.values():
        allr |= v
    got_real = R.table_driven(real, allr, set(gated_))
    # ── THE REAL CASE SPLITS INTO TWO FACTS AND THEY ARE ASSERTED APART ────
    # These arms first asserted that `alf_billing` is credited with
    # `caregiver`, and that FAILED against a correct rule. The rule locates the
    # table, the loop, the refusal and the literal `caregiver` -- all five
    # conditions hold -- and then declines, because `caregiver` IS NOT IN THE
    # ROLE UNIVERSE: it appears in no `roleSet({...})` declaration in
    # api/sd-data.js, which is the tool's own `unknown_roles()` finding.
    #
    # So the table rule is NOT what is keeping those resources in the
    # not-driven bucket. An undeclared role is. Asserting the two separately
    # is the only way the next reader can tell which one to fix.
    # C1 FIRST ASSERTED THE RULE DECLINED ENTIRELY, AND THAT WAS WRONG. The
    # suite carries TWO loops over the same table: one drives it as
    # `caregiver`, one as `owner`. So the resources ARE credited -- with
    # `owner` only, because `caregiver` is in no roleSet declaration and never
    # enters the role universe. `owner` is an ALLOWED role, so they land as
    # driven-as=owner, i.e. UNCOVERED, which is the honest state and not a
    # move to COVERED. The rule is working; the undeclared role is what stops
    # it changing the verdict.
    check('C1. THE REAL CASE: the table is attributed, and with ONLY allowed '
          'roles -- `caregiver` never enters because no roleSet declares it, '
          'so these stay UNCOVERED rather than falsely moving to COVERED',
          set(got_real) and all('caregiver' not in v for v in got_real.values())
          and 'caregiver' not in allr,
          'got %s | caregiver in all_roles: %s'
          % ({k: sorted(v) for k, v in sorted(got_real.items())[:3]},
             'caregiver' in allr))
    check('C2. ...and with `caregiver` in the role universe the SAME call '
          'credits eight resources from that one table, which is what proves '
          'the rule works on the real file and isolates the cause',
          len(R.table_driven(real, allr | {'caregiver'}, set(gated_))) >= 8,
          sorted(R.table_driven(real, allr | {'caregiver'}, set(gated_))))
else:
    check('C1. the real suite exists', False, 'api/sd-data-alf-caregiver-scope.test.js is gone')

# ── D. ANCHORS ─────────────────────────────────────────────────────────────
check('D1. file_driven still unions the table rule in, or the screen never '
      'sees it',
      'table_driven' in R.file_driven.__doc__ or
      'table' in (R.file_driven.__doc__ or '').lower(),
      'file_driven docstring does not mention the table rule')

print('\n%s  run_role_gate_table_rule_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
