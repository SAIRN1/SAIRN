"""tools/blob_conversion_coverage.py -- how many stored jsonb blobs are built
through api/_lib/blob.js, and how many still hand the raw payload to the store?

    python tools/blob_conversion_coverage.py
    python tools/blob_conversion_coverage.py --list RAW
    python tools/blob_conversion_coverage.py --repin      # after a real change

── WHY THIS TOOL EXISTS AND NOT JUST A GREP ────────────────────────────────
Item 94's per-branch blob migration was declared COMPLETE on 2026-09-26 with a
two-line measurement in the commit message:

    grep -c "storedBlob(payload"        16 -> 28
    grep -c "Object.assign({}, payload)" 12 -> 0

The second number is real and it proves nothing. `.` is a wildcard in a grep
pattern, so `Object.assign({}, payload)` requires SOME character then `)`
immediately after `payload` -- and every remaining site in the file is
`Object.assign({}, payload, { ... })`, a COMMA. The pattern could not match the
sites that were left, so it was guaranteed to report 0 the moment the sites it
COULD match were converted. A completion proof whose denominator excludes the
remainder is not a weak measurement, it is a measurement of something else.

Re-measured with the shape pinned rather than the punctuation:
`data: payload` appears 65 times and `Object.assign({}, payload, {...})` 12
more, against 28 conversions. The migration was reported complete at roughly a
quarter done.

── WHAT A "STORED BLOB SITE" IS HERE, STATED SO THE NUMBER IS READABLE ─────
A site is a `data:` property inside an object that ALSO carries `license_hash`
-- that pairing is what makes it a tenant-scoped row going to the store rather
than an arbitrary local object called data. Sites are then classified:

  CONVERTED  the expression derives from storedBlob(...)
  RAW        the raw request payload goes straight in (`data: payload`)
  SPREAD     Object.assign({}, payload, {...}) -- payload copied, then
             overridden. The override direction is SAFE for column shadowing
             and does nothing at all about the scope keys.
  NESTED     `data: payload.data` -- the caller supplies the blob already
             separated; a different shape with a different argument, counted
             apart rather than folded in either direction.
  BUILT      an object literal or a named variable assembled field by field.
             IMMUNE and gains nothing from conversion -- blob.js says so.

── WHAT THE CONVERSION ACTUALLY BUYS, SO NOBODY CONVERTS FOR NEATNESS ──────
storedBlob strips NEVER_STORED -- license_hash, app_id, p_license_hash -- on
every branch, always. A payload carrying `license_hash` rides into a RAW or
SPREAD blob and is echoed back on read as a field the row's real tenant column
contradicts. It also strips the branch's own COLUMN keys, which is what stops a
payload copy of a mapped column shadowing the real one when a read spreads the
blob last.

── WHAT IT CANNOT DO, AND THE FIRST ONE IS THE IMPORTANT ONE ───────────────
IT CANNOT CHOOSE THE COLUMN KEYS. Which payload fields are real columns is a
fact about each table, and blob.js keeps that list per-branch deliberately: a
global list would strip real data somewhere (sd_slabs and every mech_ record
keep `id` INSIDE data on purpose, because their reads return `x.data` whole).
So this tool reports which sites are unconverted; it never says what to pass,
and a converter must read the branch's own READ to derive the list.

It is a RATCHET, not a pass/fail, pinned to docs/blob-conversion-coverage.json.
The honest state is nowhere near closed, and a check that simply failed would
sit permanently red -- which is the state that gets scrolled past. OK means "no
worse than pinned", printed with the reminder that a ratchet is not a pass. An
absent or unparseable pin is exit 2 COULD NOT TELL, never 0.

It also cannot see a blob built in a helper this file calls, cannot tell a
harmless RAW site (a table whose read returns x.data whole and whose callers
never post a scope key) from a harmful one, and has no opinion on whether any
given row NEEDS the strip. That judgement is not automatable and is not
attempted.
"""
import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = os.path.join(REPO, 'docs', 'blob-conversion-coverage.json')
API = os.path.join(REPO, 'api')

# The pairing that makes a `data:` property a tenant-scoped stored row. Both
# spellings of the scope column appear in this codebase's write bodies.
SCOPE_NEAR = re.compile(r'license_hash|p_license_hash')
DATA_AT = re.compile(r'\bdata:\s*')


# A NAIVE `[^,\n]+` CAPTURE GOT THIS WRONG AND REPORTED SPREAD 0, which is the
# same class of defect this whole tool exists to expose. `data: Object.assign({},
# payload, { x: 1 })` was truncated at the FIRST comma to `Object.assign({}`, so
# every inline spread classified as BUILT -- a checker built to catch a
# punctuation-blind grep, itself blinded by punctuation. The expression is now
# read with the brackets balanced, so a comma inside one does not end it.
def _expr_at(line, start):
    depth = 0
    for j in range(start, len(line)):
        c = line[j]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                return line[start:j].strip()
            depth -= 1
        elif c == ',' and depth == 0:
            return line[start:j].strip()
    return line[start:].strip()


class CouldNotTell(Exception):
    pass


def api_files():
    """Every non-test .js under api/, AT ANY DEPTH.

    ── IT WAS A FLAT os.listdir AND THE UNIVERSE WAS A THIRD OF api/ ─────────
    Routed by cody, 2026-10-14, and the measurement is why it is a defect and
    not a preference: `os.listdir(API)` saw 50 files where a recursive walk
    sees 179, so **129 files were outside the universe this tool reports
    coverage over** -- every route under api/_lib/, api/agent/, api/sairncash/,
    api/sairndental/ and the rest. Two of them are live `data:` write sites:
    api/_lib/sd-store.js:166 and api/sairndental/public-complaint-submit.js:136.

    A COVERAGE TOOL WITH A SILENTLY NARROW UNIVERSE IS THE WORST SHAPE THIS
    REPO HAS A NAME FOR. It did not report "I only looked at the top level";
    it reported a conversion percentage, over a denominator that excluded the
    files most likely to differ -- the shared store helper and the per-app
    routes. "N of N converted" read as complete. This is the
    denominator-over-the-subset-you-looked-at error, and the fact that the
    count LOOKED plausible is exactly what kept it alive.

    node_modules is pruned because it is vendored third-party code this
    tool's conventions do not apply to; nothing else is excluded, and a
    directory this walk cannot read raises rather than being skipped.
    """
    if not os.path.isdir(API):
        raise CouldNotTell('api/ does not exist, so nothing was scanned')
    out = []
    for dirpath, dirnames, filenames in os.walk(API):
        # Pruned in place so os.walk does not descend. Named, not silent.
        dirnames[:] = [d for d in sorted(dirnames) if d != 'node_modules']
        for n in sorted(filenames):
            if not n.endswith('.js') or n.endswith('.test.js'):
                continue
            out.append(os.path.join(dirpath, n))
    if not out:
        raise CouldNotTell('api/ holds no non-test .js file at any depth -- the '
                           'layout moved and NOTHING was scanned. This is not '
                           '"no sites".')
    return sorted(out)


def classify(expr, at, bound_kind):
    """CONVERTED / RAW / SPREAD / NESTED / BUILT for one `data:` expression.

    INLINE SPELLINGS ARE JUDGED FIRST, then the nearest binding in scope.
    CONVERTED is tested before SPREAD and that order is load-bearing: a properly
    converted override site is `Object.assign(storedBlob(payload, ['id']),
    {...})` -- stripped, THEN overridden -- which is spread-SHAPED and correct.
    Asking SPREAD first would score every correct override site as a gap.
    """
    e = expr.strip()
    if 'storedBlob(' in e:
        return 'CONVERTED'
    if e in ('payload', 'mPayload'):
        return 'RAW'
    if re.match(r'^Object\.assign\(\{\s*\}\s*,\s*(?:payload|mPayload)\b', e):
        return 'SPREAD'
    if re.match(r'^payload\.[A-Za-z_]', e):
        return 'NESTED'
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', e):
        k = bound_kind(e, at)
        if k:
            return k
    return 'BUILT'


# ── THE SCOPE WINDOW WAS A LINE COUNT, AND A LINE COUNT CANNOT SEE A BODY ───
# Fixed 2026-10-16 (cc b16). `scan_one` decided whether a `data:` site was a
# LICENCE-SCOPED WRITE by asking whether `license_hash` appeared in
# `lines[i-4:i+3]` -- a flat seven-line window, three either side. That is the
# b24 bug from fourth's branch census arriving in a different tool, and it is
# wrong in the direction that matters for a RATCHET: a write body the window
# cannot see is a site the coverage ratio never divides by, so the ratio
# OVERSTATES conversion.
#
# MEASURED BEFORE THE FIX, over the real api/ tree: of 81 `data:` sites whose
# expression is a WRITE shape (storedBlob(, payload, mPayload, a payload
# spread, payload.<field>), 62 fell inside the seven-line window and 19 FELL
# OUTSIDE IT. Two were read by hand and both are real write bodies:
#
#   api/sd-data.js:16001  body: JSON.stringify({ data: payload, ... })
#                         a PATCH on leg_merch_units. `data: payload` RAW --
#                         the exact thing this tool counts -- and the
#                         license_hash is at :15995, SIX LINES UP, in the
#                         rest() URL rather than in the body at all.
#   api/sd-data.js:8880   data: payload.data || {} inside an rf_cert_rules
#                         upsert whose `license_hash: licHash` is at :8876,
#                         FOUR lines up. One line outside the window.
#
# WIDENING THE WINDOW IS NOT THE FIX AND WOULD BE THE SAME MISTAKE. A wider
# count bleeds across adjacent bodies: `api/sd-data.js` has handlers packed
# three to a dozen lines, so at +-10 a `data:` in a READ response would be
# scoped by the WRITE above it. That is item 7 -- a fix re-qualified against
# the target rather than copied -- and the target here is a file where the
# distance distribution runs to +-53 with no gap to cut at.
#
# SO THE BOUND IS STRUCTURAL, the same shape as the census's R1 and
# re-qualified for this subject rather than copied:
#
#   S1  the BODY is the object literal the `data:` sits inside, found by
#       walking braces backward to the enclosing `{` and forward to its match.
#       No line count anywhere.
#   S2  the URL is the argument span of the `await fetch(` that body belongs
#       to, read by balancing parens -- because licence scoping is frequently
#       expressed ONLY in the URL (`?license_hash=eq.` + enc(licHash)), which
#       is what :16001 is.
#   S3  a site whose body CANNOT be bounded is its own THIRD STATE,
#       UNRESOLVED-SCOPE. It is never silently included and never silently
#       excluded, because either default is a number nobody can check.
#
# A `data:` on a comment line is not a site at all, which removes the prose
# hits the old window counted (`data: payload` inside an explanatory sentence
# at :1064 and :17271 among them).
SCOPE_BODY_BOUNDED = True       # ablation toggle; False restores the 7-line window


def _enclosing_body(src, off):
    """(start, end) of the object literal containing `off`, or None.

    Backward to the `{` that is not closed before `off`, then forward to its
    match. Returns None rather than a guess when either walk runs out -- S3.
    """
    depth = 0
    start = None
    i = off - 1
    while i >= 0:
        c = src[i]
        if c == '}':
            depth += 1
        elif c == '{':
            if depth == 0:
                start = i
                break
            depth -= 1
        i -= 1
    if start is None:
        return None
    depth = 0
    j = start
    while j < len(src):
        c = src[j]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return (start, j + 1)
        j += 1
    return None                 # unbalanced to EOF -- S3


def _fetch_url_span(src, body_start, back=6000):
    """The argument text of the `await fetch(` whose CALL CONTAINS `body_start`.

    S2, and the containment test is the whole of it. The first draft took the
    nearest PRECEDING fetch regardless of whether the body was inside it, and
    that is a proximity rule wearing a structural one: a READ response body
    (`res.json({ ok: true, data: rows })`) sits a few lines AFTER a licence-
    scoped fetch, so every read in the file became a licence-scoped write site.
    Measured: that draft reported 593 sites against the old window's 266, and
    the inflation was reads.

    So the fetch's full call span is balanced and the body must lie INSIDE it.
    Empty string otherwise -- an ordinary condition, not a could-not-tell: not
    every `data:` belongs to a fetch. S3 is decided by the caller, which only
    reaches here once the body DID bound.
    """
    lo = max(0, body_start - back)
    best = ''
    for m in re.finditer(r'await\s+fetch\s*\(', src[lo:body_start]):
        k = lo + m.end()
        depth = 1
        j = k
        while j < len(src) and depth:
            if src[j] == '(':
                depth += 1
            elif src[j] == ')':
                depth -= 1
            j += 1
        if depth:
            continue                 # unbalanced to EOF; not a usable span
        if k <= body_start < j:
            best = src[k:j]          # the innermost containing call wins
    return best


def _line_offsets(src):
    """offset of the start of each 1-based line, index 0 unused."""
    offs = [0, 0]
    for ln in src.split('\n')[:-1]:
        offs.append(offs[-1] + len(ln) + 1)
    return offs


def scope_state(src, lines, offs, i, col, bounded=None):
    """'IN' | 'OUT' | 'UNRESOLVED' for one `data:` site.

    `bounded` None means use the module toggle; False is the ablation's
    seven-line window, kept so --ablate can measure what S1-S3 buy.
    """
    use = SCOPE_BODY_BOUNDED if bounded is None else bounded
    if not use:
        window = '\n'.join(lines[max(0, i - 4):i + 3])
        return 'IN' if SCOPE_NEAR.search(window) else 'OUT'
    off = offs[i] + col
    span = _enclosing_body(src, off)
    if span is None:
        return 'UNRESOLVED'
    body = src[span[0]:span[1]]
    if SCOPE_NEAR.search(body):
        return 'IN'
    if SCOPE_NEAR.search(_fetch_url_span(src, span[0])):
        return 'IN'
    return 'OUT'


def scan_one(path):
    src = io.open(path, encoding='utf-8', errors='replace').read()
    lines = src.split('\n')
    offs = _line_offsets(src)
    # Names bound to a storedBlob() result, so `data: custData` is recognised as
    # converted. WITHOUT THIS THE TOOL UNDERCOUNTS CONVERSIONS -- the platform's
    # own convention is to bind the blob to a name one line above the write, so a
    # checker that only matched `data: storedBlob(...)` inline would have found 2
    # of 28 and accused every correct branch.
    # ── BINDINGS ARE RESOLVED PER LINE, NOT FILE-WIDE, AND THAT MATTERS ─────
    # The first version built one file-wide set of storedBlob names and one of
    # spread names. `dataBlob` IS BOUND TWICE in api/sd-data.js -- line 7111
    # `Object.assign({}, payload, norm.money)` and line 7208
    # `storedBlob(payload, ['id'])` -- so the file-wide set contained it as
    # converted, CONVERTED is tested first, and the unconverted rf_claims write
    # at 7134 scored as a conversion. A checker written to catch a
    # measurement that could not see its own remainder, undercounting its own
    # remainder. The nearest binding ABOVE the use site is the one in scope, so
    # that is the one consulted.
    binds = []   # (line_no, name, kind)
    for i, line in enumerate(lines, 1):
        for m in re.finditer(r'(?:(?:const|let|var)\s+)?([A-Za-z_][A-Za-z0-9_]*)'
                             r'\s*=\s*storedBlob\(', line):
            binds.append((i, m.group(1), 'CONVERTED'))
        for m in re.finditer(r'(?:(?:const|let|var)\s+)?([A-Za-z_][A-Za-z0-9_]*)'
                             r'\s*=\s*Object\.assign\(\s*storedBlob\(', line):
            binds.append((i, m.group(1), 'CONVERTED'))
        for m in re.finditer(r'(?:(?:const|let|var)\s+)?([A-Za-z_][A-Za-z0-9_]*)'
                             r'\s*=\s*Object\.assign\(\{\s*\}\s*,\s*'
                             r'([A-Za-z_][A-Za-z0-9_]*)\b', line):
            if m.group(2) in ('payload', 'mPayload'):
                binds.append((i, m.group(1), 'SPREAD'))
        for m in re.finditer(r'(?:(?:const|let|var)\s+)\s*([A-Za-z_][A-Za-z0-9_]*)'
                             r'\s*=\s*(payload|mPayload)\s*;', line):
            binds.append((i, m.group(1), 'RAW'))
        # ── A RE-BINDING TO SOMETHING ELSE MUST CLEAR THE OLD VERDICT ───────
        # THIS IS THE THIRD DEFECT OF THE SAME FAMILY IN THIS FILE and it is
        # recorded rather than quietly patched. `merged` is bound at
        # api/sd-data.js:2824 as a payload spread and AGAIN at :3649 as
        # `Object.assign({}, curData, {...})` -- curData, the STORED row, not the
        # request. The second binding matched none of the rules above, so the
        # nearest-binding lookup walked past it to the first and reported a
        # sd_quote_requests PATCH that never touches the payload as an
        # unconverted payload spread. An overcount is not safer than an
        # undercount; it is the same tool being wrong with more confidence.
        # Every OTHER binding is registered as BUILT so it can shadow correctly.
        for m in re.finditer(r'(?:(?:const|let|var)\s+)?([A-Za-z_][A-Za-z0-9_]*)'
                             r'\s*=\s*(?!=)', line):
            binds.append((i, m.group(1), 'BUILT'))

    def bound_kind(name, at):
        best = None
        for (ln, nm, kind) in binds:
            if nm == name and ln <= at and (best is None or ln > best[0]):
                best = (ln, kind)
        return best[1] if best else None

    rows = []
    rel = os.path.relpath(path, REPO).replace('\\', '/')
    for i, line in enumerate(lines, 1):
        # A `data:` inside an explanatory sentence is not a write site. The
        # seven-line window counted several, including `data: payload` in prose
        # at api/sd-data.js:1064 and :17271.
        if line.lstrip().startswith(('//', '*', '/*')):
            continue
        for m in DATA_AT.finditer(line):
            expr = _expr_at(line, m.end())
            if not expr:
                continue
            st = scope_state(src, lines, offs, i, m.start())
            if st == 'OUT':
                continue
            if st == 'UNRESOLVED':
                # NOT dropped and NOT counted as a site. Carried as its own
                # kind so `--list` can print it and the ratchet can refuse to
                # improve on the back of one (S3).
                rows.append({'file': rel, 'line': i, 'expr': expr,
                             'kind': 'UNRESOLVED-SCOPE'})
                continue
            kind = classify(expr, i, bound_kind)
            rows.append({'file': rel, 'line': i, 'expr': expr, 'kind': kind})
    return rows


def scan():
    rows = []
    for p in api_files():
        rows.extend(scan_one(p))
    if not rows:
        raise CouldNotTell('no `data:` property was found beside a license_hash '
                           'anywhere in api/ -- the write-body shape moved and '
                           'NOTHING was measured. This is not "no sites".')
    return rows


def totals(rows):
    t = {}
    for r in rows:
        t[r['kind']] = t.get(r['kind'], 0) + 1
    return t


def load_pin():
    if not os.path.isfile(PIN):
        raise CouldNotTell('%s does not exist, so this run has nothing to '
                           'ratchet against' % os.path.relpath(PIN, REPO))
    try:
        return json.load(io.open(PIN, encoding='utf-8'))
    except ValueError as e:
        raise CouldNotTell('%s will not parse (%s)' % (os.path.relpath(PIN, REPO), e))


# ── THE UNIVERSE LOCK ───────────────────────────────────────────────────────
# Added cc b10, 2026-10-14, with the fix to api_files(). Its arms are about
# the DISCOVERY and not the classification: a coverage tool's denominator is
# the thing that was silently wrong, and the one arm that matters is the
# ABLATION -- it puts the old flat os.listdir back and requires that the
# nested-file arm then FAILS. Without that arm, deleting the recursion and
# deleting the check would both "pass", which is the shape this repo's
# methodology forbids.
def run_selftest():
    import shutil
    import tempfile
    print('BLOB CONVERSION COVERAGE -- universe lock')
    bad = total = 0

    def check(label, got, want):
        nonlocal bad, total
        total += 1
        if got != want:
            bad += 1
            print('  LOCK FAILED  %s' % label)
            print('               wanted %r, got %r' % (want, got))

    tmp = tempfile.mkdtemp(prefix='blobcov-universe-')
    global API
    real_api = API
    try:
        # A fixture api/ tree: one top-level route, one NESTED route, a test
        # file, and a node_modules copy that must not be walked.
        def w(rel, body='exports.h = async (q, r) => { await put({ data: payload }); };\n'):
            p = os.path.join(tmp, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
            return p
        w('top.js')
        w('_lib/store.js')
        w('sairndental/public-complaint-submit.js')
        w('top.test.js')
        w('node_modules/vendor/index.js')

        API = tmp
        found = [os.path.relpath(p, tmp).replace(os.sep, '/')
                 for p in api_files()]

        check('a NESTED route is in the universe -- the routed defect: a flat '
              'os.listdir saw 50 of 179 files and excluded api/_lib/ entirely',
              '_lib/store.js' in found, True)
        check('...and a route nested TWO levels deep is too',
              'sairndental/public-complaint-submit.js' in found, True)
        check('a TOP-LEVEL route is still in the universe -- the fix widens, '
              'it does not relocate', 'top.js' in found, True)
        check('a .test.js file is NOT in the universe', 'top.test.js' in found,
              False)
        check('node_modules is NOT walked -- vendored third-party code is not '
              'subject to this repo\'s blob conventions',
              any('node_modules' in f for f in found), False)
        check('the universe is exactly the 3 real routes, so nothing else '
              'leaked in either', sorted(found),
              ['_lib/store.js', 'sairndental/public-complaint-submit.js',
               'top.js'])

        # THE ABLATION. Put the pre-fix flat listdir back and require the
        # nested arm to go RED. An arm that passes under both implementations
        # is not testing the fix.
        def flat_api_files():
            out = []
            for n in sorted(os.listdir(API)):
                if not n.endswith('.js') or n.endswith('.test.js'):
                    continue
                out.append(os.path.join(API, n))
            return out
        flat = [os.path.relpath(p, tmp).replace(os.sep, '/')
                for p in flat_api_files()]
        check('ABLATION: with the old flat os.listdir back, the nested route '
              'is ABSENT -- so the recursion is what fixes this and nothing '
              'else', '_lib/store.js' in flat, False)
        check('ABLATION: ...while the top-level route is present under BOTH, '
              'which is why the old code looked like it worked',
              'top.js' in flat, True)

        # AN EMPTY UNIVERSE IS A REFUSAL, NEVER "no sites". A coverage tool
        # that reports 0 of 0 converted is the always-passing shape.
        empty = tempfile.mkdtemp(prefix='blobcov-empty-')
        API = empty
        try:
            api_files()
            raised = False
        except CouldNotTell:
            raised = True
        check('an api/ with no .js file at ANY depth raises CouldNotTell '
              'rather than reporting an empty universe as "no sites"',
              raised, True)
        shutil.rmtree(empty, ignore_errors=True)

        API = os.path.join(tmp, 'does-not-exist')
        try:
            api_files()
            raised = False
        except CouldNotTell:
            raised = True
        check('an absent api/ raises too', raised, True)
    finally:
        API = real_api
        shutil.rmtree(tmp, ignore_errors=True)

    # ========== THE SCOPE RULE, FIXTURES IN BOTH DIRECTIONS (b16) ==========
    # Locked here rather than measured on the real file, because the rule they
    # hold was found BY measuring the real file and a criterion tuned on its
    # own subject is not a criterion. Each fixture is one synthetic handler.
    print('')
    print('  SCOPE RULE S1-S3 -- 13 arms. 4 require IN (one of them twice in')
    print('  one body), 4 require OUT, 1 requires UNRESOLVED, 1 requires NO')
    print('  SITE AT ALL, and 3 are the ablation with its own control.')
    print('  A rule that says IN to everything passes the four IN arms and')
    print('  turns every read in api/ into a licence-scoped write -- which is')
    print('  what the first draft of S2 did: 593 sites against the window 266.')

    def scope_of(body):
        lines = body.split(chr(10))
        offs = _line_offsets(body)
        out = []
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith(('//', '*', '/*')):
                continue
            for m in DATA_AT.finditer(line):
                if not _expr_at(line, m.end()):
                    continue
                out.append(scope_state(body, lines, offs, i, m.start()))
        return out

    def scope_of_window(body):
        lines = body.split(chr(10))
        offs = _line_offsets(body)
        out = []
        for i, line in enumerate(lines, 1):
            for m in DATA_AT.finditer(line):
                if not _expr_at(line, m.end()):
                    continue
                out.append(scope_state(body, lines, offs, i, m.start(),
                                       bounded=False))
        return out

    DEEP = (
        "      const r = await fetch(rest('t?on_conflict=license_hash'), {\n"
        "        method: 'POST',\n"
        "        headers: headers,\n"
        "        body: JSON.stringify({\n"
        "          license_hash: licHash,\n"
        "          a: 1,\n          b: 2,\n          c: 3,\n"
        "          d: 4,\n          e: 5,\n          f: 6,\n"
        "          data: payload\n"
        "        })\n      });\n")
    URLONLY = (
        "      const r = await fetch(rest(\n"
        "        'leg_merch_units?license_hash=eq.' + enc(licHash) +\n"
        "        '&merch_unit_id=eq.' + enc(String(payload.id))\n"
        "      ), {\n"
        "        method: 'PATCH',\n"
        "        headers: headers,\n"
        "        body: JSON.stringify({ data: payload, updated_at: nowISO() })\n"
        "      });\n")
    READ_AFTER = (
        "      const r = await fetch(rest('t?license_hash=eq.' + enc(licHash)), { headers });\n"
        "      const rows = await r.json();\n"
        "      res.status(200).json({ ok: true, data: rows });\n")
    READ_ADJACENT = (
        "      const r = await fetch(rest('t?license_hash=eq.' + enc(licHash)), { headers });\n"
        "      res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data) });\n")
    NO_KEY = "      const cache = { data: payload, at: nowISO() };\n"
    AFTER_CLOSE = (
        "      const r = await fetch(rest('t?license_hash=eq.' + enc(licHash)), { headers });\n"
        "      const later = { data: payload };\n")
    ONELINE = (
        "      await fetch(rest('t'), { body: JSON.stringify({ license_hash: licHash,"
        " data: storedBlob(payload, []) }) });\n")
    TWO_SITES = (
        "      await fetch(rest('t'), { body: JSON.stringify({\n"
        "        license_hash: licHash,\n"
        "        data: payload,\n"
        "        meta: { data: storedBlob(payload, []) }\n"
        "      }) });\n")
    REGEX = "const RE = /data: image/;\n"
    COMMENT = ("        // body: JSON.stringify({ license_hash: licHash,"
               " data: payload })\n")

    check('S1 IN: license_hash in the SAME body, eleven lines above the '
          '`data:` -- outside any seven-line window', scope_of(DEEP), ['IN'])
    check('S2 IN: the key is ONLY in the rest() URL and not in the body at '
          'all -- the real api/sd-data.js:16001 shape the window missed',
          scope_of(URLONLY), ['IN'])
    check('S2 OUT: a READ response body a few lines AFTER a licence-scoped '
          'fetch is NOT a write site -- the arm that caught the first draft '
          'of S2 taking the nearest preceding fetch regardless of containment',
          scope_of(READ_AFTER), ['OUT'])
    check('S2 OUT: ...and still OUT when the read response is immediately '
          'adjacent, which is where a line-count rule is least able to tell',
          scope_of(READ_ADJACENT), ['OUT'])
    check('OUT: a body with no license_hash anywhere and no enclosing fetch '
          'is not a licence-scoped write', scope_of(NO_KEY), ['OUT'])
    check('OUT: a licence-scoped fetch that CLOSED before this body -- the '
          'test is containment, not proximity', scope_of(AFTER_CLOSE), ['OUT'])
    check('S1 IN: a one-line body, the common case, must not regress',
          scope_of(ONELINE), ['IN'])
    check('S1 IN: TWO sites in one body are both IN -- the walk is per site, '
          'not per body', scope_of(TWO_SITES), ['IN', 'IN'])
    check('S3 UNRESOLVED: a `data:` with no enclosing brace at all is its own '
          'third state, never IN and never OUT. The one real instance is the '
          'data-URI REGEX at api/_lib/dental-photo-validation.js:14',
          scope_of(REGEX), ['UNRESOLVED'])
    check('a `data:` on a COMMENT line is NOT A SITE -- the seven-line window '
          'counted prose at api/sd-data.js:1064 and :17271',
          scope_of(COMMENT), [])

    check('ABLATION: with the seven-line window back, the eleven-line body '
          'reads OUT -- so S1 is what finds it and nothing else',
          scope_of_window(DEEP), ['OUT'])
    check('ABLATION: with the window back, the adjacent READ response reads '
          'IN -- so S2 containment is what excludes it',
          scope_of_window(READ_ADJACENT), ['IN'])
    check('ABLATION CONTROL: the one-line body reads IN under BOTH rules, '
          'which is exactly why the window looked like it worked',
          scope_of_window(ONELINE), ['IN'])

    print('  %d/%d arm(s) pass' % (total - bad, total))
    if bad:
        print('  THE UNIVERSE LOCK IS BROKEN. Every coverage figure this tool '
              'prints is over a denominator nothing is checking.')
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', metavar='KIND',
                    help='print every site of one KIND (RAW, SPREAD, NESTED, '
                         'CONVERTED, BUILT) and exit')
    ap.add_argument('--repin', action='store_true',
                    help='rewrite the pin to the CURRENT numbers. Only correct '
                         'after a real conversion, never to make a run pass')
    ap.add_argument('--why', metavar='TEXT', default='',
                    help='REQUIRED with --repin when `unconverted` RISES: what '
                         'rose and why that is acceptable, 40 characters '
                         'minimum. Written into the pin and read by the next '
                         'session. A downward re-pin needs none.')
    ap.add_argument('--selftest', action='store_true',
                    help='the universe lock: arms over api_files() discovery, '
                         'including an ablation that restores the old flat '
                         'os.listdir and requires the nested arm to go red')
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    try:
        rows = scan()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2
    t = totals(rows)

    if args.list:
        want = args.list.strip().upper()
        hits = [r for r in rows if r['kind'] == want]
        print('%s -- %d site(s)' % (want, len(hits)))
        for r in hits:
            print('   %s:%d  data: %s' % (r['file'], r['line'], r['expr'][:70]))
        return 0

    # UNCONVERTED IS THE NUMBER THAT MATTERS AND IT IS NAMED, not derived by a
    # reader from three others. BUILT is excluded on purpose -- blob.js states
    # that a field-by-field blob is already immune -- and NESTED is excluded
    # because it is a different argument, not a converted or unconverted one.
    unconverted = t.get('RAW', 0) + t.get('SPREAD', 0)
    print('STORED-BLOB CONVERSION COVERAGE (api/_lib/blob.js, item 94)')
    print('%d stored-blob site(s) across api/, by shape:' % len(rows))
    for k in ('CONVERTED', 'RAW', 'SPREAD', 'NESTED', 'BUILT'):
        print('   %-10s %3d' % (k, t.get(k, 0)))
    print('')
    print('UNCONVERTED (RAW + SPREAD): %d' % unconverted)
    print('CONVERTED:                  %d' % t.get('CONVERTED', 0))
    print('')
    print('BUILT is NOT a gap -- blob.js says a field-by-field blob is already')
    print('immune. NESTED (`data: payload.data`) is a different shape with a')
    print('different argument and is counted apart rather than folded either way.')
    print('')

    if args.repin:
        # -- AN UPWARD RE-PIN NEEDS A REASON, A DOWNWARD ONE DOES NOT (b16) --
        # The note this used to write was the same sentence every time, which
        # is a field that means nothing -- the shape the defect register
        # refused for `not-citable` and the push gate refused for a bare
        # override. A ratchet re-pinned UPWARD with no recorded reason is the
        # ratchet being switched off one notch at a time, and nothing
        # downstream can tell that from a real measurement change. Going DOWN
        # is the ratchet working and needs nothing.
        #
        # FOUND BY DOING IT, TWICE, WHILE WRITING THIS GUARD. Two patch
        # attempts failed on backslash escaping in their own match pattern,
        # left the OLD code in place, and the `--repin` run meant to test the
        # new refusal cheerfully raised the pin 48 -> 49 with the generic note
        # and exit 0. Both times the pin was restored from git. That is the
        # whole argument for this guard, made by accident, in the file it is
        # being added to.
        prev = None
        try:
            prev = load_pin().get('unconverted')
        except CouldNotTell:
            prev = None
        rising = isinstance(prev, int) and unconverted > prev
        why = (args.why or '').strip()
        if rising and len(why) < 40:
            sys.stderr.write(
                'REFUSING to re-pin UPWARD (%s -> %d) without --why.'
                % (prev, unconverted) + chr(10))
            sys.stderr.write(
                'A ratchet that can be raised silently is not a ratchet. Say '
                'what rose and why that is acceptable, in at least 40 '
                'characters -- it is written into the pin and read by the next '
                'session, which is the only thing standing between a real '
                'measurement change and a quiet retreat.' + chr(10))
            return 2
        direction = 'LEVEL'
        if isinstance(prev, int):
            direction = 'UP' if unconverted > prev else (
                'DOWN' if unconverted < prev else 'LEVEL')
        io.open(PIN, 'w', encoding='utf-8', newline=chr(10)).write(json.dumps({
            'unconverted': unconverted,
            'converted': t.get('CONVERTED', 0),
            'by_kind': t,
            'previous_unconverted': prev,
            'direction': direction,
            'why': why or None,
            'note': 'A RATCHET, not a target. unconverted must never rise. '
                    'Lower it by converting a site and re-pinning with '
                    '--repin, never to make a run pass. An UPWARD re-pin is '
                    'REFUSED without --why and the reason is kept in this '
                    'file; a downward one needs none.'
        }, indent=2) + chr(10))
        print('RE-PINNED %s to unconverted=%d converted=%d'
              % (direction, unconverted, t.get('CONVERTED', 0)))
        if why:
            print('  why: %s' % why)
        return 0

    try:
        pin = load_pin()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('The numbers above were measured; nothing was JUDGED. '
                         'This is NOT a clean run.\n')
        return 2

    was = pin.get('unconverted')
    if not isinstance(was, int):
        sys.stderr.write('COULD NOT TELL -- the pin carries no integer '
                         '`unconverted`, so there is nothing to compare.\n')
        return 2

    if unconverted > was:
        print('REGRESSION -- unconverted rose from %d to %d. A NEW raw or spread'
              % (was, unconverted))
        print('blob write was added. Convert it, or if it is genuinely correct')
        print('say why in the commit and re-pin deliberately.')
        return 1
    if unconverted < was:
        print('IMPROVED -- unconverted fell from %d to %d. Re-pin:' % (was, unconverted))
        print('   python tools/blob_conversion_coverage.py --repin')
        return 0
    print('OK -- no worse than pinned (%d unconverted).' % was)
    print('A RATCHET IS NOT A PASS. %d site(s) still hand the raw payload or a'
          % unconverted)
    print('payload copy to the store, so a posted license_hash still rides into')
    print('those blobs and is echoed back on read. This run says only that the')
    print('number did not get worse.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
