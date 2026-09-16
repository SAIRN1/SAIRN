"""A dropped write, and a success message that could not possibly depend on it.

    python tools/optimistic_success_scan.py
    python tools/optimistic_success_scan.py --app sairngrounds.html
    python tools/optimistic_success_scan.py --fixtures
    python tools/optimistic_success_scan.py --json

Exit 0 when nothing is reportable, 1 on a candidate, 2 when an app could not be
read. REPORT ONLY -- every hit needs a human, and the tool says why below.

── THE SHAPE, AND WHY `write_path_fault_scan.py` CANNOT SEE IT ────────────────
That tool asks whether a call to the DATA WRAPPER reads its result, matching the
wrapper by name (`grdData(`, `sdData(`). On 2026-09-15 that reported
sairngrounds clean while `addCoursePoint()` was announcing "Point captured" for
writes that never reached the server.

THE FIRE-AND-FORGET HAD MOVED ONE LEVEL UP. `cmSavePoints()` -- a LOCAL ASYNC
HELPER -- awaited the wrapper correctly and reported honestly. Its three callers
dropped the promise it returned and toasted success anyway. The wrapper was
read; the helper was not; and a scanner matching the wrapper by name sees the
first and not the second.

── THE RULE, AND IT NEEDS NO WORD LIST ────────────────────────────────────────
A caller that DROPS a write's promise cannot condition anything on the result --
the result does not exist in that scope. So:

    a dropped write call, plus ANY later `toast()` in the same function,
    is a message that CANNOT depend on whether the write succeeded.

That is structural. It does not guess whether a message reads as success, which
would be a word list and would be wrong in both directions. The message text is
PRINTED so a human can see which kind it is.

── WHY A CORRECTION LATER IS NOT A DEFENCE ────────────────────────────────────
The obvious rebuttal, and it was made in writing at the real site: `toast()` is
`textContent = m`, so a later honest message REPLACES the optimistic one when
the push resolves.

**A MESSAGE THAT CORRECTS AN EARLIER MESSAGE ONLY CORRECTS IT IF IT IS THE NEXT
MESSAGE.** Where the action repeats -- capturing points, adding lines, saving
rows in a run -- a second action routinely starts before the first resolves and
overwrites the correction with another optimistic claim. So a deferred
correction is not a reason to dismiss a hit; it is a reason to check whether the
action can repeat.

── WHAT IT CANNOT DO, AND THE SECOND ONE IS THE REAL LIMIT ────────────────────
  * Decide that a hit is a defect. Some unconditional messages are RIGHT and
    recorded as such -- `gcdSaveRound()` fires per shot and a per-call toast
    would drown the messages somebody is waiting on. Those are decisions and
    this cannot read one.
  * FOLLOW MORE THAN ONE HOP. It finds helpers that write directly. A helper
    calling a helper that writes is invisible here, so a clean app is a FLOOR
    and not a clearance -- the same limit the tool that missed this one had,
    moved one level further out rather than removed.
  * See a message that is not a `toast()`.
  * TELL A LATER TOAST FROM A TOAST IN ANOTHER BRANCH, and this is the dominant
    DOMINANT FALSE POSITIVE rather than a theoretical one. "Any toast after the
    call in
    the same function" catches a message in the `else` arm the call can never
    reach. MEASURED on the first real sweep: of 8 candidates left after the
    three real fixes, FOUR were this shape -- `sairnlaw.sendAI`,
    `sairnsenior.confirmClaimAction` twice, and `sairndesign` after its own fix.
    Narrowing it needs a real JS parser rather than brace matching, which is a
    different tool; the number is stated here so nobody reads the hit count as
    a defect count.

── SO THE FIRST SWEEP'S RESULT, IN FULL ───────────────────────────────────────
14 candidates. THREE REAL AND FIXED (sairndental `addSupply` and `vPlaceOrder`,
sairndesign `markRoomARPoint`), FOUR ACCEPTED AND RECORDED AT THE SITE
(sairngrounds' `gcdSaveRound` callers -- per-shot writes whose silence is a
decision with a written reason), FOUR the branch false positive above, and three
`dcCreateInvoiceAndSchedule` hits that were a rule defect here and are fixed:
an element of an awaited array takes its result, and the first version said
otherwise.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CRITERIA_VERSION = '2026-09-16.1'

# The platform convention: every app's server call is `<prefix>Data(...)`.
WRITE_CALL = re.compile(r"\b(\w*[Dd]ata)\(\s*['\"]write['\"]")
# A function declaration, in the two shapes this platform uses.
FUNC_DECL = re.compile(r'^\s*(?:async\s+)?function\s+(\w+)\s*\(', re.M)
# A call whose result is NOT taken. The leading group is what would take it.
# PASSING THE CALL AS AN ARGUMENT TAKES ITS RESULT TOO. `Promise.resolve(f(x))`
# and `pushes.push(f(x))` hold the promise perfectly well, and the first version
# reported both as dropped -- a false finding on the code that had just been
# fixed, which is the worst possible direction for a tool whose whole subject is
# a result nobody reads.
TAKEN = r'(?:await\s+|return\s+|=\s*|\.then|\)\s*\.|\(\s*|,\s*|\[\s*)'


def apps():
    r = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return sorted(f for f in r.stdout.split('\n') if f.strip() and '/' not in f)


def strip_comments(src):
    """Line comments only. Block comments are rare in these files and a naive
    block stripper eats regex literals, which is worse than leaving them."""
    return re.sub(r'(?m)^\s*//[^\n]*$', '', src)


def functions(src):
    """[(name, start, end)] by brace matching from the declaration."""
    out = []
    for m in FUNC_DECL.finditer(src):
        i = src.find('{', m.end())
        if i < 0:
            continue
        depth, j = 0, i
        while j < len(src):
            if src[j] == '{':
                depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((m.group(1), m.start(), j))
    return out


def write_helpers(src, funcs):
    """Function names whose OWN body performs a server write. The data wrapper
    itself is included, so a caller dropping it directly is still seen."""
    names = set(WRITE_CALL.findall(src))
    for name, a, b in funcs:
        if WRITE_CALL.search(src[a:b]):
            names.add(name)
    return names


def scan(src):
    """[(caller, helper, line, toast_text)] -- every dropped write call whose
    enclosing function later raises a toast."""
    src = strip_comments(src)
    funcs = functions(src)
    helpers = write_helpers(src, funcs)
    hits = []
    for name, a, b in funcs:
        body = src[a:b]
        for h in sorted(helpers):
            if h == name:
                continue
            for m in re.finditer(r'(%s)?\b%s\s*\(' % (TAKEN, re.escape(h)), body):
                if m.group(1):
                    continue
                # A declaration is not a call.
                before = body[max(0, m.start() - 20):m.start()]
                if re.search(r'function\s+$', before):
                    continue
                # A RESULT CAN ALSO BE TAKEN AFTERWARDS. `saveThing(z).then(...)`
                # has nothing in front of it and holds the promise perfectly
                # well; a rule that only looked backwards reported it as
                # dropped, which is a false finding on correct code.
                depth, k = 1, m.end()
                while k < len(body) and depth:
                    if body[k] == '(':
                        depth += 1
                    elif body[k] == ')':
                        depth -= 1
                    k += 1
                if re.match(r'\s*\.\s*(then|catch|finally)\b', body[k:]):
                    continue
                after = body[m.end():]
                t = re.search(r"\btoast\(\s*(['\"])(.*?)\1", after, re.S)
                if not t:
                    continue
                line = src[:a].count('\n') + body[:m.start()].count('\n') + 1
                hits.append((name, h, line, re.sub(r'\s+', ' ', t.group(2))[:90]))
    return hits


# ── THE BLIND LOCK ────────────────────────────────────────────────────────────
FIXTURES = {
    'the real shape -- a dropped helper then a toast': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ var r = await xData('write','t',z); if(!r)toast('did not sync'); return r; }
async function addThing(){ saveThing(z); toast('Thing captured'); }
""", 1),
    'CONTROL: the caller AWAITS, so the message can depend on the result': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ var r = await xData('write','t',z); return r; }
async function addThing(){ var ok = await saveThing(z); if(ok)toast('Thing captured'); }
""", 0),
    'CONTROL: the caller ASSIGNS the promise, so it is still held': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ var r = await xData('write','t',z); return r; }
async function addThing(){ var p = saveThing(z); toast('Thing captured'); }
""", 0),
    'CONTROL: a dropped write with NO toast is not a hit -- this tool is about '
    'the CLAIM, not about the drop': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ var r = await xData('write','t',z); return r; }
async function addThing(){ saveThing(z); }
""", 0),
    'CONTROL: a helper that does not WRITE is not a write helper': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function readThing(z){ return await xData('read','t',z); }
async function addThing(){ readThing(z); toast('Thing loaded'); }
""", 0),
    'the DATA WRAPPER dropped directly is still seen': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function addThing(){ xData('write','t',z); toast('Thing captured'); }
""", 1),
    'CONTROL: a `.then` chain takes the result': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ return await xData('write','t',z); }
async function addThing(){ saveThing(z).then(function(ok){ if(ok)toast('ok'); }); }
""", 0),
    'CONTROL: a toast BEFORE the dropped call is not a claim about it': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ return await xData('write','t',z); }
async function addThing(){ toast('Saving...'); saveThing(z); }
""", 0),
    'CONTROL: passing the call as an ARGUMENT takes its result': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ return await xData('write','t',z); }
async function addThing(){ pushes.push(saveThing(z)); toast('Thing captured'); }
""", 0),
    'CONTROL: a bare statement call INSIDE a callback is still dropped': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ return await xData('write','t',z); }
async function addThing(){ list.forEach(function(z){ saveThing(z); }); toast('done'); }
""", 1),
    'CONTROL: an element of an awaited array takes its result too': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function addThing(){
  var rs = await Promise.all([xData('write','a',1), xData('write','b',2)]);
  toast(rs.every(Boolean) ? 'done' : 'partial');
}
""", 0),
    'CONTROL: a commented-out call is not a call': ("""
async function xData(op, res, row){ return fetch('/x'); }
async function saveThing(z){ return await xData('write','t',z); }
async function addThing(){
  // saveThing(z);
  toast('Thing captured');
}
""", 0),
}


def fixtures():
    out, bad = [], 0
    for name, (src, want) in FIXTURES.items():
        got = len(scan(src))
        ok = got == want
        out.append(('  ok   ' if ok else '  FAIL ') + name
                   + ('' if ok else '  <- expected %d hit(s), got %d: %s'
                      % (want, got, scan(src))))
        if not ok:
            bad += 1
    return out, bad


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('OPTIMISTIC SUCCESS SCAN -- blind lock, %d arms, no app read'
              % len(lines))
        for l in lines:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    lines, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- no app was read.')
        for l in lines:
            print(l)
        return 2

    want = argv[argv.index('--app') + 1] if '--app' in argv else None
    targets = [want] if want else apps()
    if not targets:
        print('COULD NOT LIST APPS -- nothing was scanned. NOT a clean run.')
        return 2

    results, unread = [], []
    for a in targets:
        p = os.path.join(REPO, a)
        if not os.path.isfile(p):
            unread.append(a)
            continue
        try:
            src = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError as e:
            unread.append('%s (%s)' % (a, e))
            continue
        for caller, helper, line, msg in scan(src):
            results.append({'app': a, 'caller': caller, 'helper': helper,
                            'line': line, 'message': msg})

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'unread': unread, 'candidates': results}, indent=2))
        return 1 if results else (2 if unread else 0)

    print('OPTIMISTIC SUCCESS SCAN -- criteria %s' % CRITERIA_VERSION)
    print('  %d fixture arms passed before any app was read.' % len(lines))
    print('  %d app(s) scanned, %d candidate(s).' % (len(targets) - len(unread),
                                                     len(results)))
    print('')
    if unread:
        print('  COULD NOT READ, and this is NOT a clean result for them:')
        for u in unread:
            print('    %s' % u)
        print('')
    if not results:
        print('  No caller drops a write and then raises a toast.')
    for r in results:
        print('  %s:%d' % (r['app'], r['line']))
        print('    %s() drops %s(), then: "%s"'
              % (r['caller'], r['helper'],
                 r['message'].encode('ascii', 'replace').decode('ascii')))
    print('')
    print('  THESE ARE CANDIDATES, NOT DEFECTS. A message that cannot depend on')
    print('  the write is sometimes the RIGHT design and is recorded as such --')
    print('  a per-shot write toasting every failure drowns the messages')
    print('  somebody is waiting on. This cannot read a decision; it finds the')
    print('  shape and prints the message so a human can tell which it is.')
    print('')
    print('  AND A CLEAN RUN IS A FLOOR, NOT A CLEARANCE: this follows ONE hop.')
    print('  A helper calling a helper that writes is invisible here -- the same')
    print('  limit that let this class hide from write_path_fault_scan.py, moved')
    print('  one level further out rather than removed.')
    return 1 if results else (2 if unread else 0)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
