"""tools/discarded_verdict_check.py -- find refusals that are computed and thrown away.

    python tools/discarded_verdict_check.py            # api/ and the app HTML
    python tools/discarded_verdict_check.py api/_lib/courtlistener.js

Promoted from three by-hand findings on 2026-09-04, all in one session, all the
same shape and none of them found by an existing check:

  * api/_lib/courtlistener.js -- all FOUR token-gated functions called
    `await checkAndLogRateLimit();` and discarded the return value. The limiter
    computed {limited: true, window: 'minute'} and the next line called
    CourtListener anyway. No caller in api/ read it either.
  * stonedesk.html -- intakeAccept()/intakeDismiss()/intakeAnalyzePhoto() ran
    real Supabase writes inside a bare catch and reported success regardless,
    then showed "Customer + Job created from intake!" for a write that failed.
  * api/sd-data.js -- caught by a NEGATIVE CONTROL rather than by reading:
    `if (problem)` changed to `if (false)` passed a test that only asserted the
    error code appeared somewhere in the file.

── WHAT THIS IS, PRECISELY ────────────────────────────────────────────────
A function whose whole purpose is to say NO is called, and its answer is never
consulted. The call is real, the log line is written, the budget is spent, the
check "ran" -- and the refusal evaporates. From the outside it is indis-
tinguishable from a working gate, which is why three of these survived review.

It is NOT the same as fail-open (tools/fail_open_check.py): there, a read fails
and the failure is read as "none". Here nothing fails at all. The verdict is
correct and simply nobody looks at it.

── HOW IT DECIDES ─────────────────────────────────────────────────────────
Two passes, deliberately narrow, because a loose version of this drowns in
every void-returning call in the codebase:

  1. CALLERS -- an `await f(...)` used as a bare expression statement, where
     `f` is a function this file also DEFINES and that RETURNS something on at
     least one path. A function that always returns undefined cannot have its
     verdict discarded.
  2. DEFINITIONS -- a function that returns an object carrying a refusal-shaped
     key (limited / ok / allowed / error / problem / denied / blocked /
     forbidden) and has at least one caller that ignores it.

── IT UNDER-REPORTS, AND SAYS SO ──────────────────────────────────────────
It cannot see across files: `checkAndLogRateLimit` was defined in
api/_lib/courtlistener.js and called in the same file, which is why that one is
findable here. A verdict returned by a required module and discarded in another
file is NOT caught -- that needs a cross-module pass this does not attempt.

It also cannot judge intent. Some returns are genuinely advisory. So the output
is a list to read, not a verdict, and triaged sites go in
tools/discarded_verdict_accepted.json with a reason -- the same convention as
tools/fail_open_accepted.json and tools/reachability_exemptions.json.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCEPTED_PATH = os.path.join(ROOT, 'tools', 'discarded_verdict_accepted.json')

# Keys that make a returned object a VERDICT rather than data. Deliberately
# short: every one of these is a word this codebase actually uses to mean "the
# answer to whether this is allowed".
VERDICT_KEYS = ('limited', 'allowed', 'ok', 'denied', 'blocked', 'forbidden',
                'problem', 'refused', 'error', 'valid', 'permitted')

# `await f(args);` alone on a line -- the answer computed and dropped.
BARE_AWAIT = re.compile(r'^\s*await\s+([A-Za-z_$][\w$.]*)\s*\(', re.M)

# Function definitions, in the four spellings this codebase uses.
DEFS = [
    re.compile(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('),
    re.compile(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\('),
    re.compile(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function'),
]


def load_accepted():
    """Triaged sites, with a reason. A malformed file disables NOTHING silently.

    Same standard as fail_open_check.py: a parse failure is announced and every
    site is reported as untriaged, because an acceptance list that quietly
    empties itself is the bug this tool is about, in the tool.
    """
    if not os.path.exists(ACCEPTED_PATH):
        return {}
    try:
        with io.open(ACCEPTED_PATH, encoding='utf-8') as f:
            entries = json.load(f)
    except Exception as err:
        print('WARNING: %s could not be parsed (%s). NO acceptances are in '
              'effect.' % (os.path.basename(ACCEPTED_PATH), err))
        return {}
    out = {}
    for e in entries if isinstance(entries, list) else []:
        if not isinstance(e, dict) or 'file' not in e or 'fn' not in e:
            continue
        if not e.get('reason'):
            print('WARNING: acceptance for %s %s has no reason -- an acceptance '
                  'nobody justified is not one.' % (e['file'], e['fn']))
        out[(e['file'], e['fn'])] = e.get('reason', '')
    return out


def strip_comments(src):
    """Remove comment TEXT while preserving every newline.

    A block comment used to be deleted whole, newlines and all, so every line
    number reported after one was short by however many lines the comment
    spanned. In an HTML file with CSS blocks that is a large drift -- the first
    real check of this tool against sairnlegacy.html pointed at a comment line
    two hundred lines from the hit. Found 2026-09-04, in my own tool, by
    reading a reported line and finding the wrong thing there.

    Line-preserving is also why the `//` pass keeps its newline: it strips to
    end-of-line and no further.
    """
    src = re.sub(r'/\*[\s\S]*?\*/',
                 lambda m: '\n' * m.group(0).count('\n'), src)
    return re.sub(r'(^|[^:])//[^\n]*', r'\1', src)


def function_body(src, name):
    """Rough body of a named function: from its definition to the next one.

    Brace-matching would be more precise and is not worth it -- this only needs
    to know whether a `return` with a verdict-shaped object appears inside, and
    over-reading into the next function makes the tool MORE cautious (it would
    report a site it should not), never less.
    """
    for pat in DEFS:
        for m in pat.finditer(src):
            if m.group(1) != name:
                continue
            start = m.end()
            nxt = len(src)
            for p2 in DEFS:
                m2 = p2.search(src, start)
                if m2 and m2.start() < nxt:
                    nxt = m2.start()
            return src[start:nxt]
    return None


def returns_verdict(body):
    """Does this body return something that looks like an allow/deny answer?"""
    if body is None:
        return None
    for m in re.finditer(r'return\s+([^;\n]{0,200})', body):
        expr = m.group(1)
        if expr.strip() in ('', 'null', 'undefined', 'false', 'true'):
            # A bare boolean IS a verdict, but only if some caller uses it --
            # handled by the caller pass. On its own it is too common to report.
            continue
        for k in VERDICT_KEYS:
            if re.search(r'\b' + k + r'\s*:', expr):
                return k
        if re.match(r'^[A-Za-z_$][\w$]*$', expr.strip()):
            continue
    return None


def scan(path, accepted):
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    raw = io.open(path, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    src = strip_comments(raw)
    hits = []
    for m in BARE_AWAIT.finditer(src):
        callee = m.group(1)
        name = callee.split('.')[-1]
        body = function_body(src, name)
        if body is None:
            continue                      # defined elsewhere -- see the header
        key = returns_verdict(body)
        if not key:
            continue
        line = src[:m.start()].count('\n') + 1
        hits.append({
            'file': rel, 'line': line, 'fn': name, 'key': key,
            'accepted': accepted.get((rel, name)),
            'text': raw.split('\n')[min(line - 1, len(raw.split('\n')) - 1)].strip()[:110],
        })
    return hits


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
        files += [os.path.join(ROOT, n) for n in os.listdir(ROOT)
                  if n.endswith('.html')]

    hits = []
    for f in sorted(files):
        if os.path.isfile(f):
            hits += scan(f, accepted)

    live = [h for h in hits if not h['accepted']]
    acc = [h for h in hits if h['accepted']]

    print('discarded verdicts found: %d   (to read %d, accepted %d)'
          % (len(hits), len(live), len(acc)))
    print('NOTE: this cannot see across files -- a verdict returned by a required')
    print('      module and dropped in another file is NOT caught. See the header.')

    print('\n=== A REFUSAL WAS COMPUTED AND NOT READ -- READ EVERY ONE ===')
    if not live:
        print('  none')
    for h in live:
        print('  %s:%d  %s()  returns {%s: ...}' % (h['file'], h['line'], h['fn'], h['key']))
        print('       %s' % h['text'])

    if acc:
        print('\n=== accepted (triaged, with a reason on file) ===')
        for h in acc:
            print('  %s:%d  %s -- %s' % (h['file'], h['line'], h['fn'], h['accepted']))

    return 1 if live else 0


if __name__ == '__main__':
    sys.exit(main())
