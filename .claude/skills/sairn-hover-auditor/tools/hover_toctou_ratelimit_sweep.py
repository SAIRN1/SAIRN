#!/usr/bin/env python
"""hover_toctou_ratelimit_sweep.py -- two UNDIRECTED whole-tree sweep
categories with real coverage accounting, built H1 b71.

  CATEGORY 1  TOCTOU ON MONEY OPERATIONS
  CATEGORY 2  MISSING RATE LIMITING ON UNAUTHENTICATED EXPENSIVE ENDPOINTS

WHY THESE TWO AND WHY THIS ROLE. The b71 dispatch assigns these two
categories to H1 and assigns SSRF, insecure deserialization, cache-key
poisoning, CORS/CSRF and path traversal / file upload to H2. That split
was verified against H2's own record rather than taken on trust: H2's log
entry seq1060 states "SCOPE DECLINED, explicitly: TOCTOU on money
operations and rate limiting on unauthenticated endpoints were NOT
swept." H2's entire log was additionally grepped for rate-limit/throttle
(11 hits) and TOCTOU/race/compare-and-set (119 hits) and every hit at
seq>=1040 was read: all of them concern H2's OWN tooling throttles or are
incidental word matches, not a platform sweep. So neither category is a
repeat. Recorded in chain entry #1616 BEFORE this tool ran.

WHAT A "CANDIDATE" MEANS HERE, SAID BEFORE ANY NUMBER IS PRINTED. Neither
rule can decide a defect by pattern alone, and the tool refuses to
pretend otherwise:

  * Category 1 needs to know whether two statements can interleave under
    real concurrency and whether the written value is derived from the
    read one. A matcher sees text order, not causality.
  * Category 2 needs to know whether a route is actually reachable
    unauthenticated in production and whether an environment variable is
    set in Vercel. Neither fact is in the repository.

So both rules are ADVISORY BY DESIGN. They flag a shape, report how much
of the tree they looked at, and the candidates are triaged BY READING.
This is the same stance H2's cache-key rule takes and for the same
reason. A tool that printed "N defects" from these rules would be
fabricating a determination it cannot make -- Guardian check 0b's shape.

COVERAGE ACCOUNTING IS THE POINT, NOT A GARNISH. Every file is either
CONSIDERED or SKIPPED WITH A NAMED REASON, counts and bytes are printed,
and an unreadable file is counted as UNREADABLE and forces exit 2. A
sweep that quietly skipped half the tree would look identical to a clean
one -- that is the eighth cross-domain discipline, and the reason "0
findings" is only meaningful next to "over how much".

TWO NAMED LIMITATIONS, BOTH LOCKED BY A SELFTEST ARM THAT ASSERTS THE
WEAKNESS RATHER THAN A PASS, so neither can be forgotten by a reader who
only sees the candidate count:

  * T2e -- GUARD SCOPE IS THE WHOLE FUNCTION BODY. One guarded write masks
    an unguarded write in the same function. Real instance:
    api/legal-citator.js, whose handler holds a correct upsert AND a
    read-modify-write counter increment; the upsert clears the body, so
    the tool does NOT flag the increment. It was found by reading and
    filed anyway. Fixing this needs per-statement scoping, i.e. a JS
    parser instead of a regex.
  * The candidate line is the FIRST write in the body, which is not
    necessarily the racing one. Real instance: api/agent/poll.js, reported
    at its fire-and-forget heartbeat PATCH while the actual race is the
    command-delivery write further down.

So "N candidates" is a triage queue, never a defect count in either
direction -- it can over-report (a reported line that is benign) and
under-report (a masked write), and both directions have a real instance
on this platform.

EXIT CODES. 0 = ran, no candidates. 1 = ran, candidates to triage.
2 = COULD NOT RUN (no repo, no population, or any unreadable file).
Never 0 for an incomplete run.

Run:
  python hover_toctou_ratelimit_sweep.py
  python hover_toctou_ratelimit_sweep.py --category 1
  python hover_toctou_ratelimit_sweep.py --selftest
"""
import os
import re
import subprocess
import sys

EXIT_CLEAN = 0
EXIT_CANDIDATES = 1
EXIT_COULD_NOT_RUN = 2


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=here,
                        capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover')


def population(repo):
    """(considered, skipped) -- derived from `git ls-files` every run, never
    from a count written down anywhere. The skip reasons are COUNTED, not
    silently dropped, so "208 considered" is checkable against the real
    tree size rather than asserted."""
    r = subprocess.run(['git', 'ls-files'], cwd=repo, capture_output=True,
                        text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None, None
    considered, skipped = [], []
    for p in r.stdout.splitlines():
        p = p.strip()
        if not p:
            continue
        if p.endswith('.test.js'):
            skipped.append((p, 'test file -- a test is not a production path'))
        elif p.startswith('api/') and p.endswith('.js'):
            considered.append(p)
        elif p.endswith('.html') and '/' not in p:
            considered.append(p)
        elif p.endswith('.html'):
            skipped.append((p, 'non-root html -- not a deployed app entry point'))
        else:
            skipped.append((p, 'not an api/*.js or root *.html production file'))
    return considered, skipped


# ── CATEGORY 1 ───────────────────────────────────────────────────────────
# The shape: inside ONE function body, a READ of a table followed by a
# WRITE back to the SAME table, where the body talks about money, and
# nothing between them makes the write conditional on what was read.
#
# WHY "SAME TABLE" RATHER THAN ANY READ-THEN-WRITE: a read of table A and
# a write to table B is not a lost update, it is a derived write, and
# flagging it would bury the real shape. Measured consequence of this
# choice is reported as the candidate count.

MONEY_RE = re.compile(
    r'\b(amount|balance|total|subtotal|price|cost|credit|credits|quota|'
    r'plan_status|paid|charge|charges|fee|fees|invoice|refund|payment|'
    r'payout|deposit|owed|due|remaining|units_left|cents|dollars)\b', re.I)

# A guard that makes a write conditional on the state that was read. Any
# ONE of these is enough to say the author thought about concurrency.
#
# `on_conflict` WITH AN UNDERSCORE WAS MISSING FROM THE FIRST VERSION AND
# THAT PRODUCED A FALSE POSITIVE ON REAL CODE. The first run flagged
# api/legal-citator.js:319, whose write is
# `cl_case_cache?on_conflict=cl_cluster_id` with
# `Prefer: resolution=merge-duplicates` -- a PostgREST upsert, which is a
# STRONGER guard than anything this pattern was looking for. The pattern
# matched only the SQL spelling `on conflict` with a space, so a tool
# built to find missing guards scored a correct guard as absent. That is
# the exact inversion CLAUDE.md records against sabotage_control_check.py,
# where five well-written controls using a stronger uniqueness guard were
# reported as unguarded. Found by triaging the tool's own output by hand
# rather than by trusting the count -- which is the argument for triaging
# by hand.
CAS_RE = re.compile(
    r"(return=representation|Prefer:\s*'count=exact|count=exact"
    r"|\brpc\b|/rpc/|on\s+conflict|ON\s+CONFLICT|on_conflict"
    r"|resolution=merge-duplicates|resolution=ignore-duplicates"
    r"|idempotency|advisory_lock|pg_advisory|for\s+update|FOR\s+UPDATE"
    r"|\bis\.null\b|if_match|If-Match|etag|ETag|version=eq\.|\bupsert\b)")

REST_RE = re.compile(r"/rest/v1/([A-Za-z0-9_]+)")
TABLE_IN_HELPER_RE = re.compile(r"\.rest\(\s*'([A-Za-z0-9_]+)|\.rest\(\s*([A-Z_]+)\s*\+")
WRITE_METHOD_RE = re.compile(r"method:\s*'(PATCH|PUT|POST|DELETE)'")
FUNC_SPLIT_RE = re.compile(
    r'^(?:async\s+)?function\s+\w+|^(?:module\.exports\s*=\s*)?async\s*\(|'
    r'^\s*(?:const|let)\s+\w+\s*=\s*(?:async\s*)?\(', re.M)


def _bodies(src):
    """Crude but DISCLOSED function partitioning: split on top-level
    function starts. This is a heuristic, not a parser -- a nested closure
    stays with its parent, which makes the rule slightly MORE inclusive
    (a read in the parent and a write in a closure still pair up). That
    direction is deliberate: for a detector, over-inclusive costs triage
    time, under-inclusive costs a missed defect."""
    starts = [m.start() for m in FUNC_SPLIT_RE.finditer(src)]
    if not starts:
        return [(1, src)]
    starts = [0] + starts if starts[0] != 0 else starts
    out = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(src)
        out.append((src.count('\n', 0, s) + 1, src[s:e]))
    return out


def _tables(chunk):
    t = set(REST_RE.findall(chunk))
    for a, b in TABLE_IN_HELPER_RE.findall(chunk):
        if a:
            t.add(a)
    return t


def scan_toctou(path, src):
    """[(line, table, why)] -- advisory candidates."""
    hits = []
    for start_line, body in _bodies(src):
        if not MONEY_RE.search(body):
            continue
        writes = list(WRITE_METHOD_RE.finditer(body))
        if not writes:
            continue
        tables = _tables(body)
        if not tables:
            continue
        # A read is a /rest/v1/<table> reference that is NOT the write's
        # own url. Approximated by: more rest references than writes.
        n_rest = len(REST_RE.findall(body)) + len(TABLE_IN_HELPER_RE.findall(body))
        if n_rest <= len(writes):
            continue
        if CAS_RE.search(body):
            continue
        w = writes[0]
        hits.append((start_line + body.count('\n', 0, w.start()),
                      ','.join(sorted(tables)),
                      'money-shaped body reads and writes the same table(s) '
                      'with no compare-and-set, count-exact, rpc, upsert, '
                      'idempotency or lock guard in the body'))
    return hits


# ── CATEGORY 2 ───────────────────────────────────────────────────────────
# Unauthenticated + expensive + unthrottled. All three must hold.

AUTH_RE = re.compile(
    r"(_lib/auth|_lib/license|verifySessionToken|verifyPreAuthToken"
    r"|tokenFromRequest|validateLicenseKey|credentialStillActive"
    r"|hasRole|roleSet|whoami|requireRole|verifyStripeSignature"
    r"|stripe-signature|CRON_SECRET|x-cron|verifyPin)")

EXPENSIVE_RE = re.compile(
    r"(api\.anthropic\.com|anthropic|claude-|api\.openai\.com|openai"
    r"|api\.groq\.com|groq|courtlistener|sendgrid|resend\.com|postmark"
    r"|nodemailer|puppeteer|pdfkit|PDFDocument|sharp\(|/v1/messages)")

THROTTLE_RE = re.compile(
    r"(ai-rate-limit|checkAiRateLimit|rate_limit|rateLimit|RateGate"
    r"|ai-safeguards|throttle|MIN_SECONDS_BETWEEN|rpm|RPM)")

HANDLER_RE = re.compile(r"module\.exports\s*=\s*(?:async\s*)?(?:function)?\s*\(")


def scan_ratelimit(path, src):
    """[(line, what, why)] -- advisory candidates. _lib/ modules are not
    endpoints and are excluded: a library is reached THROUGH a handler, so
    judging its reachability in isolation would report every helper as an
    unauthenticated endpoint."""
    if '/_lib/' in path or path.endswith('/_lib'):
        return []
    if not HANDLER_RE.search(src):
        return []
    exp = EXPENSIVE_RE.search(src)
    if not exp:
        return []
    if AUTH_RE.search(src):
        return []
    if THROTTLE_RE.search(src):
        return []
    return [(src.count('\n', 0, exp.start()) + 1, exp.group(0),
              'request handler performs an expensive external call with no '
              'auth-gate reference and no throttle reference in the file')]


def run(repo, categories=(1, 2)):
    considered, skipped = population(repo)
    if considered is None:
        print('COULD NOT RUN: git ls-files failed in %s' % repo)
        return EXIT_COULD_NOT_RUN, None
    if not considered:
        print('COULD NOT RUN: zero files in the considered population -- a '
              'sweep over nothing is not a clean sweep')
        return EXIT_COULD_NOT_RUN, None

    cands = {1: [], 2: []}
    nbytes = 0
    unreadable = []
    for p in considered:
        full = os.path.join(repo, p)
        try:
            with open(full, encoding='utf-8', errors='strict') as f:
                src = f.read()
        except Exception as e:
            unreadable.append((p, str(e)[:80]))
            continue
        nbytes += len(src.encode('utf-8', 'replace'))
        if 1 in categories:
            for ln, tbl, why in scan_toctou(p, src):
                cands[1].append((p, ln, tbl, why))
        if 2 in categories:
            for ln, what, why in scan_ratelimit(p, src):
                cands[2].append((p, ln, what, why))

    print('COVERAGE, MEASURED, NOT ASSERTED')
    print('  CONSIDERED : %d file(s)' % len(considered))
    print('  SKIPPED    : %d file(s), every one with a named reason'
          % len(skipped))
    reasons = {}
    for _, why in skipped:
        reasons[why] = reasons.get(why, 0) + 1
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print('               %6d  %s' % (n, why))
    print('  BYTES READ : %d' % nbytes)
    print('  UNREADABLE : %d' % len(unreadable))
    for p, why in unreadable:
        print('               %s -- %s' % (p, why))
    print('')

    if 1 in categories:
        print('CATEGORY 1 -- TOCTOU ON MONEY OPERATIONS: %d candidate(s), '
              'ADVISORY BY RULE DESIGN' % len(cands[1]))
        for p, ln, tbl, why in cands[1]:
            print('  %s:%d  [%s]' % (p, ln, tbl))
            print('      %s' % why)
    if 2 in categories:
        print('CATEGORY 2 -- MISSING RATE LIMITING ON UNAUTHENTICATED '
              'EXPENSIVE ENDPOINTS: %d candidate(s), ADVISORY BY RULE DESIGN'
              % len(cands[2]))
        for p, ln, what, why in cands[2]:
            print('  %s:%d  [%s]' % (p, ln, what))
            print('      %s' % why)
    print('')
    print('EVERY CANDIDATE ABOVE IS A SHAPE, NOT A VERDICT. Neither rule can '
          'see whether two statements interleave under real concurrency, nor '
          'whether a route is reachable unauthenticated in production, nor '
          'whether an env var is set in Vercel. Triage by reading.')

    if unreadable:
        print('EXIT 2: %d file(s) could not be read, so this run did NOT '
              'cover the tree. Not reported as clean.' % len(unreadable))
        return EXIT_COULD_NOT_RUN, cands
    total = sum(len(cands[c]) for c in categories)
    return (EXIT_CANDIDATES if total else EXIT_CLEAN), cands


# ── SELFTEST ─────────────────────────────────────────────────────────────
# Fixtures in BOTH directions for every arm, per the standing rule that a
# check which has only ever been shown to pass is not yet a check.

def selftest():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   %s' % name)
        else:
            bad[0] += 1
            print('  FAIL %s' % name)

    racy = """
async function settle(client, id) {
  const r = await fetch(client.rest('ledger?id=eq.' + id + '&select=balance'));
  const row = await r.json();
  const next = row[0].balance - 100;
  await fetch(client.rest('ledger?id=eq.' + id), {
    method: 'PATCH',
    headers: { Prefer: 'return=minimal' },
    body: JSON.stringify({ balance: next })
  });
}
"""
    ck('T1 read-then-write of the SAME money table with no guard is a '
       'candidate', len(scan_toctou('api/x.js', racy)) == 1)

    guarded = racy.replace("Prefer: 'return=minimal'",
                           "Prefer: 'return=representation'")
    ck('T2 KNOWN-GOOD CONTROL -- the identical code with a '
       'return=representation guard is NOT a candidate, so the rule is '
       'detecting the missing guard rather than the read-write pair',
       scan_toctou('api/x.js', guarded) == [])

    cas = racy.replace("'ledger?id=eq.' + id)",
                        "'ledger?id=eq.' + id + '&balance=eq.' + prior)")
    ck('T2b KNOWN-GOOD CONTROL -- a compare-and-set filter on the value '
       'that was read also clears the rule',
       scan_toctou('api/x.js',
                    cas.replace("Prefer: 'return=minimal'",
                                "Prefer: 'count=exact'")) == [])

    upsert = racy.replace("client.rest('ledger?id=eq.' + id)",
                           "client.rest('ledger?on_conflict=id')")
    ck('T2c KNOWN-GOOD CONTROL, ADDED AFTER A REAL FALSE POSITIVE -- a '
       'PostgREST upsert spelled on_conflict (underscore, not the SQL "on '
       'conflict") clears the rule. The first version missed this spelling '
       'and reported api/legal-citator.js:319 as unguarded when its write '
       'is an upsert with resolution=merge-duplicates',
       scan_toctou('api/x.js', upsert) == [])

    merge = racy.replace("Prefer: 'return=minimal'",
                          "Prefer: 'resolution=merge-duplicates,return=minimal'")
    ck('T2d KNOWN-GOOD CONTROL -- the merge-duplicates resolution Prefer '
       'header also clears the rule',
       scan_toctou('api/x.js', merge) == [])

    # ── A NAMED, LOCKED LIMITATION, not a passing arm pretending to be one.
    # CAS_RE is tested against the whole BODY, so ONE guarded write masks an
    # UNGUARDED write in the same function. This is not hypothetical: it is
    # exactly what happened to api/legal-citator.js after T2c's fix. That
    # file's handler contains a correctly-upserted cache write AND a
    # read-modify-write counter increment
    # (`{ [counterField]: current + 1 }` with an id-only filter), and the
    # upsert now clears the whole body -- so the tool no longer flags a real
    # lost-update defect that this role found BY READING and filed anyway.
    # Asserted here so the next session cannot read "3 candidates" as "3
    # unguarded writes exist". Fixing it properly needs per-write-statement
    # scoping, which needs a JS parser rather than a regex; that is a real
    # next step, recorded rather than silently absorbed.
    masked = racy.replace(
        "  await fetch(client.rest('ledger?id=eq.' + id), {",
        "  await fetch(client.rest('audit?on_conflict=id'), { method: 'POST' });\n"
        "  await fetch(client.rest('ledger?id=eq.' + id), {")
    ck('T2e LOCKED LIMITATION -- GUARD SCOPE IS THE WHOLE BODY: one guarded '
       'write in the same function MASKS a genuinely unguarded money write, '
       'so this arm asserts the FALSE NEGATIVE rather than a pass. Real '
       'instance: api/legal-citator.js. Needs per-statement scoping (a JS '
       'parser) to fix',
       scan_toctou('api/x.js', masked) == [])

    nomoney = racy.replace('balance', 'nickname')
    ck('T3 KNOWN-GOOD CONTROL -- the same read-then-write shape with no '
       'money-bearing field is NOT a candidate (the category is money '
       'operations, not every unguarded write)',
       scan_toctou('api/x.js', nomoney) == [])

    readonly = """
async function show(client, id) {
  const r = await fetch(client.rest('ledger?id=eq.' + id + '&select=balance'));
  return (await r.json())[0].balance;
}
"""
    ck('T4 KNOWN-GOOD CONTROL -- a pure read of a money table is NOT a '
       'candidate', scan_toctou('api/x.js', readonly) == [])

    naked = """
module.exports = async (req, res) => {
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST', body: JSON.stringify({ model: 'claude-x' }) });
  res.status(200).json(await r.json());
};
"""
    ck('T5 an unauthenticated handler calling a paid LLM with no throttle '
       'is a candidate', len(scan_ratelimit('api/x.js', naked)) == 1)

    authed = naked.replace('const r = await',
                            "const s = require('./_lib/auth');\n  const r = await")
    ck('T6 KNOWN-GOOD CONTROL -- the identical handler WITH an auth '
       'reference is NOT a candidate', scan_ratelimit('api/x.js', authed) == [])

    throttled = naked.replace('const r = await',
                               "await checkAiRateLimit(appId);\n  const r = await")
    ck('T7 KNOWN-GOOD CONTROL -- the identical handler WITH a throttle '
       'reference is NOT a candidate, so T5 is detecting the missing '
       'throttle and not merely the LLM call',
       scan_ratelimit('api/x.js', throttled) == [])

    # Note the SECOND replacement: the first draft of this fixture swapped
    # only the URL and still said model: 'claude-x', which the rule
    # correctly matched on `claude-`. T8 failed, and the FIXTURE was wrong,
    # not the rule -- kept as a comment because a fixture that was quietly
    # corrected teaches nothing about what the rule actually keys on.
    cheap = naked.replace('https://api.anthropic.com/v1/messages',
                           '/rest/v1/notes').replace("model: 'claude-x'",
                                                     "note: 'hello'")
    ck('T8 KNOWN-GOOD CONTROL -- an unauthenticated handler doing something '
       'CHEAP is NOT a candidate (the category is expensive endpoints)',
       scan_ratelimit('api/x.js', cheap) == [])

    ck('T9 a _lib module is NOT judged as an endpoint even when it matches '
       'everything else, because a library is reached THROUGH a handler',
       scan_ratelimit('api/_lib/thing.js', naked) == [])

    ck('T10 a file with no handler export is NOT judged as an endpoint',
       scan_ratelimit('api/x.js', naked.replace('module.exports = async (',
                                                  'function helper(')) == [])

    # The population deriver must count, not assert.
    repo = repo_root()
    considered, skipped = population(repo)
    ck('T11 the population is DERIVED from git ls-files at run time and is '
       'non-empty (%d considered, %d skipped-with-reason)'
       % (len(considered or []), len(skipped or [])),
       bool(considered) and bool(skipped))
    ck('T12 no file is both considered and skipped, and every skipped file '
       'carries a non-empty reason',
       not (set(considered) & {p for p, _ in skipped})
       and all(w.strip() for _, w in skipped))
    ck('T13 tests are excluded BY NAMED REASON rather than silently '
       '(.test.js files all land in skipped)',
       all(not p.endswith('.test.js') for p in considered)
       and any(p.endswith('.test.js') for p, _ in skipped))

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return EXIT_CLEAN if not bad[0] else EXIT_CANDIDATES


def main(argv):
    if '--selftest' in argv:
        return selftest()
    cats = (1, 2)
    if '--category' in argv:
        cats = (int(argv[argv.index('--category') + 1]),)
    rc, _ = run(repo_root(), cats)
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
