"""Every loop that calls something we do not control, and what happens when it fails.

    python tools/retry_backoff_check.py
    python tools/retry_backoff_check.py --fixtures
    python tools/retry_backoff_check.py --json

Report only. Exit 0 clean, 1 finding, 2 could-not-run.

── WHAT THE 2026-09-16 MERGE CHANGED, AND IT CHANGED THE ANSWER ─────────────
This file shipped on 2026-09-16 reporting 331 source units and ZERO retry
loops. Both figures were wrong, and neither was wrong by much in a way that
showed:

  * `sources()` listed `api/` and `api/_lib/` and NOTHING ELSE, so
    `api/agent/`, `api/sairncash/`, `api/sairndental/` and `api/_resources/`
    -- forty non-test .js files -- were never read. The walk is recursive now:
    371 units.
  * OUTBOUND held four TRANSPORT patterns and every reported row matched
    `fetch(`. A loop reaching the model through a named helper was invisible.
    `callClaude(` and `dispatchAgent(` are merged in from
    tools/retry_policy_audit.py, the other half of item 81.

WITH BOTH FIXED, THE ANSWER IS NO LONGER ZERO: `api/sd-agent.js:176` runs
MAX_ITERATIONS `callClaude(` calls back to back with NO delay and NO breaker.
A clean sweep whose denominator is short reads exactly like a clean sweep whose
denominator is whole, which is why the two item 81 tools were compared against
each other rather than each believed on its own.

── THE QUESTION, AND WHY A TEXT MATCH CANNOT ANSWER IT ──────────────────────
"Does this platform retry without backoff" is a question about CONTAINMENT: is
this outbound call inside the body of a loop, and does that same body contain a
delay. Both halves are structural. `grep -c retry` answers neither -- on this
tree it returns 88 hits in `stonedesk.html`, of which the overwhelming majority
are the word "retry" in a comment, an error message telling a USER to try again,
or a failed-LOGIN counter that has nothing to do with network behaviour.

So this blanks comments and string literals first, then brace-matches the source
into a block tree, and asks its questions against that tree. A call is "in a
retry loop" when the enclosing block is the body of a `for`, `while` or `do` --
established by walking OUT from the call site to its enclosing brace and reading
the keyword that opened it, not by looking for the word "retry" nearby.

── WHAT IT TREATS AS AN OUTBOUND CALL ───────────────────────────────────────
Something the platform does not control and therefore cannot assume about:
`fetch(`, `XMLHttpRequest`, and the Supabase client's request verbs. A local
loop that re-compresses an image until it fits is a retry in English and is not
one here -- `bsuCompressOnce` in `stonedesk.html` loops six times with no delay
and that is CORRECT, because nothing it calls can be overloaded by it.

── WHAT A FINDING MEANS, AND WHAT IT DOES NOT ───────────────────────────────
A loop containing an outbound call and no delay will, when the dependency is
down, issue its attempts as fast as the event loop allows. That is the shape
that turns a dependency's bad minute into a worse one.

It does NOT mean the code is wrong. A two-iteration loop over two DIFFERENT urls
is not a retry at all, and this tool says so rather than guessing: a loop whose
outbound call is the same expression each time is reported RETRY, one whose
target varies is reported ITERATION and is not a finding. Where it cannot tell,
it says UNCLEAR and that is not a pass.

── THE MEASUREMENT THAT CAME WITH IT (2026-09-15) ───────────────────────────
`api/_lib/resilience.js` is 386 lines implementing a composed breaker, bulkhead
and timeout, with `api/_lib/resilience.test.js` at 34 arms, and
`sairn-resilience-patterns` anchors its whole first section on it. **It has zero
importers outside its own test.** Section 0 of that same skill states the rule it
fails: *"a pattern that cannot fire is worse than no pattern, because it reads as
coverage."* This tool reports that number on every run, because it is the single
fact that most changes how the rest of the report should be read -- a clean
retry sweep against a platform with no breaker anywhere is not reassurance.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN, finish   # noqa: E402

# Things the platform does not control. `.from(` is the Supabase client's entry
# point and is how every table read and write in api/ actually leaves the box.
OUTBOUND = (
    re.compile(r'(?<![A-Za-z0-9_$.])fetch\s*\('),
    re.compile(r'(?<![A-Za-z0-9_$.])XMLHttpRequest\b'),
    re.compile(r'(?<![A-Za-z0-9_$])sairnHttp\s*\('),
    re.compile(r'\.\s*from\s*\(\s*[\'"`]'),
    # ── MERGED FROM tools/retry_policy_audit.py, 2026-09-16 ────────────────
    # The four patterns above are all TRANSPORT. Every row this tool reported
    # before the merge matched `fetch(` -- so a loop that reaches the model
    # through a named helper was invisible, and `api/sd-agent.js:175` runs
    # MAX_ITERATIONS `callClaude(...)` calls back to back with no delay and did
    # not appear at all. A call that leaves the box through a wrapper is still
    # an outbound call, and an agent turn loop is the one place on this
    # platform where the pacing question is live today.
    re.compile(r'(?<![A-Za-z0-9_$.])callClaude\s*\('),
    re.compile(r'(?<![A-Za-z0-9_$.])dispatchAgent\s*\('),
)

# A pause between attempts, in any of the spellings used on this tree.
DELAY = re.compile(
    r'(?<![A-Za-z0-9_$.])setTimeout\s*\('
    r'|(?<![A-Za-z0-9_$.])sleep\s*\('
    r'|(?<![A-Za-z0-9_$.])delay\s*\('
    r'|new\s+Promise\s*\([^)]*setTimeout')

# ── A BUDGET THAT CAN STOP THE LOOP IS A BREAKER IN THE SENSE MEANT HERE ────
# The four names above are api/_lib/resilience.js's vocabulary, which has zero
# importers -- so before 2026-09-16 this pattern could only ever match code
# nothing runs. `checkAiRateLimit` is the control that actually exists on this
# platform, and a loop that consumes a unit per iteration and EXITS when the
# answer is not allowed cannot run away.
#
# CALLING IT IS NOT ENOUGH, and that is why this is not a one-word edit.
# `checkAiRateLimit(...)` whose answer is discarded reads as protected and
# stops nothing -- the same call-and-ignore shape that made a purge look wired
# and made an append-only guard look present. So the body must ALSO leave the
# loop: a `return` or a `break` has to appear after the call, and
# breaker_is_acted_on() below is what checks it.
BREAKER = re.compile(r'(?<![A-Za-z0-9_$.])(?:guardedFetch|createBreaker|createBulkhead|withTimeout|checkAiRateLimit)\s*\(')
# The names above that only PROMISE protection if their answer is used. The
# resilience.js four wrap the call itself, so using them is acting on them; a
# budget check returns a verdict somebody has to read.
BREAKER_NEEDS_EXIT = re.compile(r'(?<![A-Za-z0-9_$.])checkAiRateLimit\s*\(')
EXIT_STMT = re.compile(r'(?<![A-Za-z0-9_$])(?:return|break)(?![A-Za-z0-9_$])')


def breaker_is_acted_on(body):
    """Does the loop body ACT on the breaker it calls, or merely call it?

    For a wrapper-style breaker the call IS the protection. For a verdict-style
    one -- a budget check -- the protection is the exit that follows it, and a
    body without one is protected by nothing at all.
    """
    m = BREAKER_NEEDS_EXIT.search(body)
    if not m:
        return True
    return bool(EXIT_STMT.search(body[m.end():]))

LOOP_KEYWORD = re.compile(r'(?<![A-Za-z0-9_$])(for|while|do)\s*$')


# A `/` starts a REGEX when the last significant token cannot end an
# expression, and is DIVISION when it can. Standard heuristic, and the set below
# is the conservative half: an identifier, a close paren/bracket or a digit means
# division; anything else means regex.
_DIV_AFTER = re.compile(r'[A-Za-z0-9_$)\]]$')
# ...except these, which LOOK like identifiers and are keywords, after which a
# `/` is a regex: `return /x/.test(s)` is the shape that matters here.
_KEYWORD_BEFORE_REGEX = re.compile(
    r'(?:^|[^A-Za-z0-9_$])(return|typeof|instanceof|in|of|new|delete|void|'
    r'case|do|else|yield|await)$')


def _starts_regex(prefix):
    """Is a `/` at this point the start of a regex literal rather than division?"""
    p = prefix.rstrip()
    if not p:
        return True
    if _KEYWORD_BEFORE_REGEX.search(p):
        return True
    return not _DIV_AFTER.search(p)


def blank_noise(src):
    """Comments, string interiors AND regex literals blanked, offsets preserved.

    Char-by-char rather than regex for the reason `tier_a_review_gate.py` gives
    for the same job: a string containing a comment marker breaks the regex
    version silently, and this platform has already shipped that defect once.
    Newlines are kept so every offset still maps to its real line.

    ── THE REGEX ARM WAS MISSING AND IT COST 59 OF 321 UNITS ───────────────
    Without it, `api/_lib/wex.js` line 46 -- `.replace(/[‘’']/g, '')`
    -- opened a string on the APOSTROPHE INSIDE THE CHARACTER CLASS and blanked
    the rest of the file, so every brace after it vanished and the unit was
    reported as unscannable. Eighteen percent of the tree landed in
    COULD-NOT-RUN that way.

    It was VISIBLE only because unbalanced braces are reported rather than
    silently tolerated: a scanner that just stopped pairing at the end of input
    would have reported those files as containing no retry loops, which is
    indistinguishable from a file that really has none. The third state is what
    turned a silent 18% blind spot into a line of output.
    """
    out, i, n, quote = [], 0, len(src), None
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if quote:
            if c == '\\':
                out.append('  ' if '\n' not in src[i:i + 2] else src[i:i + 2])
                i += 2
                continue
            if c == quote:
                quote = None
                out.append(c)
            else:
                out.append('\n' if c == '\n' else ' ')
            i += 1
            continue
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            j = n if j == -1 else j + 2
            out.append(''.join('\n' if ch == '\n' else ' ' for ch in src[i:j]))
            i = j
            continue
        if c == '/' and nxt == '/':
            j = src.find('\n', i)
            j = n if j == -1 else j
            out.append(' ' * (j - i))
            i = j
            continue
        if c == '/' and _starts_regex(''.join(out)):
            # Blank through to the unescaped closing `/`, character class aware
            # -- a `/` inside `[...]` does not end the literal.
            j, in_class = i + 1, False
            while j < n:
                d = src[j]
                if d == '\\':
                    j += 2
                    continue
                if d == '\n':           # an unterminated regex; treat as division
                    j = i
                    break
                if d == '[':
                    in_class = True
                elif d == ']':
                    in_class = False
                elif d == '/' and not in_class:
                    j += 1
                    break
                j += 1
            if j > i:
                out.append(' ' * (j - i))
                i = j
                continue
        if c in '\'"`':
            quote = c
            out.append(c)
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def blocks(code):
    """[(open_index, close_index, kind)] for every brace-delimited block.

    `kind` is 'for', 'while', 'do' or None, read from the tokens immediately
    before the `{` -- for `for`/`while` that means skipping back over the
    balanced parenthesised header first. This is the structural half: it is what
    lets a call site be attributed to the construct that ENCLOSES it rather than
    to whatever word happens to sit on the same line.

    Unbalanced input returns what it could pair and the caller is told, because
    a brace scan that silently stops early would under-report -- and
    under-reporting here looks exactly like a clean sweep.
    """
    out, stack = [], []
    for i, c in enumerate(code):
        if c == '{':
            stack.append(i)
        elif c == '}':
            if not stack:
                continue
            o = stack.pop()
            kind, header = _kind_before(code, o)
            out.append((o, i, kind, header))
    return out, len(stack)


_IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
_JS_KEYWORDS = frozenset((
    'await', 'const', 'let', 'var', 'new', 'of', 'in', 'true', 'false', 'null',
    'undefined', 'this', 'function', 'return', 'typeof', 'if', 'else', 'for',
    'while', 'do', 'try', 'catch', 'JSON', 'Object', 'Array', 'String',
    'Number', 'Math', 'Date', 'Promise'))


def _reassigned_in(scope, name):
    """Does `scope` assign, increment or bind `name`?

    Structural in the sense that matters: it asks what the LOOP DOES to the
    values the call depends on, which is the actual difference between a retry
    and an iteration. `=` is matched only when it is not `==`, `===`, `!=`,
    `<=` or `>=`.
    """
    n = re.escape(name)
    return bool(re.search(
        r'(?<![A-Za-z0-9_$.])' + n + r'\s*(?:\+\+|--|\+=|-=|(?<![=!<>])=(?!=))'
        r'|(?:const|let|var)\s+' + n + r'\b'
        r'|(?:const|let|var)\s*\{[^}]*\b' + n + r'\b[^}]*\}'
        r'|for\s*\([^)]*\b' + n + r'\s+(?:of|in)\b', scope))


def varies_across_iterations(header, body, arg_text):
    """Does anything the call depends on CHANGE from one iteration to the next?

    ── WHY THE FIRST CRITERION WAS WRONG, FOUND ON REAL CODE ───────────────
    v1 asked whether the call's SOURCE TEXT was identical each time. Every one
    of the first seven findings was a false positive and two of them show why:

      api/_lib/courtlistener.js:107  for (const key of Object.keys(CL_LIMITS))
                                     -- one pass per rate-limit WINDOW, and the
                                     url embeds `since`, derived from `key`;
      api/audit-checkpoint.js:122    for (;;) with `offset` advancing -- that is
                                     PAGINATION, and the Range header differs on
                                     every pass.

    In both the source expression really is character-identical each time and
    the VALUE is not. A text comparison cannot see the difference; asking
    whether the loop assigns any identifier the call reads, can. A retry is a
    loop that calls the SAME THING again -- so if nothing the call depends on is
    rebound by the loop, it is a retry, and otherwise it is a work list.
    """
    names = set(_IDENT.findall(arg_text)) - _JS_KEYWORDS
    scope = header + '\n' + body
    return any(_reassigned_in(scope, nm) for nm in names)


def _kind_before(code, brace):
    """(loop keyword, header text) for the block opened at `brace`, or (None, '').

    The header is the `(...)` between the keyword and the `{` -- `for (const key
    of Object.keys(X))`. It is needed as well as the body because a for-of
    binding is what makes the loop an iteration, and it lives in the header.
    A `do { } while (c)` has no leading header and returns ''.
    """
    j = brace - 1
    while j >= 0 and code[j] in ' \t\r\n':
        j -= 1
    header = ''
    if j >= 0 and code[j] == ')':
        close = j
        depth = 0
        while j >= 0:
            if code[j] == ')':
                depth += 1
            elif code[j] == '(':
                depth -= 1
                if depth == 0:
                    header = code[j:close + 1]
                    j -= 1
                    break
            j -= 1
        while j >= 0 and code[j] in ' \t\r\n':
            j -= 1
    # ── A BOUNDED WINDOW, AND THE UNBOUNDED VERSION MADE THIS O(n^2) ────────
    # This was `LOOP_KEYWORD.search(code[:j + 1])`. The pattern ends in `\s*$`,
    # so it only ever matches the last few characters -- but slicing the whole
    # prefix and searching it happens once PER BRACE, and `stonedesk.html` has
    # tens of thousands. MEASURED 2026-09-16 while triaging this tool for
    # promotion: 232 SECONDS to analyse 362 source units, down to 25 with the
    # window. The answer never changed, which is exactly why nothing caught it
    # -- a correct check that nobody had timed.
    #
    # The window is far wider than any keyword needs (`while` plus whitespace)
    # so the negative lookbehind still sees real preceding context rather than
    # the cut edge -- a window trimmed to the keyword length would let
    # `...somethingfor {` match `for` with nothing in front of it.
    m = LOOP_KEYWORD.search(code[max(0, j - 200):j + 1])
    return (m.group(1) if m else None), header


def _line_of(code, idx):
    return code.count('\n', 0, idx) + 1


def _call_args(code, match):
    """The balanced argument text of the call this match opened.

    ── FOUND BY THE BLIND LOCK, BEFORE THIS RAN ON ANY REAL FILE ────────────
    The RETRY-vs-ITERATION test first compared `match.group(0)`, which for both
    `fetch(a)` and `fetch(b)` is the string `fetch(` -- identical, so a loop over
    two DIFFERENT urls counted as one target and was reported RETRY. Every
    work-list loop on the platform would have been a finding, and the report
    would have been dismissed wholesale on the first read, which is how a real
    finding inside it gets lost.

    Comparing the ARGUMENTS is the fix, and it is why the fixture asserting the
    ITERATION shape exists at all: the criterion looked right and was wrong, and
    nothing but driving it against a case with a known answer would have said so.
    """
    i = code.rfind('(', match.start(), match.end())
    if i == -1:
        return match.group(0)
    depth, j, n = 0, i, len(code)
    while j < n:
        if code[j] == '(':
            depth += 1
        elif code[j] == ')':
            depth -= 1
            if depth == 0:
                return code[i + 1:j].strip()
        j += 1
    return code[i + 1:].strip()


def analyse(code):
    """[(line, kind, verdict, target)] for every outbound call inside a loop."""
    bs, unbalanced = blocks(code)
    loops = sorted([b for b in bs if b[2]], key=lambda b: b[1] - b[0])
    findings = []
    for pat in OUTBOUND:
        for m in pat.finditer(code):
            inner = None
            for o, c, kind, header in loops:          # smallest enclosing first
                if o < m.start() < c:
                    inner = (o, c, kind, header)
                    break
            if inner is None:
                continue
            o, c, kind, header = inner
            body = code[o:c]
            has_delay = bool(DELAY.search(body))
            has_breaker = bool(BREAKER.search(body)) and breaker_is_acted_on(body)
            args = _call_args(code, m)
            # A RETRY CALLS THE SAME THING AGAIN. If the loop rebinds anything
            # the call reads, the target differs per pass and it is a work list.
            # Text-identical is NOT the test -- see varies_across_iterations().
            if not args:
                verdict = 'UNCLEAR'
            else:
                verdict = ('ITERATION'
                           if varies_across_iterations(header, body, args)
                           else 'RETRY')
            findings.append({
                'line': _line_of(code, m.start()),
                'loop': kind,
                'call': m.group(0).strip(),
                'args': args[:60],
                'shape': verdict,
                'delay': has_delay,
                'breaker': has_breaker,
            })
    return findings, unbalanced


def sources():
    """(label, code, could_not_read) over EVERY api/**.js and the app HTML script blocks.

    ── THE WALK IS RECURSIVE, AND IT WAS NOT (fixed 2026-09-16) ────────────
    The first version listed `api/` and `api/_lib/` and nothing else, so
    `api/agent/`, `api/sairncash/`, `api/sairndental/` and `api/_resources/`
    -- FORTY non-test .js files -- were never read. One of them,
    `api/agent/poll.js:101`, holds an outbound `fetch(` inside a
    `while (Date.now() < deadline)` loop, so the headline "331 source units,
    zero retry loops" was a verdict over a tree with a subtree missing from it.

    THAT IS THE DANGEROUS DIRECTION FOR THIS PARTICULAR TOOL. A scanner that
    reports a clean sweep is read as clearance, and a clean sweep whose
    denominator is short reads exactly like a clean sweep whose denominator is
    whole. Found by comparing this tool's site list against
    tools/retry_policy_audit.py's, which is the other half of item 81 and
    scanned the subtree: two tools agreeing on a conclusion and disagreeing on
    the population is how a scope hole becomes visible at all.
    """
    from extract_scripts import ScriptExtractor
    out, bad = [], []
    api_root = os.path.join(REPO, 'api')
    api_files = []
    for dirpath, dirnames, filenames in os.walk(api_root):
        dirnames[:] = [d for d in dirnames if d != 'node_modules']
        for f in sorted(filenames):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            full = os.path.join(dirpath, f)
            api_files.append((os.path.relpath(full, REPO).replace(os.sep, '/'), full))
    for rel, p in sorted(api_files):
        try:
            out.append((rel, io.open(p, encoding='utf-8', errors='replace').read()))
        except OSError as e:                                     # noqa: BLE001
            bad.append((rel, repr(e)))
    # The api/_lib block that stood here is gone: os.walk covers it,
    # and leaving it would read every _lib file twice and double its
    # findings.
    for f in sorted(os.listdir(REPO)):
        if not f.endswith('.html'):
            continue
        try:
            ex = ScriptExtractor()
            ex.feed(io.open(os.path.join(REPO, f), encoding='utf-8',
                            errors='replace').read())
        except Exception as e:                                   # noqa: BLE001
            # AN HTML FILE THAT WOULD NOT PARSE IS NOT A FILE WITH NO RETRIES.
            bad.append((f, 'script extraction failed: %r' % e))
            continue
        for start, _end, content in ex.blocks:
            out.append(('%s:%d' % (f, start), content))
    return out, bad


def breaker_importers():
    """Files that import api/_lib/resilience.js, excluding the module and its test."""
    hits = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules')]
        for f in files:
            if not (f.endswith('.js') or f.endswith('.html')):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace('\\', '/')
            if rel.startswith('api/_lib/resilience'):
                continue
            try:
                src = io.open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            if re.search(r'''require\s*\(\s*['"][^'"]*resilience['"]|from\s+['"][^'"]*resilience['"]''', src):
                hits.append(rel)
    return sorted(hits)


# ── THE BLIND LOCK ───────────────────────────────────────────────────────────
# Criteria locked against synthetic sources before the tool is pointed at real
# code. The must-NOT-match arms are the important half: this tool's whole claim
# is that it does not fire on the word "retry", and only a fixture that CONTAINS
# that word while being correct can prove it.
FIXTURES = (
    ('retry loop, no delay',
     'while (n--) { await fetch(u); }', 1, {'shape': 'RETRY', 'delay': False}),
    ('retry loop WITH a delay',
     'while (n--) { await fetch(u); await sleep(500); }', 1,
     {'shape': 'RETRY', 'delay': True}),
    ('for loop, no delay',
     'for (let i=0;i<3;i++) { await fetch(u); }', 1,
     {'shape': 'RETRY', 'delay': False}),
    ('do-while',
     'do { await fetch(u); } while (again);', 1, {'shape': 'RETRY'}),
    ('a delay via new Promise(setTimeout)',
     'while (n--) { await fetch(u); await new Promise(r=>setTimeout(r,9)); }', 1,
     {'delay': True}),
    ('guarded by the breaker',
     'while (n--) { await guardedFetch(g, u, {}); await fetch(u); }', 1,
     {'breaker': True}),

    # MUST NOT FIRE.
    ('a fetch with no loop at all', 'await fetch(u);', 0, None),
    ('the WORD retry in a comment above a plain fetch',
     '// retry this if it fails\nawait fetch(u);', 0, None),
    ('a comment inside a loop that has no outbound call',
     'while (n--) { /* retry */ compress(x); }', 0, None),
    ('a string telling the USER to retry',
     'throw new Error("Storage full - clear old quotes and retry.");', 0, None),
    ('a local loop with no outbound call -- bsuCompressOnce\'s real shape',
     'for (var i=0;i<attempts.length;i++){ out = await compressOnce(d, a[i]); }',
     0, None),
    ('fetch inside a STRING is not a call',
     'while (n--) { log("await fetch(u)"); }', 0, None),
    ('a property named fetch is not the global',
     'while (n--) { await client.prefetch(u); }', 0, None),

    # REGEX LITERALS. The apostrophe-in-a-character-class case is wex.js line 46
    # reduced, and without the regex arm it blanked the rest of the file.
    ("an apostrophe inside a regex class does not open a string",
     "s.replace(/[']/g, ''); while (n--) { await fetch(u); }", 1,
     {'shape': 'RETRY'}),
    ('a brace inside a regex is not a block',
     "s.match(/\\d{2}/); while (n--) { await fetch(u); }", 1, {'shape': 'RETRY'}),
    ('a slash that is DIVISION is not a regex',
     'const r = a / b; while (n--) { await fetch(u); }', 1, {'shape': 'RETRY'}),
    ('the word fetch inside a regex is not a call',
     'if (/fetch\\(/.test(s)) { log(s); }', 0, None),
)


def run_fixtures():
    wrong = []
    for label, src, want_n, want in FIXTURES:
        got, unbalanced = analyse(blank_noise(src))
        if len(got) != want_n:
            wrong.append('%-52s expected %d finding(s), got %d  %r'
                         % (label, want_n, len(got), got))
            continue
        if want:
            for k, v in want.items():
                if got[0][k] != v:
                    wrong.append('%-52s expected %s=%r, got %r'
                                 % (label, k, v, got[0][k]))

    # ── RETRY vs ITERATION. Every arm here is a REAL shape from this tree, and
    # the first two are the false positives v1 produced. A criterion that cannot
    # tell pagination from a retry reports seven findings, all wrong, and the
    # report gets dismissed whole -- taking any real finding in it along.
    SHAPES = (
        ('courtlistener.js:107 -- one pass per rate-limit window',
         'for (const key of Object.keys(CL_LIMITS)) { '
         'const since = new Date(now - key).toISOString(); '
         'const r = await fetch(rest("log?since=" + since), { headers }); }',
         'ITERATION'),
        ('audit-checkpoint.js:122 -- pagination, offset advances',
         'for (;;) { const r = await fetch(rest(base), { headers: { Range: offset } }); '
         'offset += PAGE; }',
         'ITERATION'),
        ('for-of over a work list',
         'for (const u of urls) { await fetch(u); }', 'ITERATION'),
        ('a real retry: nothing the call reads is rebound',
         'while (n--) { await fetch(url, opts); }', 'RETRY'),
        ('a real retry in a counted loop',
         'for (let i = 0; i < 3; i++) { await fetch(url); }', 'RETRY'),
        ('the counter is not an argument, so it does not make it an iteration',
         'for (let i = 0; i < 3; i++) { await fetch(url, { headers }); }', 'RETRY'),
    )
    for label, src, want_shape in SHAPES:
        got, _ = analyse(blank_noise(src))
        if not got:
            wrong.append('%-52s expected a %s, found nothing' % (label, want_shape))
        elif any(g['shape'] != want_shape for g in got):
            wrong.append('%-52s expected %s, got %s'
                         % (label, want_shape, [g['shape'] for g in got]))

    # Unbalanced braces must be REPORTED, not silently half-scanned.
    _g, unb = analyse(blank_noise('while (n--) { await fetch(u);'))
    if unb != 1:
        wrong.append('%-52s expected 1 unclosed brace reported, got %r'
                     % ('unbalanced source is reported', unb))

    if wrong:
        print('REFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  ' + w)
        return EXIT_COULD_NOT_RUN
    print('  %d/%d fixtures correct (%d must fire, %d must NOT), plus %d '
          'retry-vs-iteration shapes and the unbalanced-brace arm.'
          % (len(FIXTURES), len(FIXTURES),
             sum(1 for f in FIXTURES if f[2]), sum(1 for f in FIXTURES if not f[2]),
             len(SHAPES)))
    return EXIT_CLEAN


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    srcs, unreadable = sources()
    if not srcs:
        print('COULD NOT RUN: no sources found under api/ or *.html. A sweep '
              'over nothing reports clean.')
        return EXIT_COULD_NOT_RUN

    rows, unbalanced = [], []
    for label, src in srcs:
        found, unb = analyse(blank_noise(src))
        if unb:
            unbalanced.append((label, unb))
        for f in found:
            f['file'] = label
            rows.append(f)

    importers = breaker_importers()
    retries = [r for r in rows if r['shape'] == 'RETRY']
    bare = [r for r in retries if not r['delay'] and not r['breaker']]
    unclear = [r for r in rows if r['shape'] == 'UNCLEAR']

    # THE VERDICT IS COMPUTED ONCE AND BOTH OUTPUT MODES RETURN IT.
    #
    # FOUND 2026-09-16 BY THE FIRST ARTICLE INSPECTION ITEM 47 DEMANDS OF THIS
    # TOOL (Hank, on Cody's tool). `--json` used to carry its own rule --
    # `EXIT_FINDING if (bare or unclear) else EXIT_CLEAN` -- and it disagreed
    # with the text path on the same input in TWO ways:
    #
    #   UNCLEAR. The text path routes it through `could_not_run`, so it exits
    #   2. The json path called it a FINDING and exited 1. "Could not tell" and
    #   "found something" are the two states this repo most insists on keeping
    #   apart, and which one a caller got depended on an output flag.
    #
    #   THE BREAKER, AND THIS IS THE SHARPER HALF. The text path adds "the only
    #   breaker on the platform cannot fire" to `findings` when there are no
    #   importers -- the tool's own headline result. The json path never looked
    #   at `importers` at all, so on today's real repo `--json` exits 0 while
    #   the text run exits non-zero, and a caller wiring the machine-readable
    #   mode into anything would have read the platform as clean.
    #
    # One accounting, two renderings.
    cnr = ['%s (%d unclosed brace(s) -- the scan stopped short there)' % u
           for u in unbalanced]
    cnr += ['%s -- %s' % u for u in unreadable]
    cnr += ['%s line %d: could not tell retry from iteration'
            % (r['file'], r['line']) for r in unclear]
    findings = ['%s line %d: %s loop calls %s every iteration with no delay '
                'and no breaker' % (r['file'], r['line'], r['loop'], r['call'])
                for r in bare]
    if not importers:
        findings.append('api/_lib/resilience.js has no importer: the only '
                        'breaker on the platform cannot fire')

    if '--json' in argv:
        print(json.dumps({'rows': rows, 'breaker_importers': importers,
                          'unbalanced': unbalanced, 'unreadable': unreadable,
                          'findings': findings, 'could_not_run': cnr},
                         indent=2))
        return finish(findings, cnr, quiet=True)

    print('RETRY / BACKOFF / BREAKER -- report only, nothing gates on this')
    print('  %d source unit(s) scanned (every api/**.js and every <script> block in '
          'the app HTML)' % len(srcs))
    print('  %d outbound call(s) inside a loop; %d read as RETRY, %d as '
          'ITERATION, %d UNCLEAR'
          % (len(rows), len(retries),
             sum(1 for r in rows if r['shape'] == 'ITERATION'), len(unclear)))
    print('')

    print('  THE BREAKER: api/_lib/resilience.js has %d importer(s) outside '
          'its own test.' % len(importers))
    if importers:
        for i in importers:
            print('      %s' % i)
    else:
        print('      NONE. 386 lines of composed breaker/bulkhead/timeout, 34')
        print('      test arms, and nothing on this platform calls it. Section 0')
        print('      of sairn-resilience-patterns states the rule this fails:')
        print('      "a pattern that cannot fire is worse than no pattern,')
        print('      because it reads as coverage." Read every line below with')
        print('      that in view: a quiet retry sweep on a platform with no')
        print('      breaker anywhere is not the same as a protected platform.')
    print('')

    if bare:
        print('  RETRY WITH NEITHER A DELAY NOR A BREAKER (%d):' % len(bare))
        for r in bare:
            print('    %-34s line %-6d %s loop, calls %s'
                  % (r['file'], r['line'], r['loop'], r['call']))
        print('')
    for r in retries:
        if r not in bare:
            print('    ok  %-30s line %-6d %s loop -- %s'
                  % (r['file'], r['line'], r['loop'],
                     'delay' if r['delay'] else 'breaker'))

    return finish(findings, cnr,
                  clean_line='\n  No loop issues an uncontrolled call without a '
                             'delay or a breaker.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
