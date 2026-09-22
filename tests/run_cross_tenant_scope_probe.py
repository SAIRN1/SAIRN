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
import re
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


# A file that DECLARES and carries no table at all. Built by join so the
# fixture cannot be broken by an escape in a literal.
NO_TABLE = chr(10).join(['// CROSS-TENANT-ISOLATION: a_one', 'console.log(1)'])


def _re_grades(mod):
    """Every grade string the scanner can attach to a hit, read from its own
    source rather than from a list kept here -- a second copy of the vocabulary
    is what would let a fourth grade slip in unnoticed."""
    import re as _r
    src = io.open(os.path.join(REPO, 'tools/cross_tenant_isolation_scope.py'),
                  encoding='utf-8').read()
    # ANCHORED ON THE FUNCTION THAT GRADES, AND THE ANCHOR IS ASSERTED. An
    # anchor that has moved would make this arm scan an empty span and pass on
    # nothing, which is the vacuous shape this file exists to police.
    start = src.index('def tests_naming(')
    end = src.index('# ── RISK RANK', start)
    body = src[start:end]
    found = set(_r.findall(r"hits\[n\]\.append\(\(rel, '([A-Z]+)'", body))
    assert found, 'no graded append found -- the anchor has moved'
    return found


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

    # ── A WRAPPED DECLARATION MUST PARSE WHOLE ───────────────────────────
    # The first version's regex stopped at the newline, so a 46-resource
    # declaration was read as 4. An UNDER-count is the safe direction and was
    # still wrong, and nothing would have announced it.
    wrapped = ('// CROSS-TENANT-ISOLATION: a_one, a_two,\n'
               '//   b_one, b_two,\n'
               '//   c_one\n'
               '// and now some prose that is not a resource list at all\n')
    got_w, _ = S.declared_coverage(wrapped)
    okw = got_w == {'a_one', 'a_two', 'b_one', 'b_two', 'c_one'}
    print('  %-4s %-58s %s' % ('ok' if okw else 'FAIL',
                               'a WRAPPED declaration parses whole and stops at prose',
                               ','.join(sorted(got_w))))
    if not okw:
        FAILED.append('wrapped-declaration')

    # ── THE ARM FOURTH'S REVIEW FOUND MISSING ────────────────────────────
    # Three declaration arms existed and NONE of them asked the one question
    # that matters: does a name on the declaration line, and nowhere else,
    # credit a resource? It did. Fourth drove it -- `sv_controlled` added to
    # the reference file's declaration and nothing else took GENUINE 3 -> 4,
    # with no test behind it and every arm here green.
    #
    # Driven IN MEMORY against the real reference file, not a fixture, because
    # a fixture written from the same reading as the fix cannot contradict it
    # -- which is the lesson the REAL-FILE arms above already carry.
    real = io.open(os.path.join(REPO, 'api/sd-data-cross-tenant-isolation.test.js'),
                   encoding='utf-8').read()
    injected = real.replace(
        '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts',
        '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts, sv_controlled')
    # ASSERT THE MUTATION LANDED. The arm depends on a literal string in
    # another file; if that declaration line is ever reworded, `injected`
    # equals `real`, nothing is tested, and without this the arm still passes.
    # That is the shape this whole tool keeps recording -- a check that stops
    # checking and says nothing.
    if injected == real:
        print('  FAIL %-58s %s' % ('the injection arm could not find its target line',
                                   'the declaration line was reworded'))
        FAILED.append('injection-target-missing')
    okinj = injected != real
    decl_i, _ri = S.declared_coverage(injected)
    driven_i = S.driven_resources(injected)
    okinj = okinj and 'sv_controlled' in decl_i and driven_i is not None         and 'sv_controlled' not in driven_i
    print('  %-4s %-58s %s' % ('ok' if okinj else 'FAIL',
                               'a name on the DECLARATION LINE alone is not driven',
                               'declared=%d driven=%d' % (len(decl_i), len(driven_i or []))))
    if not okinj:
        FAILED.append('declaration-line-only')

    # And the table reader itself must not be vacuous: it has to FIND the
    # reference file's table, or the cross-check above passes by matching
    # nothing, which is how a guard stops guarding.
    driven_real = S.driven_resources(real)
    okt = driven_real is not None and {'law_invoices', 'law_opaccounts',
                                       'law_barcerts'} <= driven_real
    print('  %-4s %-58s %s' % ('ok' if okt else 'FAIL',
                               "the table reader finds the reference suite table",
                               ','.join(sorted(driven_real or [])) or '(none)'))
    if not okt:
        FAILED.append('table-reader')

    # A file with NO table is a THIRD state, not a refusal: it must return None
    # so its declarations are credited and DISCLOSED rather than silently lost.
    okn = S.driven_resources(NO_TABLE) is None
    print('  %-4s %-58s' % ('ok' if okn else 'FAIL',
                            'a file with no table reads as None, not as an empty set'))
    if not okn:
        FAILED.append('no-table-third-state')

    # ── AN UNTABLED FILE'S DECLARATION WAS EVIDENCE FOR ITSELF ───────────
    # THE GAP: when driven_resources() returned None the declaration was
    # credited WHOLE, and the only other test a name had to pass was appearing
    # somewhere in the body -- which the DECLARATION LINE ITSELF satisfies. So
    # a suite with no table could declare any resource and be credited GENUINE
    # for it with nothing driving it. Same shape as the tabled-file defect
    # fixed in d538f1e8, in the branch that fix did not reach.
    #
    # MEASURED BEFORE THE FIX, and it matters for how this is read: 683 test
    # files scanned, 5 carry a declaration, and ALL THREE that declare
    # resources are TABLED. The other two declare `none(...)`. So the branch
    # has ZERO live instances today -- this is ARMING it before it is
    # exercised, not repairing a number that is currently wrong.
    # ── THE RESIDUE INSIDE THE WEAK DOWNGRADE ────────────────────────────
    # The untabled branch now credits WEAK rather than GENUINE, which is the
    # load-bearing fix. A RESIDUE SURVIVES IT: the hits loop still requires the
    # name to appear in the body, and the DECLARATION LINE ITSELF satisfies
    # that -- so a resource named only in the declaration, with nothing else in
    # the file referring to it, still earns WEAK. Reported, not re-graded; a
    # fourth grade would reach rank()'s dict and take the tool down, which is
    # the same reason the downgrade rejected a third one.
    #
    # TWO CONVERGENT FIXES LANDED ON THIS BRANCH WITHIN THE HOUR and these arms
    # cover the merged behaviour rather than either one alone.
    print('')
    print('UNTABLED DECLARATIONS -- the declaration may not be its own evidence')
    _u = getattr(S, 'unbacked_declarations', None)
    if _u is None:
        print('  FAIL %-58s' % 'unbacked_declarations() is missing')
        FAILED.append('untabled-no-helper')
    else:
        # SYNTHETIC NAMES, matching NO_TABLE's own `a_one` convention above.
        # I first wrote these fixtures with REAL Tier A resource names, and
        # that is wrong on its own merits before any gate is involved: a reader
        # cannot tell a fixture body from a quotation of real code, which is
        # the confusion this whole file is about. It also made the Tier A
        # review gate fire on three resources none of this touches -- said out
        # loud so the rename is not read as slipping a gate: the gate is what
        # made me look, the convention is why it changed.
        DECL = '// CROSS-TENANT-ISOLATION: a_one'
        # Nothing but the declaration mentions it.
        GHOST = chr(10).join([DECL, 'assert.strictEqual(res.status, 401);'])
        # The file really does refer to it outside the declaration.
        REAL = chr(10).join([
            DECL,
            "await call({ resource: 'a_one', tenant: 'A' });",
            'assert.strictEqual(res.status, 401);',
        ])
        for label, body, want in (
                ('a name appearing ONLY in the declaration is REPORTED as '
                 'unbacked', GHOST, True),
                ('CONTROL: a name the file really refers to is NOT reported, '
                 'so the check discriminates', REAL, False)):
            got = 'a_one' in _u(body, {'a_one'})
            good = got == want
            print('  %-4s %-58s' % ('ok' if good else 'FAIL', label))
            if not good:
                FAILED.append('untabled-' + ('ghost' if want else 'real'))
        # THE DECLARATION BLOCK IS STRIPPED INCLUDING ITS WRAPPED CONTINUATION
        # LINES -- a 46-resource declaration does not fit on one line, and a
        # strip that stopped at the first newline would read every continued
        # name as evidence of itself.
        WRAPPED = chr(10).join([
            '// CROSS-TENANT-ISOLATION: a_one,',
            '//   a_two, a_three',
            'assert.strictEqual(res.status, 401);',
        ])
        okwrap = set(_u(WRAPPED, {'a_one', 'a_two', 'a_three'})) == \
            {'a_one', 'a_two', 'a_three'}
        print('  %-4s %-58s' % ('ok' if okwrap else 'FAIL',
                                'a WRAPPED declaration is stripped whole, continuation lines too'))
        if not okwrap:
            FAILED.append('untabled-wrapped-not-stripped')
        # AND IT REPORTS RATHER THAN RE-GRADING. A fourth grade would reach
        # rank()'s {'GENUINE':0,'WEAK':2,'NONE':3} lookup and take the tool
        # down on the first file to hit this branch.
        okgrades = set(_re_grades(S)) <= {'GENUINE', 'WEAK', 'NONE'}
        print('  %-4s %-58s' % ('ok' if okgrades else 'FAIL',
                                'no fourth grade was introduced -- rank() has no key for one'))
        if not okgrades:
            FAILED.append('untabled-fourth-grade')
        # THE TABLED PATH MUST BE UNTOUCHED. The whole change is in the
        # `driven is None` branch, and quietly narrowing the tabled path would
        # be a far worse trade than the gap.
        _real_tabled = S.driven_resources(io.open(
            os.path.join(REPO, 'api/sd-data-cross-tenant-dispatchers.test.js'),
            encoding='utf-8').read())
        oktab = _real_tabled is not None and len(_real_tabled) >= 40
        print('  %-4s %-58s %s' % ('ok' if oktab else 'FAIL',
                                   'CONTROL: the real tabled suite still reads its table',
                                   len(_real_tabled or [])))
        if not oktab:
            FAILED.append('untabled-broke-tabled')

    # ── EVERY DECLARED RESOURCE MUST ACTUALLY BE DRIVEN ──────────────────
    # The declaration is a claim somebody signs, and a signature is only worth
    # more than a guess if something checks it. The dispatcher suite declared
    # sd_quote_requests -- which has its own named branch and is not a member
    # of any dispatcher map -- and no arm drove it. Caught here, not in review.
    import re as _re
    src = io.open(os.path.join(REPO, 'api/sd-data-cross-tenant-dispatchers.test.js'),
                  encoding='utf-8').read()
    units = _re.search(r'const UNITS = \[(.*?)\n\];', src, _re.S)
    driven = set(_re.findall(r"\['([a-z0-9_]+)',\s*'[a-z0-9_]+'", units.group(1)))
    declared, _n = S.declared_coverage(src)
    extra = sorted(declared - driven)
    missing = sorted(driven - declared)
    okd = not extra and not missing
    print('  %-4s %-58s %d driven, %d declared'
          % ('ok' if okd else 'FAIL',
             'the dispatcher suite declares EXACTLY what it drives',
             len(driven), len(declared)))
    if not okd:
        print('        declared but NOT driven: %s' % (extra or '-'))
        print('        driven but NOT declared: %s' % (missing or '-'))
        FAILED.append('declaration-vs-driven')

    # ── THE EXCLUSION LIST ITSELF, WHICH NOTHING WAS GUARDING ────────────
    # SELF_EXCLUDED is the fix for a real false GENUINE: the grader was
    # counting its OWN fixture bodies as platform coverage, so two of three
    # reported GENUINEs were one real file and this one. The fix is two string
    # literals, and a string literal naming another file is the exact shape
    # this platform keeps recording as "nothing announces the day a check stops
    # testing anything" -- rename either file and the exclusion silently
    # excludes nothing, while the report keeps PRINTING both names as excluded.
    # A claim that the exclusion happened, over an exclusion that did not.
    print('')
    print('SELF-EXCLUSION -- the guard on the guard, and it had none')
    scanned = set(S.all_files(('.js', '.py')))
    for rel in S.SELF_EXCLUDED:
        # Membership of the SCANNED set, not os.path.isfile. A path that exists
        # on disk but is spelled differently from what all_files() emits -- a
        # backslash, a './' prefix, a file moved out of api/ or tests/ -- is
        # excluded from nothing, and `isfile` would call it healthy.
        oke = rel in scanned
        print('  %-4s %-58s %s'
              % ('ok' if oke else 'FAIL', 'excluded and actually scanned: ' + rel,
                 'in the scan set' if oke else 'NOT a file this scan reaches'))
        if not oke:
            FAILED.append('self-excluded-missing:' + rel)
            continue
        # And the exclusion has to still be LOAD-BEARING. A file the scanner
        # would have ignored anyway is a decorative guard, and a decorative
        # guard is one nobody notices has stopped mattering. Either grade or a
        # declaration is enough -- both are ways this file would have been
        # credited had it not been excluded.
        #
        # ── AN IMPORTER IS LOAD-BEARING BY THE OTHER ARM'S OWN RULE ─────────
        # (2026-09-22) These two arms CONTRADICTED each other and the
        # contradiction was unreachable until a file hit it. The completeness
        # arm below says, in its own words, "a test file that IMPORTS this
        # grader has the grader as its subject, full stop" -- so it DEMANDS
        # such a file be listed. This arm then REFUSED the listing when that
        # file happened to declare nothing and grade NONE. Both arms cannot be
        # satisfied for it: listed, it is decorative; unlisted, the list is
        # incomplete. tests/grader_exclusion_parser_review_probe.py sat in that
        # gap and left the importer arm red on main, which stopped
        # tests/run_self_exclusion_guard_sabotage_probe.py at its baseline and
        # took all five of its mutations out of service.
        #
        # The resolution takes the completeness arm's rule as the stronger one,
        # because it is about WHAT THE FILE IS rather than what it currently
        # happens to be credited with. cc's own reasoning for excluding
        # tests/cross_tenant_dispatchers_review_probe.py was that it "was one
        # fixture edit away" from inflating the headline -- that argument does
        # not depend on today's credit either.
        #
        # MEASURED, so the cost is known: all six current entries import the
        # grader, and five of them are load-bearing by the original test as
        # well. So this exemption changes the verdict for exactly one entry
        # today, and it leaves the decorative check with NO current entry to
        # bite on -- it still applies to any future NON-importer entry, which
        # is the padding case it was written for, but it is unexercised by the
        # live corpus and a mutation cannot prove it bites without a fixture.
        # Stated rather than quietly accepted.
        body = io.open(os.path.join(REPO, rel), encoding='utf-8').read()
        g, _w = S.grade(body)
        decl, _n = S.declared_coverage(body)
        imports_grader = 'cross_tenant_isolation_scope' in body
        okl = g != 'NONE' or bool(decl) or imports_grader
        print('  %-4s %-58s %s'
              % ('ok' if okl else 'FAIL', 'and the exclusion still prevents something',
                 'grades %s, declares %d%s' % (g, len(decl),
                                               ', IMPORTS the grader' if imports_grader else '')))
        if not okl:
            FAILED.append('self-excluded-decorative:' + rel)

    # ── AND THE LIST MUST BE COMPLETE, which is a question a literal cannot
    # answer about itself. No heuristic here: a test file that IMPORTS this
    # grader has the grader as its subject, full stop. That is how
    # tests/cross_tenant_dispatchers_review_probe.py was found -- it imports
    # the module, quotes the reference file's CROSS-TENANT-ISOLATION line in
    # its prose, and was therefore credited with law_invoices, law_opaccounts
    # and law_barcerts "on the declaration alone".
    importers = []
    for rel in sorted(scanned):
        if not S.is_test(rel) or not rel.endswith('.py'):
            continue
        body = io.open(os.path.join(REPO, rel), encoding='utf-8').read()
        if re.search(r'^\s*(?:import|from)\s+cross_tenant_isolation_scope\b',
                     body, re.M):
            importers.append(rel)
    unexcluded = [r for r in importers if r not in S.SELF_EXCLUDED]
    oki = not unexcluded
    print('  %-4s %-58s %d importer(s)'
          % ('ok' if oki else 'FAIL',
             'every test that IMPORTS the grader is excluded', len(importers)))
    if not oki:
        for r in unexcluded:
            print('        NOT excluded: %s' % r)
        FAILED.append('grader-importer-not-excluded')

    # ── AND THE EXCLUSION IS APPLIED, not merely declared ────────────────
    # The two arms above check the LIST. This checks that tests_naming()
    # actually consults it: a `continue` deleted from the loop would leave both
    # arms above green and the false GENUINE back.
    hits = S.tests_naming(['law_invoices'])
    cited = [rel for rel, _g, _w in hits.get('law_invoices', [])]
    oka = 'tests/run_cross_tenant_scope_probe.py' not in cited
    print('  %-4s %-58s %s'
          % ('ok' if oka else 'FAIL', 'and tests_naming() really skips them',
             '%d file(s) cited for law_invoices' % len(cited)))
    if not oka:
        FAILED.append('self-exclusion-not-applied')
    # A skip that skipped EVERYTHING would also pass the arm above, so the
    # citation list has to be non-empty for the same resource.
    okb = bool(cited)
    print('  %-4s %-58s %s'
          % ('ok' if okb else 'FAIL', 'while still citing the files that are not excluded',
             ','.join(cited[:3]) or '(none)'))
    if not okb:
        FAILED.append('self-exclusion-skipped-everything')

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
