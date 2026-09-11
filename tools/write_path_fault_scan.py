"""write_path_fault_scan.py -- which server writes are blind to a WORLD failure.

    python tools/write_path_fault_scan.py [app.html ...]

── WHY, AND THE EVIDENCE IS ONE DAY OLD ────────────────────────────────────
The first fault-injection run this platform has done (2026-09-10,
tests/faults/) was pointed at ONE write path -- SAIRNdental's vendor objects --
and found three live defects in it:

  * a DROPPED SOCKET rejected, and a rejection never reaches a
    `.then(ok => ...)` handler, so the user clicked Save on a dead connection
    and saw NOTHING;
  * a HANG never settled and there was no timeout anywhere on the path;
  * a PARTIAL RESPONSE counted as success and cleared a guard flag.

Fifteen apps issue a server write. Writing a dynamic fault suite for each is
weeks of work and most of it would land on paths that are already safe, so this
finds WHERE THE HAZARD IS first. It is a pointer, not a verdict -- the same
standing tools/sairn_reachability_probe.py gives itself.

── THE THREE HAZARD SHAPES IT LOOKS FOR ────────────────────────────────────
 1. FIRE-AND-FORGET -- the write is a bare statement. Nothing reads the result,
    so a refusal, a rejection and a success are indistinguishable, and a
    rejection is an unhandled promise rejection as well.
 2. THEN-WITHOUT-CATCH -- the result is read, but only on the success path. A
    rejection skips it entirely. This is the shape that produced the silent
    Save on SAIRNdental, and reading the code does not reveal it: the handler
    is right there and looks complete.
 3. NO TIMEOUT ANYWHERE -- nothing on the file's write path races a timer, so a
    hung connection is indistinguishable from a user who has not clicked.

── WHAT IT CANNOT TELL YOU, said here rather than discovered later ─────────
 * Whether a caller ABOVE the write handles the failure. A wrapper returning a
   promise its caller inspects is counted as fire-and-forget here and may be
   perfectly safe. Read the site.
 * Whether the user is actually TOLD. That needs the dynamic harness; this only
   finds where it is worth pointing one.
 * Anything about writes that do not go through a `*Data('write', ...)` call.
"""
import bisect
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jscomments                                              # noqa: E402

WRITE = re.compile(r"\b([a-zA-Z_]\w*[Dd]ata)\(\s*'write'")
# A timeout on the write path: a race against a timer, or an AbortController.
TIMEOUT = re.compile(r'Promise\.race\s*\(|AbortController|AbortSignal|signal\s*:')
FN_OPEN = re.compile(r'\bfunction\s+(\w+)\s*\(')

# ── THE TIMEOUT COLUMN WAS WRONG IN THE OPTIMISTIC DIRECTION, 2026-09-10 ────
# The first version ran TIMEOUT over RAW SOURCE and reported yes/no for the
# whole file. Both halves of that were wrong, and both made an unprotected app
# look protected -- the one direction a hazard scan must never fail in:
#
#   * STRING LITERALS COUNTED. `sairngrounds.html` was reported `yes` on the
#     strength of two user-facing sentences -- "Weather Command Engine signal: "
#     -- matching `signal\s*:`. That file contains no timer race, no
#     AbortController and no AbortSignal anywhere. It has EIGHT fire-and-forget
#     writes and was reading as the one thing that made them survivable.
#
#   * A READ-PATH TIMEOUT COUNTED AS A WRITE-PATH TIMEOUT. This is a
#     WRITE-path hazard table, and `sairnbiz.html`'s only race bounds
#     `sbFirstDeviceHydrate()` (a hydrate, documented at the site as bounding
#     first paint), while `stonedesk.html`'s only `AbortSignal.timeout(8000)` is
#     on `/api/knowledge`, a read. Neither protects a single write.
#
# So the portfolio line "eleven of fifteen apps have NO TIMEOUT anywhere" was
# itself too kind: measured properly it is THIRTEEN of fifteen, and only
# sairndental and sairnvet have a real one. The column is now three-state, and
# `read-only` is deliberately not spelled `yes` -- an app whose reads are
# bounded and whose writes can hang forever is the NO case for this table.
def inside_string_on_line(code, pos):
    r"""Is `pos` inside a quoted literal, judged from the START OF ITS LINE?

    DELIBERATELY LINE-LOCAL, and the first attempt is why. Blanking every string
    in the file desynced on sairnvet.html -- one quote-state slip early on and
    `Promise.race` at line 2178 vanished from the scan entirely, turning a real
    write-path timeout into `NO`. A whole-file quote walk that goes wrong goes
    wrong for the REST OF THE FILE, which is the worst possible failure mode for
    a detector. Scanning from the line start cannot drift further than one line.

    It also cannot be done on a string-blanked copy of the source at all, because
    the thing this tool searches for IS a string: `*Data('write'`. Blanking
    literals erased every write call site. Comments are stripped globally (safe,
    length-preserving); strings are judged here, per hit.

    LIMIT, stated: a `signal:` inside a MULTI-LINE template literal reads as
    code. The real false positive this closes is a one-line user-facing message
    -- sairngrounds' "Weather Command Engine signal: " -- and no multi-line
    template on any current write path contains a timeout token.
    """
    bol = code.rfind(chr(10), 0, pos) + 1
    quote, i = None, bol
    while i < pos:
        c = code[i]
        if quote:
            if c == chr(92):          # backslash escape
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in ('"', chr(39), '`'):
            quote = c
        i += 1
    return quote is not None


def timeout_state(src):
    """'write', 'read-only' or 'none' -- measured on code, never on prose."""
    code = jscomments.strip_comments(src)
    hits = [m.start() for m in TIMEOUT.finditer(code)
            if not inside_string_on_line(code, m.start())]
    if not hits:
        return 'none'
    # A hit or a write belongs to the last `function NAME(` opening before it.
    # Crude, and crude is the right amount here: the question is "is the timer in
    # the same function as a write", not "is it reachable on the call graph".
    opens = [(m.start(), m.group(1)) for m in FN_OPEN.finditer(code)]
    starts = [o[0] for o in opens]

    def owner(pos):
        k = bisect.bisect_right(starts, pos) - 1
        return opens[k][1] if k >= 0 else None

    # Two ways a timeout can be on the write path, and the second was missed at
    # first. (a) the timer sits in the same function as a write call -- SAIRNvet's
    # svPushOne(), SAIRNdental's dntPushOne(). (b) THE TIMER SITS IN THE SHARED
    # TRANSPORT the write calls, which protects all 43 of SAIRNgrounds' writes at
    # once and is in the same function as none of them. Reporting (b) as
    # `read-only` called the broadest possible fix the weakest -- the same
    # flags-its-own-repair shape the `.then(ok, err)` blindness had.
    writing = set(owner(m.start()) for m in WRITE.finditer(code))
    transports = set(m.group(1) for m in WRITE.finditer(code))
    for h in hits:
        own = owner(h)
        if own in writing or own in transports:
            return 'write'
    return 'read-only'


def apps(argv):
    if argv:
        return argv
    r = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                       capture_output=True, text=True)
    return [f for f in r.stdout.split('\n') if f.strip() and '/' not in f]


def then_takes_reject_handler(tail):
    """Does the first `.then(` in `tail` pass a SECOND argument?

    `.then(onFulfilled, onRejected)` handles a rejection exactly as `.catch`
    does, and the first version of this tool only looked for the literal
    `.catch(`. So it reported `then-no-catch` on two sites that are the FIXES
    for this very hazard -- svPushOne() in sairnvet.html and dntPushOne() in
    sairndental.html, both of which map a rejection onto null through the
    two-argument form. A checker that flags the repair is how a checker gets
    switched off, so the distinction is made here rather than in a reader's head.

    Found 2026-09-10 by the SAIRNvet fix landing on its own report.

    Brace/paren balanced rather than regex, because the comma that matters is
    the one at the TOP level of the argument list -- `.then(function(r){
    foo(a,b); })` has a comma and takes one argument. String literals are
    skipped so a comma inside a message does not count. LIMIT, stated rather
    than discovered: a regex literal containing an unbalanced bracket or quote
    would confuse the scan. None exists on any current write path, and this is
    a pointer tool, not a parser.
    """
    i = tail.find('.then(')
    if i < 0:
        return False
    i += len('.then(')
    depth, quote = 1, None
    while i < len(tail):
        c = tail[i]
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in '"\'`':
            quote = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                return False          # argument list closed, one argument only
        elif c == ',' and depth == 1:
            return True
        i += 1
    return False


COLLECT = re.compile(r'(?:await|return|=)\s*Promise\.'
                     r'(?:all|allSettled|race|any)\s*\(\s*\[?\s*$')


def inside_awaited_collection(src, pos):
    r"""Is this write an ELEMENT of an awaited or returned Promise.all([...])?

    FIVE OF THE EIGHT SAIRNgrounds "fire-and-forget" sites were this, and all
    five were safe -- found 2026-09-10 by reading every flagged site before
    starting work on them, which is the rule this tool prints on every run.
    `await Promise.all([grdData('write',...), ...])` then inspects `results[i]`
    and names in a toast exactly which records did not sync. That is the most
    careful write-reporting on the platform, and it was being reported as the
    least.

    The `assigned` regex below looks 40 characters behind the call for
    `var x =` / `return` / `await`, so it cannot see an `await` that sits before
    a `Promise.all([` and a line break. Over-reporting is the direction that
    gets a checker switched off, which is why this is fixed rather than noted.

    Walks back from the call to the opening bracket of the enclosing argument
    list and checks what introduces it. Bounded at 400 characters: a collection
    literal longer than that is not a shape this platform writes.
    """
    i, depth, window = pos - 1, 0, max(0, pos - 400)
    while i >= window:
        c = src[i]
        if c in ')]}':
            depth += 1
        elif c in '([{':
            if depth == 0:                      # the bracket this call sits in
                return bool(COLLECT.search(src[max(0, i - 80):i + 1]))
            depth -= 1
        i -= 1
    return False


def classify(src, m):
    """What does the code do with this write's result?

    Looks at the statement the call sits in, bounded by the enclosing line and
    a short window after -- enough to see `.then(`/`.catch(` chained onto it
    without running into the next statement.
    """
    start = src.rfind('\n', 0, m.start()) + 1
    window = src[start:m.start() + 600]
    # Cut at the first statement boundary that is not inside the chain.
    tail = src[m.end():m.end() + 600]
    has_then = '.then(' in tail[:400]
    has_catch = '.catch(' in tail[:400] or then_takes_reject_handler(tail[:400])
    assigned = bool(re.search(r'(?:var|let|const)\s+\w+\s*=\s*$|return\s+$|await\s+$',
                              src[max(0, m.start() - 40):m.start()]))
    if has_then and has_catch:
        return 'handled'
    if has_then:
        return 'then-no-catch'
    if assigned or inside_awaited_collection(src, m.start()):
        return 'awaited-or-returned'
    return 'fire-and-forget'


def scan(path):
    raw = io.open(os.path.join(REPO, path), encoding='utf-8', errors='replace').read()
    # COMMENTS STRIPPED BEFORE FINDING WRITE SITES, added 2026-09-10 the moment it
    # bit. The SAIRNgrounds fix carried a comment explaining the house pattern and
    # quoting it -- `var syncResult = await grdData('write', ...)` -- and the scan
    # dutifully reported a fire-and-forget write inside a comment, at a line where
    # no code exists. Same shape as the wrapper-honesty check counting a comment as
    # a log: prose satisfying a code detector. strip_comments() is length- and
    # newline-preserving, so every reported line number stays true.
    src = jscomments.strip_comments(raw)
    counts = {'handled': 0, 'then-no-catch': 0, 'awaited-or-returned': 0,
              'fire-and-forget': 0}
    lines = []
    for m in WRITE.finditer(src):
        k = classify(src, m)
        counts[k] += 1
        if k in ('then-no-catch', 'fire-and-forget'):
            lines.append((src[:m.start()].count('\n') + 1, k, m.group(1)))
    return counts, lines, timeout_state(src)


def main(argv):
    targets = apps([a for a in argv if not a.startswith('-')])
    print('WRITE-PATH FAULT HAZARDS -- a pointer, not a verdict. Read every site.')
    print('')
    print('%-28s %7s %9s %9s %9s  %s'
          % ('app', 'handled', 'await/ret', 'then-only', 'fire&for', 'timeout?'))
    total_blind = 0
    detail = []
    for t in sorted(targets):
        counts, lines, tstate = scan(t)
        if not any(counts.values()):
            continue
        blind = counts['then-no-catch'] + counts['fire-and-forget']
        total_blind += blind
        print('%-28s %7d %9d %9d %9d  %s'
              % (t, counts['handled'], counts['awaited-or-returned'],
                 counts['then-no-catch'], counts['fire-and-forget'],
                 {'write': 'yes', 'read-only': 'read-only', 'none': 'NO'}[tstate]))
        if lines:
            detail.append((t, lines))
    print('')
    print('%d write call site(s) across the portfolio read their result on the '
          'SUCCESS PATH ONLY or not at all.' % total_blind)
    print('')
    print('A `then-only` site is the shape that produced the silent Save on')
    print('SAIRNdental: the handler is right there and looks complete, and a')
    print('rejection skips it. A `fire&for` site cannot tell a refusal from a')
    print('success at all, and a rejection there is unhandled.')
    print('')
    print('NO under timeout means nothing in that file races a timer or uses an')
    print('AbortController, so a hung connection is indistinguishable from a')
    print('user who has not clicked.')
    for t, lines in detail:
        print('')
        print('-- %s --' % t)
        for ln, kind, fn in lines[:40]:
            print('   %-16s line %-6d %s(' % (kind, ln, fn))
        if len(lines) > 40:
            print('   ...and %d more' % (len(lines) - 40))
    print('')
    print('THIS IS NOT A LIST OF DEFECTS. A wrapper whose caller inspects the')
    print('promise is counted as fire-and-forget here and may be entirely safe.')
    print('It says where a dynamic fault suite is worth pointing, which is the')
    print('only question it was built to answer.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
