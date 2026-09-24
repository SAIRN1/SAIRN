"""tools/primitive_obsession_check.py -- three named shapes where a raw
primitive crosses a boundary unparsed, each already paid for on this platform.

    python tools/primitive_obsession_check.py             # report, exit 1 on a NEW one
    python tools/primitive_obsession_check.py --full      # every occurrence
    python tools/primitive_obsession_check.py --self-test # fixture lock only

Item 90 (parse-don't-validate / make illegal states unrepresentable), built
against the platform's own defects rather than the textbook's examples. One
tool, three detectors, because the three shapes are one mistake -- a value kept
as a raw string/number long past the point where it should have become a typed
fact -- and a reader hunting one should find its siblings.

── SHAPE 1: A MEASURED VALUE DEFENDED INTO A DEFAULT ──────────────────────
    Number(amount) || 0        parseFloat(fee) || 0

`Number('')` is 0, `Number('abc')` is NaN, and `|| 0` folds BOTH into the same
value as a legitimate zero. Three different facts -- "empty", "unreadable",
"measured zero" -- become one number, and the one number is money. SAIRNdental
shipped exactly this in addChargeEntry/addPaymentEntry ("MONEY IN, OR NOTHING.
NEVER A MEASURED ZERO", 2026-09-18): correct by caller, not by construction,
and the fourth caller without the guard would have stored a silent $0.

RELATIONSHIP TO tools/truthy_sum_check.py, STATED SO NOBODY MERGES THEM: that
tool finds `+ (x || 0)` with NO coercion (the guard never fires, `+`
concatenates). This shape is the complement -- coercion PRESENT, and the
default swallowing its failure. The two are disjoint by construction: one
requires Number to be absent, the other requires it present.

── SHAPE 2: A CONFIG READ WHERE Number('') IS 0 ───────────────────────────
    Number(process.env.SAIRN_X)

`SAIRN_X=''` -- a cleared but present env var -- converts to 0, silently. Where
zero is legal (a jitter, a grace period, a floor) that is a switched-off
feature that looks configured. api/_lib/safe-number.js's own header names
cron-jitter.js as the only one of six sites that handled this, and the five
rate-limiter sites as "correct BY ACCIDENT of an unrelated positivity
constraint". The fix is routing through configNumber(); this detector finds
the sites that have not.

── SHAPE 3: A LOCALE DATE STRING USED AS A DATA VALUE ─────────────────────
    date: new Date().toLocaleDateString()      if (a.date > b.date)

toLocaleDateString() is DISPLAY: its output ('9/24/2026', '24.09.2026',
'2026/9/24') depends on the viewer's locale, does not sort, and does not
compare -- '9/24/2026' > '10/1/2026' is true lexicographically and false in
time. Stored on a record it becomes a data value that every later comparison,
sort or filter silently mis-handles, and two devices in two locales write two
formats into one column. stonedesk.html's quote history stores exactly this
shape (`date: new Date().toLocaleDateString()`). The three date-comparison
defects item 90 cites are this shape at three sites. Direct concatenation into
HTML/print output is display and is NOT reported.

── THE BASELINE IS THE MECHANISM (same as truthy_sum_check) ───────────────
Real occurrences exist today and a checker reporting all of them forever sits
at exit 1 and gates nothing. Existing keys are grandfathered in
tools/primitive_obsession_baseline.json; the check fails on a NEW one. Burn one
down by parsing at the edge -- measureNumber/configNumber for shapes 1-2, an
ISO date (or a real timestamp) for shape 3.

── THE FIXTURE LOCK RUNS FIRST, EVERY TIME (cross-domain discipline 1) ────
Criteria are locked against synthetic fixtures in BOTH directions before any
real file is read, and the tool REFUSES (exit 2) to judge real data if a
fixture misclassifies. CRITERIA_VERSION stamps the rule set so a criteria
change is a visible event, not a drift.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, 'tools', 'primitive_obsession_baseline.json')

CRITERIA_VERSION = 1

# Shape 1: coercion whose failure is swallowed by a defaulting ||.
MEASURED_DEFAULT_RE = re.compile(
    r'\b(Number|parseFloat|parseInt)\s*\(\s*([^()]*(?:\([^()]*\)[^()]*)*)\)\s*\|\|\s*'
    r'(0(?![\w.])|[\'"][^\'"]*[\'"]|\d[\w.]*)')

# Shape 2: a config read straight off process.env.
ENV_NUMBER_RE = re.compile(
    r'\b(Number|parseFloat|parseInt)\s*\(\s*process\.env[.\[][^)]*\)')

# Shape 3a: locale date stored as a value -- assigned or set as a property.
LOCALE_STORE_RE = re.compile(
    r'([\w$\.\[\]\'"]+\s*[:=]\s*)new Date\([^)]*\)\s*\.\s*toLocaleDateString\s*\(')
# Shape 3b: locale date in a relational comparison, either side.
LOCALE_CMP_RE = re.compile(
    r'toLocaleDateString\s*\([^)]*\)\s*[<>]=?|[<>]=?\s*[\w$.]*toLocaleDateString')

BINARY_EXT = ('.zip', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.woff',
              '.woff2', '.ttf', '.mp4', '.xlsx', '.docx', '.pyc')

# Files that ARE the parse-at-the-edge fix or that quote the shapes to teach
# them. By path, never by content sniffing -- a content rule that tried to
# tell "quoted" from "real" is the regex-over-a-construct mistake this repo
# has paid for three times.
ALLOWED = {
    'api/_lib/safe-number.js',
    'tools/primitive_obsession_check.py',
    'tools/truthy_sum_check.py',
}


def strip_noncode(src):
    """Blank comments and string interiors, keeping line structure.

    Same rule and same reason as truthy_sum_check.strip_comments: a checker
    whose subject is code must not match the fix's own prose, whether that
    prose lives in a comment or in a refusal-message string. Quotes are kept
    so tokens still delimit; only contents go.

    THE ONE EXCEPTION: a template-literal or quoted PROPERTY KEY before a
    colon is not what shape 3 keys on (it matches the `=` / `:` OUTSIDE the
    string), so blanking interiors does not blind it.
    """
    out, i, n = [], 0, len(src)
    quote = None
    line_comment = False
    block_comment = False
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if line_comment:
            if c == '\n':
                line_comment = False
                out.append('\n')
            else:
                out.append(' ')
            i += 1
            continue
        if block_comment:
            if c == '*' and nxt == '/':
                block_comment = False
                out.append('  ')
                i += 2
                continue
            out.append('\n' if c == '\n' else ' ')
            i += 1
            continue
        if quote:
            if c == '\\' and i + 1 < n:
                out.append('  ')
                i += 2
                continue
            if c == quote:
                out.append(c)
                quote = None
            else:
                out.append('\n' if c == '\n' else ' ')
            i += 1
            continue
        if c == '/' and nxt == '/':
            line_comment = True
            out.append('  ')
            i += 2
            continue
        if c == '/' and nxt == '*':
            block_comment = True
            out.append('  ')
            i += 2
            continue
        if c in ('"', "'", '`'):
            quote = c
        out.append(c)
        i += 1
    return ''.join(out)


def scan_text(code):
    """Findings for one file's stripped code: (shape, line, token)."""
    findings = []
    lines = code.split('\n')
    for idx, line in enumerate(lines, 1):
        for m in MEASURED_DEFAULT_RE.finditer(line):
            arg = m.group(2).strip()
            # `Number(x || 0)` -- default INSIDE the coercion -- is the
            # truthy_sum shape's cousin but the || here belongs to the
            # argument, not to the result. Group 2 capturing a || means the
            # outer match mis-split; skip rather than misreport.
            findings.append(('measured-default', idx,
                             m.group(1) + '(' + arg[:40] + ')||' + m.group(3)))
        for m in ENV_NUMBER_RE.finditer(line):
            findings.append(('env-number', idx, m.group(0)[:60]))
        for m in LOCALE_STORE_RE.finditer(line):
            lhs = m.group(1).strip().rstrip(':=').strip()
            findings.append(('locale-date-value', idx, lhs[:40] + ' = toLocaleDateString'))
        for m in LOCALE_CMP_RE.finditer(line):
            findings.append(('locale-date-compare', idx, m.group(0)[:60]))
    return findings


# ── FIXTURES: both directions, locked before any real file is read ─────────
FIXTURES = [
    # (name, code, expected shapes)
    ('measured default on money',
     "var amt = Number(amount) || 0;", ['measured-default']),
    ('parseFloat with a numeric default',
     "cfg.fee = parseFloat(row.fee) || 25;", ['measured-default']),
    ('coercion with NO default is not this shape',
     "var amt = Number(amount);", []),
    ('validated-then-defaulted is still reported -- the || is the finding',
     "var n = parseInt(qty, 10) || 1;", ['measured-default']),
    ('env read straight through Number',
     "const t = Number(process.env.SAIRN_TIMEOUT_MS);", ['env-number']),
    ('env read through the safe helper is clean',
     "const t = configNumber('SAIRN_TIMEOUT_MS', 5000);", []),
    ('env number that ALSO defaults reports both shapes',
     "const t = Number(process.env.SAIRN_X) || 30;",
     ['measured-default', 'env-number']),
    ('locale date stored on a record',
     "var q = { date: new Date().toLocaleDateString(), total: t };",
     ['locale-date-value']),
    ('locale date assigned to a variable',
     "var today = new Date().toLocaleDateString();", ['locale-date-value']),
    ('locale date concatenated into display output is NOT reported',
     "w.document.write('<p>' + new Date().toLocaleDateString() + '</p>');", []),
    ('locale date compared relationally',
     "if (a.toLocaleDateString() > cutoff) { flag(); }",
     ['locale-date-compare']),
    ('an ISO date stored is clean',
     "var q = { date: new Date().toISOString() };", []),
    ('the shape inside a STRING is not code',
     "msg = 'the YTD reduce was Number(o.total) || 0 and that was the bug';", []),
    ('the shape inside a COMMENT is not code',
     "// old: charge = Number(amount) || 0\ncharge = measureNumber(amount);", []),
    ('a lone comparison operator near an unrelated call is clean',
     "if (count > limit) { refuse(); }", []),
]


def fixture_lock():
    """Every fixture must classify exactly, or nothing real gets judged."""
    failures = []
    for name, code, expected in FIXTURES:
        got = sorted(set(s for s, _l, _t in scan_text(strip_noncode(code))))
        if got != sorted(set(expected)):
            failures.append('  %s\n    expected %s, classified %s'
                            % (name, sorted(set(expected)) or '[]', got or '[]'))
    return failures


def tracked():
    out = subprocess.run(['git', 'ls-files', '*.html', '*.js'], cwd=REPO,
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace').stdout
    return [f for f in out.split('\n')
            if f.strip()
            and not f.startswith('archive/')
            and not f.startswith('docs/skill-backups/')
            and f not in ALLOWED
            and not f.lower().endswith(BINARY_EXT)]


def load_baseline():
    try:
        with io.open(BASELINE, encoding='utf-8') as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except FileNotFoundError:
        return {'criteria_version': CRITERIA_VERSION, 'keys': []}
    except Exception:
        return None


def main(argv):
    if '--self-test' in argv:
        f = fixture_lock()
        if f:
            print('FIXTURE LOCK FAILED:')
            print('\n'.join(f))
            return 2
        print('fixture lock: %d fixtures classify correctly (CRITERIA_VERSION %d)'
              % (len(FIXTURES), CRITERIA_VERSION))
        return 0

    # THE LOCK RUNS FIRST, EVERY REAL RUN. A tool whose criteria have drifted
    # must refuse to judge, not judge differently in silence.
    lockfail = fixture_lock()
    if lockfail:
        print('COULD NOT RUN: the fixture lock failed, so the criteria no '
              'longer classify the synthetic cases they were locked against. '
              'Nothing real was judged, and that is not a pass.')
        print('\n'.join(lockfail))
        return 2

    base = load_baseline()
    if base is None:
        print('COULD NOT RUN: %s is unreadable. A baseline that cannot be '
              'read makes every hit look new (or none) -- refusing rather '
              'than guessing.' % os.path.relpath(BASELINE, REPO))
        return 2
    if base.get('criteria_version') != CRITERIA_VERSION:
        print('COULD NOT RUN: the baseline was written for CRITERIA_VERSION '
              '%s and the tool is at %d. Re-baseline deliberately '
              '(--write-baseline) so the change is a visible event.'
              % (base.get('criteria_version'), CRITERIA_VERSION))
        return 2

    per_shape = {}
    found_keys = {}
    for f in tracked():
        try:
            with io.open(os.path.join(REPO, f), encoding='utf-8',
                         errors='replace') as fh:
                src = fh.read()
        except OSError:
            continue
        for shape, line, token in scan_text(strip_noncode(src)):
            key = f + '::' + shape + '::' + token
            found_keys.setdefault(key, []).append(line)
            per_shape.setdefault(shape, []).append((f, line, token))

    known = set(base.get('keys') or [])
    new = sorted(k for k in found_keys if k not in known)
    stale = sorted(k for k in known if k not in found_keys)

    # ── A WHOLE SHAPE VANISHING IS A REFUSAL, NOT A CELEBRATION ────────────
    # The backstop behind the fixture lock, added because this tool's own
    # sabotage probe proved the lock alone is not enough: skip the lock AND
    # blind a detector, and every key of that shape reports "fixed since
    # baseline" while the tool exits 0 -- CLEAN over shapes it can no longer
    # see. Real fixes retire keys one at a time; a detector going blind
    # retires an entire shape at once. So a shape with baseline keys and ZERO
    # current occurrences refuses: either the platform genuinely fixed every
    # instance -- re-baseline deliberately, which makes it a visible event --
    # or a detector died, which must never look like progress. This is the
    # "nothing announces the day a check stops testing anything" convention
    # as a positive control on real data.
    base_shapes = set(k.split('::', 2)[1] for k in known if k.count('::') >= 2)
    live_shapes = set(per_shape)
    dead_shapes = sorted(base_shapes - live_shapes)
    if dead_shapes and '--write-baseline' not in argv:
        print('COULD NOT RUN: shape(s) with baselined occurrences found ZERO '
              'matches this run: %s. A detector that went blind is '
              'indistinguishable from a platform that fixed every instance, '
              'and only one of those is a pass. If every instance is truly '
              'gone, re-baseline with --write-baseline so the change is a '
              'deliberate, visible event.' % ', '.join(dead_shapes))
        return 2

    if '--write-baseline' in argv:
        with io.open(BASELINE, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump({'criteria_version': CRITERIA_VERSION,
                       'keys': sorted(found_keys)}, fh, indent=1)
        print('baseline written: %d keys grandfathered. Every one is a real '
              'occurrence of a named anti-pattern -- grandfathered means '
              '"predates the check", never "fine".' % len(found_keys))
        return 0

    print('primitive-obsession check (CRITERIA_VERSION %d) -- three shapes, '
          'each paid for on this platform' % CRITERIA_VERSION)
    for shape in sorted(per_shape):
        print('  %-22s %4d occurrence(s)' % (shape, len(per_shape[shape])))
    print('  distinct keys      : %d' % len(found_keys))
    print('  grandfathered      : %d' % len(known & set(found_keys)))
    print('  fixed since baseline: %d' % len(stale))
    if '--full' in argv:
        for shape in sorted(per_shape):
            print('\n-- %s --' % shape)
            for f, line, token in per_shape[shape]:
                print('  %s:%d  %s' % (f, line, token))
    if new:
        print('\n%d NEW occurrence(s) -- not in the baseline:' % len(new))
        for k in new[:40]:
            f, shape, token = k.split('::', 2)
            print('  %s:%s  [%s]  %s' % (f, found_keys[k][0], shape, token))
        if len(new) > 40:
            print('  ... and %d more' % (len(new) - 40))
        print('\nParse at the edge instead: measureNumber/configNumber '
              '(api/_lib/safe-number.js) for the number shapes, an ISO date '
              'for the locale one. If a hit is genuinely correct, add its key '
              'to %s with a reason in the commit.' % os.path.relpath(BASELINE, REPO))
        return 1
    print('CLEAN -- no occurrence that is not already grandfathered.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
