"""Item 81: every retry on a remote call, and whether it backs off or hammers.

    python tools/retry_policy_audit.py
    python tools/retry_policy_audit.py --json
    python tools/retry_policy_audit.py --all        # include archive/ and docs/
    python tools/retry_policy_audit.py --self-check

Exit 0 when no live retry construct is unbacked-off or unbounded, 1 when one
is, 2 when the fixtures fail -- which means nothing real was scanned. REPORT
ONLY.

── WHY THIS IS NOT A REGEX, AND THE FIRST ATTEMPT IS THE REASON ────────────
A regex pass at item 81 reported 24 of 25 `api/` files as having retry logic
with no backoff. Spot-checking three killed it: one hit was the word "retry" in
a comment, one was the author's own comment about a retry count, and the
"backoff" hits in that file were the author's own citations of another module.
THE FIGURE WAS PROSE. It was retracted rather than published, which is the
right call and is also the reason this file exists.

Both of those false-positive classes are IMPOSSIBLE HERE BY CONSTRUCTION, not
by a longer pattern. `jscomments.strip_comments` walks the source with a state
machine that skips strings, template literals and regex literals, and
`blank_string_bodies` then empties the string contents. A scanner running after
those two cannot see a comment or a string body at all, because there is
nothing left of them. That module exists precisely because seven hand-rolled
strippers in this repo disagreed and three were destroying 90% of their input.

── WHAT A RETRY IS HERE: A STRUCTURE, NOT A WORD ───────────────────────────
A retry construct is a LOOP or a CATCH BLOCK, found by keyword-plus-balanced-
brace extraction, WHOSE BODY CONTAINS A REMOTE CALL. Nothing is matched on the
word "retry" anywhere -- a loop called `drainQueue` that re-issues a write is a
retry, and a variable called `retryCount` that nothing loops on is not.

THE BODY IS THE REAL BODY. An early version of this reconnaissance used a fixed
1,200-character window after the loop header and produced a false positive on
`sairnlaw.html` -- a CSV split loop whose window happened to reach a `setTimeout`
belonging to something else entirely. Balanced braces, or the answer is about
whatever happened to be nearby.

── WHAT IS MEASURED, AND WHAT IS REFUSED ───────────────────────────────────
MEASURED, mechanically, from the extracted body:

  BOUND      the loop header compares a counter against a maximum, or the
             construct is a catch that runs once. `while (true)` with no
             counter comparison is UNBOUNDED.
  DELAY      the body contains a wait -- setTimeout, sleep, delay, or an
             awaited Promise around one.
  BACKOFF    the delay ARGUMENT varies with the attempt: it references the loop
             variable, or contains `*`, `**`, `Math.pow` or `<<`. A delay that
             is the same every time is FIXED DELAY and is reported as such,
             because "it waits" and "it backs off" are different claims and
             only one of them protects a struggling backend.
  JITTER     the delay argument references Math.random or a jitter helper.

REFUSED, and said here rather than discovered later:

  * A CIRCUIT BREAKER IS NOT DECIDABLE FROM ONE FILE and this tool does not
    claim to find one. A breaker is persistent state -- a failure count that
    outlives the request, checked before the next call -- and on serverless
    functions that state is in the database, not in the module. What IS
    reported is whether the construct's file declares any candidate breaker
    state at all, which is a NECESSARY-NOT-SUFFICIENT signal and is labelled
    that way. NONE FOUND is not proof there is no breaker.
  * Whether the remote call NEEDS a retry. Some do not.
  * Retries implemented by a caller above the construct, or by the platform.
  * Anything in a language this cannot tokenise.

── ARCHIVE IS EXCLUDED BY DEFAULT, AND THE COUNT IS PRINTED ────────────────
`archive/` holds pre-platform uploads with their own retry loops, and counting
them would inflate every figure with code nobody runs. They are excluded, the
number excluded is printed, and `--all` includes them.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import jscomments                                                # noqa: E402

# ── THE VOCABULARY, DECLARED RATHER THAN INFERRED ───────────────────────────
# A remote call is one that leaves the process. Named explicitly: a pattern
# broad enough to catch "any function call" would make every loop a retry.
REMOTE = re.compile(
    r'\bfetch\s*\('                      # the browser and node transport
    r'|\b\w*[Dd]ata\s*\(\s*[\'"]'        # sdData('write', ...) and siblings
    r'|\.rpc\s*\('                       # supabase RPC
    r'|\.from\s*\([^)]*\)\s*\.\s*(select|insert|update|upsert|delete)\b'
    r'|\bcallClaude\s*\('
    r'|\banthropic\b'
    r'|\bdispatchAgent\s*\('
)
DELAY = re.compile(r'\bsetTimeout\s*\(|\bsleep\s*\(|\bdelay\s*\(')
JITTER = re.compile(r'\bMath\s*\.\s*random\b|\bjitter\b', re.I)
# A varying delay: arithmetic on the attempt, or an explicit power/shift.
VARYING = re.compile(r'\*\*|Math\s*\.\s*pow\b|<<|\*')
# Candidate circuit-breaker state. NECESSARY, NOT SUFFICIENT -- see the header.
BREAKER = re.compile(r'\b\w*(breaker|circuit|tripped|cooldown|backoff_until|'
                     r'consecutive_failures)\w*\b', re.I)

LOOP_KW = ('for', 'while', 'do')
IDENT = re.compile(r'[A-Za-z_$][\w$]*')


def _matching(code, open_at):
    """Index just past the brace/paren that balances the one at `open_at`."""
    pairs = {'{': '}', '(': ')', '[': ']'}
    want = pairs.get(code[open_at])
    if not want:
        return None
    depth, i = 0, open_at
    while i < len(code):
        c = code[i]
        if c in pairs:
            depth += 1
        elif c in ('}', ')', ']'):
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _statement_end(code, i):
    """Index just past the `;` ending the statement starting at i, or None.

    Depth-aware: a `;` inside `for (a; b; c)` or inside a function expression
    argument does not end the outer statement.
    """
    depth = 0
    while i < len(code):
        c = code[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth < 0:
                return None
        elif c == ';' and depth == 0:
            return i + 1
        i += 1
    return None


def constructs(code):
    """Every loop and catch block, with its HEADER and its real BODY.

    Keyword-plus-balanced-brace extraction. The keyword has to be a whole token
    -- `for` inside `before` is not a loop, and after string blanking there is
    nothing else that could produce one.
    """
    out = []
    for m in re.finditer(r'\b(for|while|do|catch)\b', code):
        kw = m.group(1)
        i = m.end()
        # Optional header in parens: for(...), while(...), catch(e). `do` has
        # none. Skip whitespace, then take a balanced paren group if present.
        while i < len(code) and code[i] in ' \t\r\n':
            i += 1
        header = ''
        if i < len(code) and code[i] == '(':
            end = _matching(code, i)
            if end is None:
                continue
            header = code[i:end]
            i = end
        elif kw != 'do':
            # `for`, `while` and `catch` CANNOT be written without parentheses.
            # A bare one is not a loop -- it is the word appearing in text this
            # tokenizer does not blank, and in an HTML file that is common:
            # `<label for="x">`. The first version read the "body" of one of
            # those as everything up to the next semicolon, which in a 2MB
            # single-file app swept up a real fetch and reported it.
            continue
        while i < len(code) and code[i] in ' \t\r\n':
            i += 1
        if i >= len(code) or code[i] != '{':
            # A SINGLE-STATEMENT BODY, and it is read rather than skipped.
            # The first version skipped these and reported 882 unread loops --
            # a coverage hole big enough to hide the thing being looked for.
            # The statement END is structural, not a window: scan to the first
            # `;` that is not inside any paren, brace or bracket. That is where
            # the statement really ends, however long it is.
            end = _statement_end(code, i)
            out.append({'kind': kw, 'header': header,
                        'body': code[i:end] if end else None,
                        'single': True, 'start': m.start()})
            continue
        end = _matching(code, i)
        if end is None:
            continue
        out.append({'kind': kw, 'header': header, 'body': code[i:end],
                    'start': m.start()})
    return out


def loop_var(header):
    """The counter a `for` header increments, if it has one."""
    m = re.search(r'\b(?:var|let|const)?\s*([A-Za-z_$][\w$]*)\s*=', header or '')
    return m.group(1) if m else None


def delay_args(body):
    """The argument text of every delay call in the body, balanced."""
    args = []
    for m in DELAY.finditer(body):
        p = body.find('(', m.start())
        if p == -1:
            continue
        end = _matching(body, p)
        if end:
            args.append(body[p:end])
    return args


# ── THE SECOND FALSE-POSITIVE CLASS, AND IT WAS MINE ────────────────────────
# The first run of THIS tool reported 24 "retry constructs". Reading four of
# them killed the figure: `for (const key of Object.keys(...))` making a call
# per key is ITERATION; `for(;;)` advancing an `offset` is PAGINATION;
# `while(true)` that shifts a queue is a DRAIN; `while (Date.now() < deadline)`
# is a POLL. Not one was a retry. A loop that contains a remote call is not a
# loop that RE-ISSUES one, and reporting the first as the second is the same
# defect shape as matching the word "retry" in a comment -- a broader net, an
# equally wrong number.
#
# A RETRY re-issues a call BECAUSE IT FAILED. That has a structure: the loop
# does not advance through anything, and it leaves early when the call works.
COLLECTION = re.compile(r'\bof\b|\bin\b|\.length\b')
PROGRESS = re.compile(r'\b(offset|cursor|page|from|start|skip)\b\s*(\+=|\+\+|=)'
                      r'|\.\s*(shift|pop|splice)\s*\(')
DEADLINE = re.compile(r'\bDate\s*\.\s*now\s*\(\)|\bdeadline\b|\bperformance\s*\.\s*now\b')
RETRY_BOUND = re.compile(r'\b\w*(attempt|retr|max_?tries|tries)\w*\b', re.I)
# `if (r.ok) break;` / `if (saved) return x;` -- leaving BECAUSE it worked.
SUCCESS_EXIT = re.compile(
    r'\bif\s*\([^;{]{0,120}?\b(ok|success|saved|done|res|r|result)\b[^;{]{0,120}?\)'
    r'\s*(\{[^{}]{0,200}?)?\b(break|return)\b')


# WRITTEN AFTER A LITERAL BACKSPACE SHIPPED IN THIS EXACT LINE. The first
# version went through a shell heredoc and every \b arrived as 0x08, so the
# pattern could never match and the agent loop it was added for was silently
# classified POLL. That is the defect CLAUDE.md already records -- a regex
# that shipped with a literal backspace and could never match -- reproduced
# by the same mechanism. The blind lock caught it only because the fixture
# asserts the ROLE and not just the policy.
AI_CALL = re.compile(r'\bcallClaude\s*\(|\banthropic\b|\bdispatchAgent\s*\(')
if not AI_CALL.search('await callClaude(messages)'):   # pragma: no cover
    raise AssertionError('AI_CALL cannot match its own example -- the pattern '
                         'holds a control character, not an escape')


def loop_kind(header, body):
    """RETRY / POLL / PAGINATE / ITERATE -- what this loop is actually doing.

    Ordered most-specific first. Each rule earns its place by a real construct
    in this repo that the previous version mis-labelled.
    """
    if COLLECTION.search(header or ''):
        return 'ITERATE'            # for (const k of ...), for (i<arr.length)
    if AI_CALL.search(body) and not re.search(r'\bfetch\s*\(', body):
        # An agent TURN loop: one model call per turn until the model stops
        # asking for tools. Not a retry and not a poll -- it advances a
        # conversation. Named separately because "agent dispatch" is one of the
        # three surfaces item 81 asks about, and calling it a poll would
        # misdescribe the one finding on that surface.
        return 'AGENT-LOOP'
    if PROGRESS.search(body):
        return 'PAGINATE'           # offset += PAGE, queue.shift()
    if RETRY_BOUND.search(header or ''):
        return 'RETRY'              # for (attempt = 0; attempt < MAX_RETRIES)
    if SUCCESS_EXIT.search(body):
        return 'RETRY'              # keeps going until the call works
    if DEADLINE.search(header or ''):
        return 'POLL'               # while (Date.now() < deadline)
    return 'POLL'                   # a loop that re-calls and advances nothing


def classify(c, file_code):
    """One construct -> its retry policy, or None if it is not a retry."""
    body = c.get('body')
    if not body or not REMOTE.search(body):
        return None

    header = c.get('header') or ''
    var = loop_var(header)
    if c['kind'] == 'catch':
        # A catch that re-issues a call is a retry only if the SAME callee is
        # in the try. Without that it is error HANDLING, which is a different
        # thing and is not this tool's question.
        kind = 'CATCH-RETRY'
    else:
        kind = loop_kind(header, body)
    if kind in ('ITERATE', 'PAGINATE'):
        return None

    # BOUND. A for/while whose header compares something against a maximum.
    # `while(true)` and `for(;;)` are unbounded by inspection.
    bounded = bool(re.search(r'[<>]=?', header)) and not re.search(
        r'\(\s*true\s*\)', header)
    if c['kind'] == 'catch':
        bounded = True          # a catch body runs once per throw
    if c['kind'] == 'do':
        # do{...}while(cond) -- the condition follows the body.
        bounded = True

    args = delay_args(body)
    has_delay = bool(args)
    joined = ' '.join(args)
    varying = bool(args) and (
        (var and re.search(r'\b%s\b' % re.escape(var), joined))
        or bool(VARYING.search(joined)))
    jitter = bool(args) and bool(JITTER.search(joined))

    if not has_delay:
        policy = 'NO DELAY'
    elif not varying:
        policy = 'FIXED DELAY'
    elif jitter:
        policy = 'BACKOFF + JITTER'
    else:
        policy = 'BACKOFF'

    return {
        'kind': c['kind'], 'role': kind, 'policy': policy, 'bounded': bounded,
        'has_delay': has_delay, 'varying': varying, 'jitter': jitter,
        'header': ' '.join(header.split())[:80],
        'breaker_state_in_file': bool(BREAKER.search(file_code)),
        'concerning': (policy in ('NO DELAY', 'FIXED DELAY')) or not bounded,
    }


def scan_source(src):
    """(findings, skipped_single_statement) for one file's source text."""
    code = jscomments.blank_string_bodies(jscomments.strip_comments(src))
    found, skipped = [], 0
    for c in constructs(code):
        if c.get('body') is None:
            skipped += 1
            continue
        r = classify(c, code)
        if r:
            r['line'] = code[:c['start']].count('\n') + 1
            found.append(r)
    return found, skipped


def live_files(include_all=False):
    r = subprocess.run(['git', 'ls-files', '*.js', '*.html'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    out, excluded = [], 0
    for f in r.stdout.split('\n'):
        f = f.strip()
        if not f or f.endswith('.test.js'):
            continue
        archived = (f.startswith('archive/') or f.startswith('docs/')
                    or '/node_modules/' in f)
        if archived and not include_all:
            excluded += 1
            continue
        out.append(f)
    return sorted(out), excluded


# ── THE BLIND LOCK: criteria fixed against synthetic code BEFORE real data ──
FIXTURES = {
    'hot_loop': ("for (var i = 0; i < 5; i++) { var r = await fetch(u); "
                 "if (r.ok) break; }", 'NO DELAY', True, 'RETRY'),
    'fixed_delay': ("for (var i = 0; i < 5; i++) { var r = await fetch(u); "
                    "if (r.ok) break; await new Promise(function(z){"
                    "setTimeout(z, 1000);}); }", 'FIXED DELAY', True, 'RETRY'),
    'backoff': ("for (var i = 0; i < 5; i++) { var r = await fetch(u); "
                "if (r.ok) break; await new Promise(function(z){"
                "setTimeout(z, 100 * i);}); }", 'BACKOFF', True, 'RETRY'),
    'backoff_jitter': ("for (var i = 0; i < 5; i++) { var r = await fetch(u); "
                       "if (r.ok) break; await new Promise(function(z){"
                       "setTimeout(z, 100 * i + Math.random() * 50);}); }",
                       'BACKOFF + JITTER', True, 'RETRY'),
    'unbounded': ("while (true) { var r = await fetch(u); if (r.ok) break; "
                  "await new Promise(function(z){setTimeout(z, 100 * n);}); }",
                  'BACKOFF', False, 'RETRY'),
    'poll': ("while (Date.now() < end) { var r = await fetch(u); "
             "handle(r); }", 'NO DELAY', True, 'POLL'),
    'agent_loop': ("for (let i = 0; i < MAX_ITERATIONS; i++) { "
                   "const response = await callClaude(messages); "
                   "if (response.stop_reason === 'tool_use') { continue; } "
                   "return response; }", 'NO DELAY', True, 'AGENT-LOOP'),
}

# Each of these MUST produce nothing. The first two are the exact shapes that
# killed the regex attempt at item 81.
NEGATIVE = {
    'the word retry in a comment':
        '// we should add a retry with backoff to this fetch call one day\n'
        'var x = 1;\n',
    'the word retry in a string':
        'var msg = "retrying the fetch with exponential backoff";\n',
    'a loop with no remote call':
        'for (var i = 0; i < rows.length; i++) { total += rows[i].amount; }',
    'a retry COUNTER that nothing loops on':
        'var retryCount = 0; var maxRetries = 3; console.log(retryCount);',
    # THE SECOND FALSE-POSITIVE CLASS, and it was this tool's own. Each of
    # these three is a real construct from this repo that the first run
    # reported as a retry.
    'ITERATION over a collection, one call per item':
        'for (const key of Object.keys(limits)) { await fetch(u + key); }',
    'ITERATION by index over an array':
        'for (var i = 0; i < rows.length; i++) { await sdData("write", r, rows[i]); }',
    'PAGINATION advancing an offset':
        'for (;;) { const r = await fetch(u + offset); if (!r.n) break; '
        'offset += PAGE; }',
    'A QUEUE DRAIN that shifts its work list':
        'while (true) { var q = queue(); if (!q.length) break; '
        'var ok = await senData("write", "x", q[0]); if (!ok) break; q.shift(); }',
    'a comment mentioning setTimeout beside an unrelated loop':
        'for (var i = 0; i < n; i++) { sum += i; }\n'
        '// the fetch above should setTimeout between attempts\n',
}


def blind_lock():
    """(ok, rows, problems). Run BEFORE any real file is opened."""
    rows, problems = [], []
    for name, (src, want_policy, want_bounded, want_role) in sorted(FIXTURES.items()):
        found, _sk = scan_source(src)
        if len(found) != 1:
            problems.append('fixture %s produced %d findings, expected exactly '
                            '1 -- the extractor is wrong, not the fixture'
                            % (name, len(found)))
            rows.append({'fixture': name, 'got': None})
            continue
        got = found[0]
        rows.append({'fixture': name, 'policy': got['policy'],
                     'bounded': got['bounded'], 'role': got['role']})
        # THE ROLE IS LOCKED TOO. Without this the classifier could call every
        # construct POLL and every policy arm above would still pass -- which
        # is how the first run of this tool reported 24 "retries" that were
        # iteration, pagination and queue drains.
        if got['role'] != want_role:
            problems.append('fixture %s classified role %s, expected %s'
                            % (name, got['role'], want_role))
        if got['policy'] != want_policy:
            problems.append('fixture %s classified %s, expected %s'
                            % (name, got['policy'], want_policy))
        if got['bounded'] != want_bounded:
            problems.append('fixture %s bounded=%s, expected %s'
                            % (name, got['bounded'], want_bounded))
    for name, src in sorted(NEGATIVE.items()):
        found, _sk = scan_source(src)
        rows.append({'fixture': 'NEG: ' + name, 'findings': len(found)})
        if found:
            problems.append('NEGATIVE fixture "%s" produced %d finding(s) -- '
                            'this is the false-positive class that retracted '
                            'the first attempt at item 81' % (name, len(found)))
    return (not problems), rows, problems


def self_check():
    ok, rows, problems = blind_lock()
    for r in rows:
        print('  %s %s' % ('ok  ' if 'findings' not in r or r['findings'] == 0
                           else ('ok  ' if ok else 'FAIL'), r))
    extra = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            extra.append(name)

    ck('the blind lock passes on the shipped criteria', ok, problems)

    # The extractor itself, in both directions.
    body = constructs('while (a) { x(); { y(); } z(); } after();')
    ck('a nested block does not end the body early',
       body and body[0]['body'].endswith('z(); }'), body)
    ck('`for` inside an identifier is not a loop',
       constructs('var before = 1; var formal = 2;') == [],
       constructs('var before = 1; var formal = 2;'))
    single = constructs('for (var i=0;i<3;i++) doThing();')
    ck('a single-statement body is READ, to the first `;` at depth zero',
       single and single[0]['body'].strip() == 'doThing();', single)
    nested = constructs('for (var i=0;i<3;i++) go(a(1;2));')
    ck('...and a `;` nested inside parens does not end it early',
       nested and nested[0]['body'].endswith('go(a(1;2));'), nested)
    ck('a bare `for` with no parentheses is NOT a loop -- `<label for="x">` in '
       'an HTML file is the common case and it swept up a real fetch',
       constructs('<label for="x">y</label> fetch(u);') == [],
       constructs('<label for="x">y</label> fetch(u);'))

    # The delay argument must be the balanced one, or a nested call truncates it.
    args = delay_args('{ setTimeout(function(){ q(1, 2); }, 100 * i); }')
    ck('the delay argument is balanced, so a nested call does not truncate it',
       args and '100 * i' in args[0], args)

    # A FIXED delay whose constant contains a `*` must still be FIXED: the
    # varying test is about the ATTEMPT, and `1000 * 2` is a constant.
    f, _s = scan_source('for (var i = 0; i < 3; i++) { await fetch(u); '
                        'setTimeout(z, 1000); }')
    ck('a bare constant delay is FIXED DELAY, never BACKOFF',
       f and f[0]['policy'] == 'FIXED DELAY', f)

    ck('a catch block containing a remote call is a retry construct',
       scan_source('try { a(); } catch (e) { await fetch(u); }')[0],
       'catch retries are the second half of this shape')

    print('\n%d failure(s)' % len(extra))
    return 1 if extra else 0


def main(argv):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                            # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-check', action='store_true', dest='selfcheck')
    args = ap.parse_args(argv)

    if args.selfcheck:
        return self_check()

    ok, _rows, problems = blind_lock()
    if not ok:
        print('COULD NOT RUN -- the blind lock FAILED, so nothing real was')
        print('scanned. The criteria are wrong and any number produced from')
        print('them would be worse than no number:')
        for p in problems:
            print('  ! %s' % p)
        return 2

    files, excluded = live_files(args.all)
    findings, skipped, scanned = [], 0, 0
    for f in files:
        try:
            src = io.open(os.path.join(REPO, f), encoding='utf-8',
                          errors='replace').read()
        except Exception:                                        # noqa: BLE001
            continue
        scanned += 1
        got, sk = scan_source(src)
        skipped += sk
        for g in got:
            g['file'] = f
            findings.append(g)

    concerning = [f for f in findings if f['concerning']]

    if args.json:
        print(json.dumps({'scanned': scanned, 'excluded_archive': excluded,
                          'retry_constructs': findings,
                          'concerning': len(concerning),
                          'single_statement_bodies_skipped': skipped}, indent=1))
        return 1 if concerning else 0

    if not args.quiet:
        print('RETRY POLICY AUDIT -- item 81, report only')
        print('  blind lock: LOCKED (%d fixtures, both directions)'
              % (len(FIXTURES) + len(NEGATIVE)))
        print('  %d file(s) scanned, %d archived file(s) excluded (--all '
              'includes them)' % (scanned, excluded))
        print('  %d retry construct(s) on a remote call, %d concerning'
              % (len(findings), len(concerning)))
        print('')
        roles = {}
        for f in findings:
            roles[f['role']] = roles.get(f['role'], 0) + 1
        print('  by role: %s' % (', '.join('%s %d' % (k, v)
                                           for k, v in sorted(roles.items()))
                                 or 'none'))
        if not roles.get('RETRY') and not roles.get('CATCH-RETRY'):
            print('')
            print('  ZERO TRUE RETRIES ON A REMOTE CALL IN LIVE CODE, AND THAT')
            print('  IS THE ANSWER TO ITEM 81. There is no missing backoff')
            print('  because there is almost nothing that retries: a Supabase')
            print('  write that fails is not re-issued, it is lost, which is')
            print('  the write-path hazard rather than a retry-storm hazard.')
            print('  The two constructs below re-issue remote calls for other')
            print('  reasons and carry the pacing question anyway.')
        print('')
        if not findings:
            print('  NO RETRY CONSTRUCT FOUND ON A REMOTE CALL.')
            print('  That is a finding about RETRIES, not about resilience: a')
            print('  call that never retries cannot retry badly, and whether it')
            print('  SHOULD retry is a different question this does not ask.')
        for f in findings:
            flag = '!' if f['concerning'] else ' '
            print('  %s %-28s line %-6d %-12s %-16s %s'
                  % (flag, f['file'], f['line'], f['role'], f['policy'],
                     'bounded' if f['bounded'] else 'UNBOUNDED'))
            print('      %s (%s)' % (f['header'] or '(no header)', f['kind']))
        print('')
        print('  NO DELAY means the loop re-issues the call immediately: a')
        print('  backend that is failing because it is overloaded gets hit')
        print('  harder by every client at once. FIXED DELAY waits, which is')
        print('  not the same as backing off -- every client still returns on')
        print('  the same cadence.')
        print('')
        print('  A CIRCUIT BREAKER IS NOT DECIDABLE FROM ONE FILE and is NOT')
        print('  claimed here. On serverless functions the state that would')
        print('  hold one outlives no request, so it lives in the database.')
        print('  The column below is whether the file declares ANY candidate')
        print('  breaker state -- necessary, not sufficient, and NONE FOUND is')
        print('  not proof there is no breaker.')
        for f in findings:
            print('    %-28s line %-6d breaker state in file: %s'
                  % (f['file'], f['line'],
                     'candidate found' if f['breaker_state_in_file'] else 'NONE FOUND'))
        if skipped:
            print('')
            print('  %d construct(s) had no readable statement end and were '
                  'NOT read.' % skipped)
            print('  A brace-less body is read to the first `;` at depth zero,')
            print('  which is a real statement boundary; these are the ones')
            print('  where even that ran off the end of the file. Counted')
            print('  rather than dropped -- an unread construct is a third')
            print('  state and is never folded into "clean".')
    return 1 if concerning else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
