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
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRITE = re.compile(r"\b([a-zA-Z_]\w*[Dd]ata)\(\s*'write'")
# A timeout on the write path: a race against a timer, or an AbortController.
TIMEOUT = re.compile(r'Promise\.race\s*\(|AbortController|signal\s*:')


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
    if assigned:
        return 'awaited-or-returned'
    return 'fire-and-forget'


def scan(path):
    src = io.open(os.path.join(REPO, path), encoding='utf-8', errors='replace').read()
    counts = {'handled': 0, 'then-no-catch': 0, 'awaited-or-returned': 0,
              'fire-and-forget': 0}
    lines = []
    for m in WRITE.finditer(src):
        k = classify(src, m)
        counts[k] += 1
        if k in ('then-no-catch', 'fire-and-forget'):
            lines.append((src[:m.start()].count('\n') + 1, k, m.group(1)))
    return counts, lines, bool(TIMEOUT.search(src))


def main(argv):
    targets = apps([a for a in argv if not a.startswith('-')])
    print('WRITE-PATH FAULT HAZARDS -- a pointer, not a verdict. Read every site.')
    print('')
    print('%-28s %7s %9s %9s %9s  %s'
          % ('app', 'handled', 'await/ret', 'then-only', 'fire&for', 'timeout?'))
    total_blind = 0
    detail = []
    for t in sorted(targets):
        counts, lines, has_timeout = scan(t)
        if not any(counts.values()):
            continue
        blind = counts['then-no-catch'] + counts['fire-and-forget']
        total_blind += blind
        print('%-28s %7d %9d %9d %9d  %s'
              % (t, counts['handled'], counts['awaited-or-returned'],
                 counts['then-no-catch'], counts['fire-and-forget'],
                 'yes' if has_timeout else 'NO'))
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
