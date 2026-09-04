"""tools/fail_open_check.py -- find reads that turn "I could not ask" into "none".

    python tools/fail_open_check.py            # whole api/ tree
    python tools/fail_open_check.py api/ledger.js

Promoted from a one-off grep on 2026-09-04, after the same shape produced
eighteen real defects across five files in a single session:

  * api/_lib/dental-public.js  -- resolveSlug() answered 404 "booking link not
    found" when the store was unreachable, and the rate limiter read an
    unreachable counter as zero and allowed everything.
  * api/sairndental/public-*.js -- nine reads that fabricated a calendar in
    BOTH directions: a failed provider-hours read showed a practice fully
    booked, a failed appointments read showed every slot free.
  * api/ledger.js -- a duplicate check that permitted double-posting revenue,
    and a trial_balance that reported the books BALANCED AND EMPTY because it
    could not read them.
  * api/alf-pharmacy.js -- a failed check reset an already-reviewed medication
    order back to pending_review.
  * api/sd-data.js -- six SAIRNcare append-only checks, three of which then
    silently overwrote the record they exist to protect.

── IT UNDER-REPORTS, AND THAT IS SAID HERE RATHER THAN DISCOVERED ─────────
The heuristics below catch a value used DIRECTLY -- a `.length` test, a
`.find()`, a loop. They do NOT catch a value that is unpacked into another
variable and then passed into a function, which is how api/sd-data.js:8347
escaped: an unreadable facility read yields `{}`, that becomes
`fac.food_thresholds`, and evaluateFoodTemp() falls back to the FDA Food Code
defaults -- so a facility with a STRICTER local threshold is silently graded
against the looser national one. It was found by reading, not by this tool.

So the second bucket is labelled UNTRIAGED, not "safe". A clean run means "no
hit matched a known decision shape", never "there are no fail-open decisions".

── WHAT THIS CAN AND CANNOT DECIDE ────────────────────────────────────────
It finds the SHAPE. It cannot tell you the shape is wrong, and most hits are
fine: a list that renders empty is wrong-but-visible, and some sites are
deliberately fail-open with a reason written above them.

WHAT MATTERS IS WHETHER THE RESULT FEEDS A DECISION OR A DISPLAY. So each hit
is scored on what the following lines actually do with it -- a `.length` test
that gates a 409, a `.find()` whose miss creates a record, a loop that drives a
sweep -- and printed as DECISION or display. A DECISION hit is a claim to
verify, not a verdict.

Triaged-and-accepted sites go in tools/fail_open_accepted.json with a reason a
reader can check, exactly like tools/reachability_exemptions.json. The point is
that the list converges instead of being re-triaged every time.
"""
import io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCEPTED_PATH = os.path.join(ROOT, 'tools', 'fail_open_accepted.json')

# The three spellings this codebase actually uses. Deliberately narrow: a
# looser pattern drowns the output and gets ignored, which is how a check dies.
# `.catch(...)` is written BOTH ways in this codebase -- `.catch(() => [])` and
# `.catch(function () { return null; })` -- and a first draft used `[^)]*`,
# which cannot cross the nested parens of an arrow function. It silently missed
# api/alf-alerts.js:207, a facilities read that drives the whole medication
# exception sweep. A checker that under-reports without saying so is the exact
# failure class it exists to find, so the catch tail is now non-greedy across
# anything up to the ternary colon.
_CATCH = r'(?:\.catch\(.*?\))?'
PATTERNS = [
    (re.compile(r'(\w+)\s*=\s*(\w+)\.ok\s*\?\s*await\s+\2\.json\(\)' + _CATCH + r'\s*:\s*\[\]'), 'ternary-to-[]'),
    (re.compile(r'(\w+)\s*=\s*(\w+)\.ok\s*\?\s*await\s+\2\.json\(\)' + _CATCH + r'\s*:\s*null'), 'ternary-to-null'),
    (re.compile(r'if\s*\(!\s*(\w+)\.ok\)\s*return\s+(?:\[\]|null)\s*;'), 'guard-to-empty'),
]

# What the following lines do with the value. A decision gates a write or a
# refusal; a display renders it.
DECISION = [
    (re.compile(r'\.length\s*(?:>|>=|===|!==|\?|\))'), 'existence test'),
    (re.compile(r'\.find\('), '.find() -- a miss usually creates something'),
    (re.compile(r'\.some\('), '.some() -- overlap/conflict test'),
    (re.compile(r'res\.status\(409\)'), 'gates a 409'),
    (re.compile(r'ALREADY_|DUPLICATE|SLOT_TAKEN|_TAKEN'), 'gates a duplicate refusal'),
    (re.compile(r'\bfor\s*\(\s*(?:const|let|var)\b'), 'drives a loop/sweep'),
    (re.compile(r'method:\s*[\'"]POST'), 'a write follows'),
    (re.compile(r'\bnew Set\('), 'builds a membership set'),
]
DISPLAY = [
    (re.compile(r'res\.status\(200\)\.json\('), 'returned to the caller'),
    (re.compile(r'\.map\('), 'mapped for output'),
]
LOOKAHEAD = 14


def load_accepted():
    try:
        with io.open(ACCEPTED_PATH, encoding='utf-8') as f:
            return {(e['file'], e['var']): e.get('reason', '') for e in json.load(f)}
    except Exception:
        return {}


def scan(path, accepted):
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    src = io.open(path, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    lines = src.split('\n')
    out = []
    for i, line in enumerate(lines):
        # A commented-out example is not a defect. Every fix in this codebase
        # quotes the expression it replaced, so this is not a nicety.
        if re.match(r'\s*(//|\*|/\*)', line):
            continue
        for pat, kind in PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            var = m.group(1)
            after = '\n'.join(lines[i + 1:i + 1 + LOOKAHEAD])
            # Only count signals that mention THIS variable, or are unmissable.
            near = '\n'.join(l for l in after.split('\n') if var in l or 'res.status(409)' in l or 'method:' in l)
            why = [label for rx, label in DECISION if rx.search(near)]
            disp = [label for rx, label in DISPLAY if rx.search(near)]
            out.append({
                'file': rel, 'line': i + 1, 'var': var, 'kind': kind,
                'decision': why, 'display': disp,
                'accepted': accepted.get((rel, var)),
                'text': line.strip()[:110],
            })
    return out


def main():
    accepted = load_accepted()
    targets = sys.argv[1:]
    if targets:
        files = [os.path.join(ROOT, t) for t in targets]
    else:
        files = []
        for base, dirs, names in os.walk(os.path.join(ROOT, 'api')):
            dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__')]
            files += [os.path.join(base, n) for n in names
                      if n.endswith('.js') and not n.endswith('.test.js')]

    hits = []
    for f in sorted(files):
        hits += scan(f, accepted)

    dec = [h for h in hits if h['decision'] and not h['accepted']]
    dis = [h for h in hits if not h['decision'] and not h['accepted']]
    acc = [h for h in hits if h['accepted']]

    print('fail-open reads found: %d   (decision-shaped %d, untriaged %d, accepted %d)'
          % (len(hits), len(dec), len(dis), len(acc)))
    print('NOTE: a clean decision-shaped list means no hit matched a KNOWN shape.')
    print('      It does not mean there are no fail-open decisions left -- see the header.')

    print('\n=== DECISION-SHAPED -- READ EVERY ONE ===')
    if not dec:
        print('  none')
    for h in dec:
        print('  %s:%d  %s  [%s]' % (h['file'], h['line'], h['var'], h['kind']))
        print('       why: ' + '; '.join(h['decision']))
        print('       %s' % h['text'])

    print('\n=== NOT OBVIOUSLY DECISION-SHAPED -- UNTRIAGED, NOT CLEARED ===')
    print('    (what the heuristics did not match, which is not the same as a')
    print('     value that only ever reaches a display -- see the header)')
    for h in dis:
        print('  %s:%d  %s%s' % (h['file'], h['line'], h['var'],
                                 ('  -> ' + '; '.join(h['display'])) if h['display'] else ''))

    if acc:
        print('\n=== accepted (triaged, with a reason on file) ===')
        for h in acc:
            print('  %s:%d  %s -- %s' % (h['file'], h['line'], h['var'], h['accepted']))

    # Exit 1 only on decision-shaped hits, so this can gate a push later
    # without failing on the long tail of display reads.
    return 1 if dec else 0


if __name__ == '__main__':
    sys.exit(main())
