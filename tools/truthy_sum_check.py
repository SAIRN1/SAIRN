"""A numeric fold that adds `(x || 0)` without coercing it concatenates a string.

    python tools/truthy_sum_check.py             # report, exit 1 on a new one
    python tools/truthy_sum_check.py --full      # every occurrence
    python tools/truthy_sum_check.py --quiet     # exit code only

WHY THIS EXISTS. Found 2026-09-11 in `dnt_vendor_orders`, and it is the
sharpest defect of the seventeen-resource SAIRNdental validation sweep. The YTD
Spend KPI is

    hist.reduce(function (s, o) { return s + (o.total || 0); }, 0)

and `|| 0` does not do what it looks like it does. Measured in node:

    0 + ("500" || 0)  ->  "0500"      a STRING
    0 + ("abc" || 0)  ->  "0abc"
    "500" || 0        ->  "500"       the guard never fires: a non-empty
                                      string is TRUTHY
    "" || 0           ->  0           only an EMPTY string falls through

THE PLAUSIBLE CASE IS WORSE THAN THE BROKEN ONE, and that is the reason this is
a checker rather than a note. From a real 350 baseline, a `total` of "abc"
renders "350abc" -- visibly wrong, so somebody asks. A `total` of "500" renders
"350500": a believable $350,500 where the truth is $850. Nobody asks. In
SAIRNdental that figure was then handed to Claude by `vSpendAI()` under a system
prompt calling it "real, already-computed" and instructing it never to invent
figures -- a fabricated number laundered into an AI answer as verified fact.

MULTIPLICATION IS SAFE AND ADDITION IS NOT, which is why this only looks at
`+`. Measured: `2 * ("3" || 0)` is 6, because `*` has no string overload;
`0 + ("3" || 0)` is "03", because `+` does. A term like
`s + (i.qty || 0) * (i.cost || 0)` is reported for the `+` and not for the `*`.

WHAT MAKES THE SHAPE A DEFECT RATHER THAN A HAZARD, stated plainly because the
count is large: the shape is only exploitable where something can put a STRING
in that field. A field written only by app code that already does
`Number(x) || 0` cannot. A field written through an API branch with no domain
check can -- which is exactly what `dnt_vendor_orders` was. **So this reports a
HAZARD, and the question it asks of each one is "who can write this field".**
That question is not derivable here and the tool does not pretend to answer it.

THE BASELINE IS THE MECHANISM, same as tools/removal_path_baseline.json. The
real run finds 135 occurrences across 10 files -- 80 distinct file+field keys,
led by stonedesk.html (28), sairnbuild.html (20) and api/_lib/wip-accounting.js
(10). A checker reporting all 135 forever would sit at exit 1 and gate nothing,
so all 80 keys are grandfathered and the check fails on a NEW one. Burn one down
by wrapping the term in `Number(...)` -- which is the whole fix -- or, if the
field is provably numeric, by replacing its line in the baseline with that
reason.

(An earlier draft of this paragraph said "104 occurrences across eight apps",
which was a hand-count taken before the tool existed and before string
interiors were stripped. It is corrected here rather than left to be quoted --
a number in a docstring is a claim like any other.)
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, 'tools', 'truthy_sum_baseline.json')

# `+ (something || 0)`. The term is captured so the report can name the field.
TERM_RE = re.compile(
    r'(?<![+])\+\s*\(\s*([A-Za-z_$][\w$.\[\]\'"]*)\s*\|\|\s*0\s*\)')
# Any of these around the term means somebody already thought about it.
COERCED_RE = re.compile(r'(Number|parseFloat|parseInt)\s*\($')
BINARY_EXT = ('.zip', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.woff',
              '.woff2', '.ttf', '.mp4', '.xlsx', '.docx', '.pyc')


def tracked():
    out = subprocess.run(['git', 'ls-files', '*.html', '*.js'], cwd=REPO,
                         capture_output=True, text=True).stdout
    return [f for f in out.split('\n')
            if f.strip()
            # The preserved ancestor branch is kept for provenance and CLAUDE.md
            # says explicitly it must not be run or recreated. Scanning it would
            # report twelve dead 2026-06 snapshots -- exactly how a report-only
            # checker earns the reputation that gets it switched off.
            and not f.startswith('archive/')
            # A VENDORED THIRD-PARTY VIEWER, not platform code. Six of the
            # first 86 keys came from docs/skill-backups/, a stored copy of a
            # skill's bundled asset that nothing here deploys or maintains.
            # Reporting somebody else's bundled HTML forever is how a
            # report-only checker earns the reputation that gets it switched
            # off. The exclusion is PRINTED on every run rather than silent.
            and not f.startswith('docs/skill-backups/')
            and not f.lower().endswith(BINARY_EXT)]


def strip_comments(src):
    """Blank comments AND string interiors, leaving only executable code.

    Comments, because comment-blindness in a checker is this repo's house
    defect -- the comment-quote checker's own first version blanked from any
    `//` to end of line and swallowed every https://, and this author's
    one-line coverage derivation counted the word "deliberately" out of a
    comment the same day.

    STRING INTERIORS TOO, AND THAT WAS FOUND BY RUNNING THIS. The first version
    stripped comments only and immediately reported a hit in
    api/_lib/dental-ledger.js -- inside the REFUSAL MESSAGE this checker's own
    subject writes, which quotes the pattern verbatim to explain it:
    `'... The YTD reduce is s + (o.total || 0), '`. That is the comment-quoting
    rule one step over: a checker whose subject is CODE must not match the
    fix's own prose, whether that prose lives in a comment or in a string. The
    quotes are kept so the tokens still delimit; only the contents go.

    A `+ (x || 0)` inside a string literal is never executable, so nothing real
    is lost by blanking it.
    """
    out, i, n = [], 0, len(src)
    quote = None
    while i < n:
        c = src[i]
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
        if c in '\'"`':
            quote = c
            out.append(c)
            i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                out.append(' ')
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            while i < n and not (src[i] == '*' and i + 1 < n and src[i + 1] == '/'):
                out.append('\n' if src[i] == '\n' else ' ')
                i += 1
            out.append('  ')
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def occurrences():
    """(file, line, term) for every uncoerced `+ (x || 0)` in tracked source."""
    found = []
    for f in tracked():
        path = os.path.join(REPO, f)
        if not os.path.exists(path):
            continue
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            src = fh.read()
        code = strip_comments(src)
        for m in TERM_RE.finditer(code):
            # `Number(` immediately before the `(` means the term is coerced.
            before = code[max(0, m.start() - 24):m.start() + 1]
            if COERCED_RE.search(before.replace(' ', '').replace('+', '')):
                continue
            head = code[:m.start()]
            found.append((f, head.count('\n') + 1, m.group(1)))
    return found


def key(f, line, term):
    """A file+term key, NOT a line number.

    Deliberate, and the reason is written down elsewhere in this repo: the
    pre-auth exemption file keyed on line numbers and a one-line import above
    it silently invalidated an anchor. A term moving down a file is not a new
    defect; a NEW field being summed uncoerced is.
    """
    return f + '::' + term


def main(argv):
    quiet, full = '--quiet' in argv, '--full' in argv
    found = occurrences()
    baseline = {}
    if os.path.exists(BASELINE):
        with io.open(BASELINE, encoding='utf-8') as fh:
            baseline = json.load(fh).get('grandfathered', {})

    new = [(f, ln, t) for f, ln, t in found if key(f, ln, t) not in baseline]

    if not quiet:
        print('truthy-sum check')
        print('  not scanned: archive/ (the preserved ancestor branch) and '
              'docs/skill-backups/ (a vendored third-party viewer)')
        print('  uncoerced `+ (x || 0)` occurrences : %d' % len(found))
        print('  distinct file+field keys           : %d'
              % len({key(f, l, t) for f, l, t in found}))
        print('  grandfathered                      : %d' % len(baseline))
        if full:
            print('\n--- every occurrence ---')
            for f, ln, t in found:
                mark = ' ' if key(f, ln, t) in baseline else '*'
                print('  %s %-24s :%-6d %s' % (mark, f, ln, t))
        if new:
            print('\n%d NEW OCCURRENCE(S):' % len(new))
            for f, ln, t in new:
                print('  - %s:%d  + (%s || 0)' % (f, ln, t))
            print('\nWrap the term in Number(...). `|| 0` does NOT make it a '
                  'number: a non-empty string is TRUTHY, so the guard never '
                  'fires and `+` CONCATENATES -- 0 + ("500" || 0) is the string '
                  '"0500". Multiplication is safe; addition is not. If the '
                  'field is provably numeric because everything that writes it '
                  'coerces, move it into tools/truthy_sum_baseline.json with '
                  'that reason instead.')
        else:
            print('  CLEAN -- no uncoerced numeric fold that is not already '
                  'grandfathered.')
    return 1 if new else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
