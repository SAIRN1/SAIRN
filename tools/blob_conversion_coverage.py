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
    if not os.path.isdir(API):
        raise CouldNotTell('api/ does not exist, so nothing was scanned')
    out = []
    for n in sorted(os.listdir(API)):
        if not n.endswith('.js') or n.endswith('.test.js'):
            continue
        out.append(os.path.join(API, n))
    if not out:
        raise CouldNotTell('api/ holds no non-test .js file -- the layout moved '
                           'and NOTHING was scanned. This is not "no sites".')
    return out


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


def scan_one(path):
    src = io.open(path, encoding='utf-8', errors='replace').read()
    lines = src.split('\n')
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
    for i, line in enumerate(lines, 1):
        for m in DATA_AT.finditer(line):
            expr = _expr_at(line, m.end())
            if not expr:
                continue
            # The scope key may sit on the same line (the common one-line body)
            # or a line or two away in a multi-line body literal.
            window = '\n'.join(lines[max(0, i - 4):i + 3])
            if not SCOPE_NEAR.search(window):
                continue
            kind = classify(expr, i, bound_kind)
            rows.append({'file': os.path.relpath(path, REPO).replace('\\', '/'),
                         'line': i, 'expr': expr, 'kind': kind})
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', metavar='KIND',
                    help='print every site of one KIND (RAW, SPREAD, NESTED, '
                         'CONVERTED, BUILT) and exit')
    ap.add_argument('--repin', action='store_true',
                    help='rewrite the pin to the CURRENT numbers. Only correct '
                         'after a real conversion, never to make a run pass')
    args = ap.parse_args(argv)

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
        io.open(PIN, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            'unconverted': unconverted,
            'converted': t.get('CONVERTED', 0),
            'by_kind': t,
            'note': 'A RATCHET, not a target. unconverted must never rise. '
                    'Lower it by converting a site and re-pinning with '
                    '--repin, never to make a run pass.'
        }, indent=2) + '\n')
        print('RE-PINNED to unconverted=%d converted=%d'
              % (unconverted, t.get('CONVERTED', 0)))
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
