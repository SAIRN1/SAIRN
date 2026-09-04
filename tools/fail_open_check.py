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
    """Load the acceptance list, and NEVER fail silently doing it.

    The first version was `except Exception: return {}`. A single entry without
    a `file` key -- the human-readable `_note` at the top of the file -- raised
    KeyError, the bare except swallowed it, and EVERY acceptance was silently
    discarded while the checker reported "accepted 0" as though the file were
    empty. A malformed acceptance file quietly disabling all acceptances is the
    same swallow-and-carry-on this whole tool exists to find, in the tool.
    """
    if not os.path.exists(ACCEPTED_PATH):
        return {}
    try:
        with io.open(ACCEPTED_PATH, encoding='utf-8') as f:
            entries = json.load(f)
    except Exception as err:
        print('WARNING: %s could not be parsed (%s). NO acceptances are in '
              'effect, so every site below is listed as untriaged.'
              % (os.path.basename(ACCEPTED_PATH), err))
        return {}
    out = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        # Entries without file+var are prose (the `_note` header), not defects.
        if 'file' not in e or 'var' not in e:
            continue
        if not e.get('reason'):
            print('WARNING: acceptance for %s %s has no reason -- an acceptance '
                  'nobody justified is not one.' % (e['file'], e['var']))
        out[(e['file'], e['var'])] = e.get('reason', '')
    return out


# ── THE BROWSER-SIDE CLASS (2026-09-04) ────────────────────────────────────
# The three patterns above are all `res.ok ? await res.json() : []` -- an
# api/*.js fetch. Pointing this tool at an app's HTML and getting zero was
# therefore meaningless, and it was reported as a clean sweep of SAIRNlegacy and
# SAIRNdesign until a planted browser-side fixture was scanned and NOT flagged.
#
# The client's version of the same defect is the storage loader every SAIRN app
# has:
#
#     function ld(k,d){try{var r=localStorage.getItem(k);
#                          return r===null?d:JSON.parse(r);}catch(e){return d;}}
#
# ABSENT AND CORRUPT RETURN THE SAME VALUE, and nothing says which happened.
# A record that will not parse renders as "you have none" -- and where `d` is a
# seeded default rather than `[]`, it renders as invented content instead, which
# is the StoneDesk SEED-fallback shape Guardian's lesson 6 records.
#
# ONE FINDING PER WRAPPER, NOT PER CALL SITE, and that is the whole reason this
# is usable. Flagging every `ld('x',[])` whose result meets a `.length` test
# would produce hundreds of hits across thirteen apps and the tool would be
# ignored -- which this file's own header says is how a check dies. The
# wrapper is where the two facts are collapsed, so the wrapper is the finding.
#
# It is REPORTED, never gating: fourteen live wrappers on the day this shipped,
# and turning that into a blocking exit would have made the gate the problem.
# THE CATCH BODY IS ALLOWED TO DO THINGS BEFORE RETURNING, and that is not a
# detail. A first version required the catch to be exactly `{return d;}`, which
# made the `console.` exclusion below UNREACHABLE -- a loader that logged could
# never match the pattern in the first place, so a branch that looked like a
# safeguard was dead code. A fixture proved it: removing the exclusion entirely
# changed nothing. Widened so the exclusion is real, and so a loader that does
# other work before returning the default is still seen.
LOADER = re.compile(
    r'function\s+(\w+)\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)\s*\{'
    r'(?:(?!function\s).){0,300}?localStorage\.getItem'
    r'(?:(?!function\s).){0,300}?catch\s*\(\s*\w+\s*\)\s*\{'
    r'(?:(?!function\s)[^{}]){0,200}?return\s+(\w+)\s*;?\s*\}',
    re.S)


def scan_loaders(path, accepted):
    """Storage loaders where a parse failure is indistinguishable from absence.

    A loader that LOGS on the catch is not reported: the two facts are still
    returned identically, but a reader can now tell them apart, which is the
    same bar st() was held to.
    """
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    raw = io.open(path, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    out = []
    for m in LOADER.finditer(raw):
        name, default_param, catch_returns = m.group(1), m.group(3), m.group(4)
        if catch_returns != default_param:
            continue                      # returns something else -- not this shape
        body = m.group(0)
        if 'console.' in body:
            continue                      # says which happened; not silent
        out.append({
            'file': rel,
            'line': raw[:m.start()].count('\n') + 1,
            'var': name,
            'accepted': accepted.get((rel, name)),
        })
    return out


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
        # THE APP HTML IS NOW IN THE DEFAULT WALK. It was api/ only, so the
        # browser-side pass below would never have run unless someone named a
        # file -- a check that only fires when asked for is one nobody runs.
        files += [os.path.join(ROOT, n) for n in os.listdir(ROOT) if n.endswith('.html')]

    hits = []
    loaders = []
    for f in sorted(files):
        if not os.path.isfile(f):
            continue
        hits += scan(f, accepted)
        loaders += scan_loaders(f, accepted)

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

    live_loaders = [l for l in loaders if not l['accepted']]
    acc_loaders = [l for l in loaders if l['accepted']]
    print('\n=== BROWSER-SIDE: a corrupt record and an absent one return the same thing ===')
    print('    (%d storage loader(s); REPORTED, never gating -- see the LOADER note.' % len(live_loaders))
    print('     A loader that LOGS on the catch is not listed: the values are still')
    print('     identical, but a reader can tell which happened.)')
    if not live_loaders:
        print('  none')
    for l in live_loaders:
        print('  %s:%d  %s()' % (l['file'], l['line'], l['var']))
    if acc_loaders:
        print('  -- accepted --')
        for l in acc_loaders:
            print('  %s:%d  %s() -- %s' % (l['file'], l['line'], l['var'], l['accepted']))

    # ── AN ACCEPTANCE THAT MATCHES NOTHING IS A LIE WAITING TO BE READ ──────
    # The first entry in this file was resolved within the hour it was written
    # (api/sd-data.js facRows, the food-temperature thresholds). Nothing would
    # have said so: an unmatched key is silently ignored, so the file would keep
    # asserting a known-open defect that no longer exists, and the next reader
    # would triage around a ghost. Same staleness this project has been bitten
    # by in CLAUDE.md and in three status docs.
    # ── ONLY ON A FULL RUN (2026-09-04) ──────────────────────────────────────
    # This used to compare every acceptance against whatever subset had just
    # been scanned, so ANY targeted run reported every acceptance outside that
    # subset as stale -- and the message tells the reader to delete it.
    #
    # Reproduced, not theorised: `fail_open_check.py sairnlegacy.html
    # sairndesign.html` reported api/_lib/ai-rate-limit.js's `wRows` acceptance
    # as matching nothing. That site is alive at line 172 and its reasoning is
    # intact; following the advice would have deleted a correct, reasoned
    # acceptance because it was not in the two files being looked at.
    #
    # A tool that tells you to throw away right answers is worse than one that
    # stays quiet, so staleness is now only computed when the whole tree was
    # scanned -- which is the only run that can actually know.
    matched = set((h['file'], h['var']) for h in hits)
    stale = [k for k in accepted if k not in matched] if not targets else []
    if stale:
        print('\n=== STALE ACCEPTANCES -- these match nothing any more ===')
        for f, v in stale:
            print('  %s  %s  -- the site is gone or was renamed. Remove the entry or' % (f, v))
            print('       re-triage it; leaving it asserts a defect that is not there.')
    elif targets and accepted:
        print('\n(stale-acceptance check skipped: only a full run can tell, and this')
        print(' run was scoped to %d file(s).)' % len(targets))

    # Exit 1 only on decision-shaped hits, so this can gate a push later
    # without failing on the long tail of untriaged reads.
    return 1 if dec else 0


if __name__ == '__main__':
    sys.exit(main())
