"""The control on tools/cross_tenant_isolation_scope.py's GRADER.

    python tests/run_cross_tenant_scope_probe.py

Exit 0 all arms pass, 1 an arm failed.

── WHY THIS EXISTS, AND IT IS THE FIRST CROSS-DOMAIN DISCIPLINE ───────────────
docs/2026-09-13-cross-domain-disciplines.md: lock a check's criteria against
SYNTHETIC FIXTURES before running it on real data. The scope tool's whole output
is a claim about which tests are real, and a grader that is wrong in the
generous direction reports coverage this platform does not have -- on exactly
the control where an overstated number is worse than a zero.

BOTH DIRECTIONS ARE DRIVEN, which is the point. A grader that says GENUINE to
everything passes a positive-only fixture set, and a grader that says NONE to
everything passes a negative-only one. Neither is worth anything alone.

THE NEAR-MISS FIXTURES ARE THE LOAD-BEARING ONES. A fixture that is obviously
not an isolation test proves nothing; the shapes below are each ONE property
short of genuine, and each of those properties is one this platform has
actually shipped as a false pass somewhere.
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import cross_tenant_isolation_scope as S  # noqa: E402

FAILED = []


def arm(name, body, expect):
    got, why = S.grade(body)
    ok = got == expect
    print('  %-4s %-58s expected %-7s got %-7s' % ('ok' if ok else 'FAIL', name, expect, got))
    if not ok:
        print('        why: %s' % why)
        FAILED.append(name)


# ── THE REFERENCE CASE, verbatim in shape ─────────────────────────────────────
GENUINE = """
var rows = [
  { license_hash: 'practice-A-hash', complaint_id: 'A-1' },
  { license_hash: 'practice-B-hash', complaint_id: 'B-1' }
];
global.fetch = async function (url) {
  var u = String(url);
  var mHash = u.match(/license_hash=eq\\.([^&]+)/);
  var mId = u.match(/complaint_id=eq\\.([^&]+)/);
  var matches = rows.filter(function (r) {
    if (mHash && r.license_hash !== decodeURIComponent(mHash[1])) return false;
    if (mId && r.complaint_id !== decodeURIComponent(mId[1])) return false;
    return true;
  });
  return { ok: true, json: async function () { return matches; } };
};
assert.strictEqual(res.statusCode, 404);
"""

# ── NEAR MISSES: each one property short, each a real shipped shape ──────────
NO_FILTER = """
var rows = [
  { license_hash: 'practice-A-hash', complaint_id: 'A-1' },
  { license_hash: 'practice-B-hash', complaint_id: 'B-1' }
];
global.fetch = async function (url) {
  assert.ok(String(url).indexOf('license_hash=eq.') !== -1);
  return { ok: true, json: async function () { return rows; } };
};
assert.strictEqual(res.statusCode, 404);
"""

ONE_TENANT = """
global.fetch = async function (url) {
  var u = String(url);
  var mHash = u.match(/license_hash=eq\\.([^&]+)/);
  var rows = [{ license_hash: 'only-hash', id: 'X' }];
  return { ok: true, json: async function () {
    return rows.filter(function (r) { return !mHash || r.license_hash === mHash[1]; }); } };
};
assert.strictEqual(res.statusCode, 404);
"""

NO_REFUSAL = """
var rows = [
  { license_hash: 'hash-A', id: 'A-1' },
  { license_hash: 'hash-B', id: 'B-1' }
];
global.fetch = async function (url) {
  var u = String(url);
  var mHash = u.match(/license_hash=eq\\.([^&]+)/);
  return { ok: true, json: async function () {
    return rows.filter(function (r) { return !mHash || r.license_hash === mHash[1]; }); } };
};
assert.strictEqual(res.statusCode, 200);
"""

# ── AND THE OTHER DIRECTION: things that must NOT score at all ────────────────
APP_BOUNDARY = """
// one tenant, two APPS -- this is tests/app_session_isolation.js's real shape.
var LIC_HASH = 'abc123';
var tok = sign({ license_hash: LIC_HASH, app_id: 'stonedesk' });
await handler(mockReq({ resource: 'law_trusttx' }, tok), res);
assert.strictEqual(res.statusCode, 401);
"""

UNRELATED = """
await handler(mockReq({ resource: 'law_trusttx', action: 'write' }, 'Bearer K'), res);
assert.strictEqual(res.statusCode, 400);
assert.strictEqual(res.body.error.code, 'INVALID_TIME_ENTRY');
"""


# ── THE SECOND SPELLING, added when the grader scored the MORE GENERAL test
# WORSE. A generic `<col>=eq.<value>` parser and two tenants bound to constants
# is strictly better engineering than a hardcoded license_hash regex and inline
# string literals, and criteria derived from one file scored it WEAK. Both
# spellings are fixtures now so neither can be lost to the next widening.
GENUINE_GENERIC = """
const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';
const rows = [
  { license_hash: HASH_A, invoice_id: 'A-1' },
  { license_hash: HASH_B, invoice_id: 'B-1' }
];
function postgrestMock(rows) {
  return async function (url) {
    const q = String(url).split('?')[1] || '';
    const eqs = [];
    q.split('&').forEach(function (part) {
      const m = part.match(/^([a-z0-9_]+)=eq\\.(.*)$/);
      if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
    });
    const matches = rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; });
    });
    return { ok: true, json: async function () { return matches; } };
  };
}
assert.deepStrictEqual(owners, ['A']);
assert.strictEqual(res.statusCode, 404);
"""


# ── THE SHAPE THE CRITERIA COULD NOT SEE ────────────────────────────────────
# A LIST read has no status code to assert -- the refusal is an ABSENCE, a 200
# carrying only tenant A's rows. The first criteria matched a status code and a
# bare `.length, 0` and had no expression at all for a content assertion, so
# the reference implementation, whose own header says "assert the CONTENT of
# the array, never its length alone", graded WEAK while a transplant doing the
# thing it calls wrong graded GENUINE. Fixture added so that cannot recur.
CONTENT_REFUSAL = """
const HASH_A = 'tenant-A-hash';
const HASH_B = 'tenant-B-hash';
const rows = [
  { license_hash: HASH_A, invoice_id: 'A-1', data: { owner: 'A' } },
  { license_hash: HASH_B, invoice_id: 'B-1', data: { owner: 'B' } }
];
global.fetch = async function (url) {
  const q = String(url).split('?')[1] || '';
  const eqs = [];
  q.split('&').forEach(function (part) {
    const m = part.match(/^([a-z0-9_]+)=eq\\.(.*)$/);
    if (m) eqs.push([m[1], decodeURIComponent(m[2])]);
  });
  return { ok: true, json: async function () {
    return rows.filter(function (r) {
      return eqs.every(function (kv) { return String(r[kv[0]]) === kv[1]; }); }); } };
};
const owners = res.body.data.map(function (x) { return x.owner; });
assert.deepStrictEqual(owners, ['A']);
"""


def main():
    print('GRADER CONTROL -- criteria %s' % S.CRITERIA_VERSION)
    print('')
    print('POSITIVE -- the shape the reference case has')
    arm('the reference shape: filtering mock, 2 hashes, refusal', GENUINE, 'GENUINE')
    arm('the GENERIC spelling: eq.-parser + tenants bound to constants',
        GENUINE_GENERIC, 'GENUINE')
    print('')
    print('NEAR MISSES -- one property short, each a real false-pass shape')
    arm('mock returns a FIXED array; eq. asserted as a substring', NO_FILTER, 'WEAK')
    arm('filtering mock and a refusal, but only ONE tenant', ONE_TENANT, 'WEAK')
    arm('filtering mock and two tenants, but asserts SUCCESS', NO_REFUSAL, 'WEAK')
    print('')
    print('NEGATIVE -- must not be mistaken for tenant isolation')
    arm('the APP boundary: one tenant, two apps', APP_BOUNDARY, 'NONE')
    arm('an ordinary validation test that names the resource', UNRELATED, 'NONE')
    print('')
    print('THE CONTENT-ASSERTION SHAPE -- invisible to the criteria for a full session')
    arm('a LIST read whose refusal is an ABSENCE, not a status code',
        CONTENT_REFUSAL, 'GENUINE')

    print('')
    # ── REAL FILES, NOT FIXTURES, AND THIS IS THE ARM THAT WAS MISSING ──────
    # CC's review: "ALL SEVEN ARE SYNTHETIC. A fixture written from the same
    # reading as the criteria cannot contradict them, which is why the criteria
    # could be blind to a content-assertion refusal while all seven arms
    # passed." That is exactly what happened -- the reference implementation
    # graded WEAK for a full session while every fixture arm was green. Every
    # reference case is driven here as a REAL FILE, and a new reference must be
    # added to S.REFERENCE_TESTS, which is what makes this arm grow with the
    # work instead of staying anchored on the first one.
    print('REAL FILES -- the arm that was missing, and its absence let the inversion ship')
    for ref in S.REFERENCE_TESTS:
        body = io.open(os.path.join(REPO, ref), encoding='utf-8').read()
        got, why = S.grade(body)
        ok = got == 'GENUINE'
        print('  %-4s %-58s expected %-7s got %-7s'
              % ('ok' if ok else 'FAIL', 'the REAL ' + ref, 'GENUINE', got))
        if not ok:
            print('        why: %s' % why)
            FAILED.append(ref)

    # A real file that must NOT grade GENUINE, so the real-file arms are not
    # one-directional. cc's suite for this feature is a serious, green,
    # 20-assertion file that tests the outbound queue and no tenant boundary.
    negative = 'tests/sairnscape_outbound_queue.js'
    try:
        body = io.open(os.path.join(REPO, negative), encoding='utf-8').read()
    except OSError:
        body = None
    if body is not None:
        got, why = S.grade(body)
        ok = got != 'GENUINE'
        print('  %-4s %-58s expected %-7s got %-7s'
              % ('ok' if ok else 'FAIL', 'the REAL ' + negative, 'not GEN', got))
        if not ok:
            print('        why: %s' % why)
            FAILED.append(negative)

    # And the per-resource half, which the file-level grade does not answer.
    print('')
    print('DECLARATION -- a file-level GENUINE credits only what the file DECLARES')
    ref = 'api/sd-data-cross-tenant-isolation.test.js'
    body = io.open(os.path.join(REPO, ref), encoding='utf-8').read()
    got_set, none_reason = S.declared_coverage(body)
    want = {'law_invoices', 'law_opaccounts', 'law_barcerts'}
    ok = got_set == want and none_reason is None
    print('  %-4s %-58s %s' % ('ok' if ok else 'FAIL',
                               'the reference DECLARES its three resources',
                               ','.join(sorted(got_set)) or '(none)'))
    if not ok:
        FAILED.append('declaration')
    got_set2, reason2 = S.declared_coverage(
        io.open(os.path.join(REPO, 'api/dnt-bi.test.js'), encoding='utf-8').read())
    ok2 = got_set2 == set() and bool(reason2)
    print('  %-4s %-58s %s' % ('ok' if ok2 else 'FAIL',
                               'dnt-bi declares none WITH a reason',
                               (reason2 or '(no reason)')[:40]))
    if not ok2:
        FAILED.append('none-declaration')
    ok3 = S.declared_coverage('nothing here')[1] is None
    print('  %-4s %-58s' % ('ok' if ok3 else 'FAIL',
                            'an ABSENT declaration is not a `none` declaration'))
    if not ok3:
        FAILED.append('absent-vs-none')

    print('')
    if FAILED:
        print('%d arm(s) FAILED: %s' % (len(FAILED), ', '.join(FAILED)))
        print('The scope tool\'s numbers are NOT trustworthy until these pass.')
        return 1
    print('all arms pass -- the grader separates the reference shapes from the near')
    print('misses and the unrelated shapes, agrees with every REAL reference file,')
    print('and credits a resource only where the file DECLARES it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
