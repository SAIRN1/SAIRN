"""A declaration with NO TABLE behind it must not earn GENUINE.

Run: python tests/run_cross_tenant_untabled_declaration_probe.py

# REQUIREMENT: tools/cross_tenant_isolation_scope.py must not issue its
#   STRONGEST verdict on a coverage claim it had no way to check -- and the
#   branch where it used to is one NO FILE ON THIS CORPUS TAKES, so nothing
#   that reads the real output can tell whether the fix works

THIS IS A LATENT FAIL-OPEN, FIXED BEFORE IT FIRED, AND THAT IS EXACTLY WHY IT
NEEDS THIS FILE. `d538f1e8` closed the same hole for files that DO carry a
table: a declared name absent from the driven set is reported and intersected
away. The untabled half kept the report and dropped the intersection, so a
declaration nothing could verify still earned full GENUINE credit. Measured
2026-09-22: ZERO files take that branch, so the tool's real output is
BYTE-IDENTICAL before and after the fix. A fix that changes no output is the
kind somebody reverts as pointless, and a branch no corpus exercises is the
kind that fails open years later with nobody watching. The arms below are the
only thing that can tell either story.

WHY WEAK AND NOT A THIRD GRADE, asserted rather than asserted-in-prose: rank()
collapses hits through `gap = {'GENUINE': 0, 'WEAK': 2, 'NONE': 3}[best]`. A
new grade string reaches that dict with no key for it and the tool dies on the
first file that hits the branch -- trading a silent over-credit for a crash, in
a branch nobody exercises. C4 drives rank() on the untabled result and requires
it to survive, which is the arm that would have caught that mistake.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'cross_tenant_isolation_scope.py')

passed = failed = 0


def ok(name, cond, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   ' + name)
    else:
        failed += 1
        print('  FAIL ' + name + ('\n         ' + str(detail) if detail else ''))


def load():
    spec = importlib.util.spec_from_file_location('cts', TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# The reference GENUINE shape, same properties the grader requires: a
# URL-FILTERING mock (it reads the eq. clause out of the query), two distinct
# tenant hashes, and a refusal asserted. Copied in shape from
# tests/run_cross_tenant_scope_probe.py's own reference rather than invented,
# so this probe is not grading against a rule of its own.
GENUINE_ARM = """
var rows = [
  { license_hash: 'tenant-A-hash', widget_id: 'A-1' },
  { license_hash: 'tenant-B-hash', widget_id: 'B-1' }
];
global.fetch = async function (url) {
  var u = String(url);
  var mHash = u.match(/license_hash=eq\\.([^&]+)/);
  var matches = rows.filter(function (r) {
    return !mHash || r.license_hash === decodeURIComponent(mHash[1]);
  });
  return { ok: true, json: async function () { return matches; } };
};
assert.strictEqual(res.statusCode, 404);
"""

# THE TABLE SHAPE IS THE TOOL'S, NOT MINE. _ROW_NAME reads a row's FIRST string
# literal out of a BRACKETED row -- ['fx_alpha', 'alpha_id'] -- and _TABLE wants
# `^const NAME = [` ... `^];`. My first draft wrote rows as
# `{ resource: 'fx_alpha' }`, which parses as NO TABLE AT ALL, so C1 and C6 both
# fell into the untabled branch they exist to CONTRAST with and failed. The
# fixture was wrong, not the tool -- and it is worth leaving recorded, because a
# control that silently drifts into the branch it is supposed to be the opposite
# of proves nothing while still looking like a test.
TABLE = """
const CASES = [
  ['fx_alpha', 'alpha_id'],
  ['fx_beta', 'beta_id'],
];
"""


def drive(m, body, names):
    """Run tests_naming() over ONE synthetic file."""
    m.all_files = lambda exts: ['tests/fx_fixture.js']
    m.is_test = lambda rel: True
    m.read = lambda rel: body
    m.SELF_EXCLUDED = set()
    return m.tests_naming(names), list(m.UNDECLARED)


def grades_for(hits, name):
    return [g for _f, g, _w in hits.get(name, [])]


def main():
    print('cross_tenant_isolation_scope -- a declaration with no table behind '
          'it is a claim, not evidence\n')
    NAMES = ['fx_alpha', 'fx_beta']

    # ── C1 CONTROL: table present and driving the name -> GENUINE stands ────
    m = load()
    body = ('// CROSS-TENANT-ISOLATION: fx_alpha\n' + TABLE + GENUINE_ARM)
    hits, und = drive(m, body, NAMES)
    ok('C1 CONTROL: a genuine arm, DECLARED, with a table that really drives '
       'the name -- still GENUINE. Without this arm every assertion below is '
       'satisfied by a tool that never says GENUINE at all',
       'GENUINE' in grades_for(hits, 'fx_alpha'),
       grades_for(hits, 'fx_alpha'))

    # ── C2 THE FIX: same genuine arm, same declaration, NO table ────────────
    m = load()
    body_nt = ('// CROSS-TENANT-ISOLATION: fx_alpha\n' + GENUINE_ARM)
    hits_nt, und_nt = drive(m, body_nt, NAMES)
    g_nt = grades_for(hits_nt, 'fx_alpha')
    ok('C2 THE FIX: the SAME genuine arm and the SAME declaration with NO '
       'table is WEAK, not GENUINE -- the file has a real cross-tenant arm and '
       'nothing says this resource is what it covers',
       g_nt == ['WEAK'], g_nt)
    ok('C3 ...and the reason NAMES the missing table, so a reader can tell '
       'this downgrade from the unrelated one that fires when a resource is '
       'not declared at all',
       any('NO TABLE' in w for _f, _g, w in hits_nt.get('fx_alpha', [])),
       [w for _f, _g, w in hits_nt.get('fx_alpha', [])])

    # ── C4 THE ARM THAT JUSTIFIES REUSING 'WEAK' ───────────────────────────
    # rank() looks the collapsed grade up in a dict with three keys. A new
    # grade string would KeyError here, on the first file to hit the branch.
    try:
        row = m.rank('fx_alpha', [], hits_nt['fx_alpha'], 'fx_alpha harm text')
        survived, why = True, row.get('coverage')
    except Exception as e:                       # noqa: BLE001 -- the arm reads it
        survived, why = False, repr(e)
    ok('C4 rank() SURVIVES the untabled result and collapses it to WEAK -- this '
       'is why the fix reuses an existing grade instead of inventing a third '
       'one, and it is the arm that would have caught that mistake',
       survived and why == 'WEAK', why)

    # ── C5: the file is still NAMED, not silently downgraded ───────────────
    ok('C5 the file is still reported in UNDECLARED with the explanation -- a '
       'suite legitimately written without a table should not lose its credit '
       'silently, and the reader has to know which of the two cases this is',
       any('carries no table' in note for _rel, note, _res in und_nt),
       [n for _r, n, _x in und_nt])

    # ── C6: d538f1e8's case is UNCHANGED ───────────────────────────────────
    m = load()
    body_undriven = ('// CROSS-TENANT-ISOLATION: fx_alpha, fx_beta\n'
                     + "const CASES = [\n  ['fx_alpha', 'alpha_id'],\n];\n"
                     + GENUINE_ARM)
    hits_u, und_u = drive(m, body_undriven, NAMES)
    ok('C6 the TABLED case is untouched: a declared name the table does not '
       'drive is still intersected away (fx_beta -> not GENUINE) while the '
       'driven one still earns it (fx_alpha -> GENUINE)',
       'GENUINE' in grades_for(hits_u, 'fx_alpha')
       and 'GENUINE' not in grades_for(hits_u, 'fx_beta'),
       {'fx_alpha': grades_for(hits_u, 'fx_alpha'),
        'fx_beta': grades_for(hits_u, 'fx_beta')})

    # ── C7: a file declaring NOTHING is unaffected in either direction ─────
    m = load()
    hits_nd, _ = drive(m, GENUINE_ARM + '\nfx_alpha\n', NAMES)
    ok('C7 a genuine file that declares NOTHING still credits WEAK with the '
       'undeclared reason, not the untabled one -- the two downgrades must '
       'stay distinguishable',
       grades_for(hits_nd, 'fx_alpha') == ['WEAK']
       and not any('NO TABLE' in w for _f, _g, w in hits_nd.get('fx_alpha', [])),
       [w[:90] for _f, _g, w in hits_nd.get('fx_alpha', [])])

    # ── C8: THE REAL CORPUS, and the honest disclosure with it ─────────────
    m = load()
    real = m.tests_naming(m.tier_a())
    untabled = [(rel, res) for rel, note, res in m.UNDECLARED
                if 'carries no table' in note]
    bad = []
    for rel, resources in untabled:
        for r in resources:
            if any(f == rel and g == 'GENUINE' for f, g, _w in real.get(r, [])):
                bad.append((rel, r))
    ok('C8 on the REAL corpus, no untabled declaration earns GENUINE. '
       'Files taking that branch today: %d -- so this is a LATENT fail-open '
       'fixed before it fired, and the arm is vacuous now and meaningful the '
       'day one appears' % len(untabled),
       bad == [], bad)

    print('\n%d passed, %d failed' % (passed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
