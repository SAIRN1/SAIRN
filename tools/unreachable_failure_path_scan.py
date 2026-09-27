#!/usr/bin/env python
"""A FAILURE PATH THE CALLER TESTS FOR AND THE CALLEE CANNOT PRODUCE.

    python tools/unreachable_failure_path_scan.py
    python tools/unreachable_failure_path_scan.py --fixtures   # blind lock only
    python tools/unreachable_failure_path_scan.py sairnvet.html

Exit 0 nothing found, 1 findings, 2 could not run. Three states, never two.

── THE DEFECT THIS EXISTS FOR, WITH ITS NAME AND DATE ──────────────────────
2026-09-26, stonedesk.html. `pcToggleSlab()` has read `ok === false` since the
public catalog shipped, to show *"Saved on this device only -- the catalog on the
web has NOT changed"*:

    var ok = (typeof slabSyncOne === 'function') ? await slabSyncOne(sl) : null;
    ...
    notify(ok === false ? 'Saved on this device only ...' : 'Slab published ...')

and `slabSyncOne()` returned `undefined` on every path -- two bare `return;`
guards and a `try{ await ... }catch(e){}` with no return at all. So `ok === false`
was NEVER true, the warning could not fire, and a failed publish said *"Slab
published to the catalog"*.

**THAT IS WORSE THAN A MISSING WARNING.** A missing warning is a gap somebody can
see. A warning that is present in the source, reviewed, and unreachable reads as
coverage on every future read of that function -- and the reviewer who added the
`ok === false` branch was right to add it. Nothing was wrong with the caller. The
defect is a DISAGREEMENT BETWEEN TWO FUNCTIONS that neither one's own reader can
see, which is precisely the shape no single-file review catches.

── WHY THIS SHAPE AND NOT THE WHOLE FAMILY ────────────────────────────────
The same session caught three defects of one family in one afternoon, and they are
not all mechanically decidable:

  1. THIS ONE -- a tested value the callee cannot return. Decidable: a function
     whose every `return` is bare has exactly one possible result.
  2. A check reading the WRONG FIELD, so both sides of its comparison are the
     same refusal. `load_compliance_seed.py` sent `payload.check` where the
     endpoint requires `payload.requirement_type`, answered 400 before AND after
     a load, and two identical 400s compare equal -- so it printed UNCHANGED on
     every run it had ever made, including the one where the rules landed. NOT in
     scope here: deciding it needs the endpoint's required-field list joined to
     every caller's payload, across files and languages.
  3. A criterion that cannot distinguish its two cases -- "the answer must have
     CHANGED" conflating *nothing loaded* with *already loaded* on an upserting
     endpoint. NOT in scope: that is a judgement about what a comparison means.

Scoping to (1) is deliberate. A scan that reported all three at this confidence
would be a scan nobody could act on, and the two out of scope are named here so
the gap is a decision rather than an omission.

── WHAT MAKES A FINDING, AND THE TWO CONFIDENCES ARE NOT MERGED ────────────
A function is BARE when it contains at least one `return` and every one of them
is `return;` -- or contains no `return` at all. Its only possible value is
`undefined`. (An `async` bare function resolves to `undefined`, which is what an
`await`ing caller sees; that is the same answer and is why async is not a
special case.)

  CONFIRMED  a caller compares that function's result -- directly, or through a
             variable assigned from it -- against a literal that is not
             `undefined`. The branch cannot be taken. This is the pcToggleSlab
             shape and it is a defect in the pair, not in either half.
  ADVISORY   a caller BINDS the result and never tests it. That is the
             next-shape-along `tools/sync_write_result_check.py` already names
             and is reported separately, never added to the confirmed count.

`!x` and truthiness are DELIBERATELY NOT CONFIRMED. `!undefined` is true, so a
caller writing `if (!f())` gets a branch that fires every time -- which may be
exactly what a guard wants. Reporting it as unreachable would be the wrong
direction, and reporting it as fine would miss a real case; so it is neither, and
this paragraph is the record of that call.

── AND THE LIMIT, STATED RATHER THAN DISCOVERED LATER ──────────────────────
This is a REGEX-AND-BRACE-MATCHING scan, not a parser. It cannot see a value
returned by mutating an argument, a function whose result comes from a wrapper it
does not resolve, or a caller in a different file when scanning one file. Every
finding is a pair of line numbers a person reads. It is REPORT-ONLY and is not a
gate: a false positive that blocked a push would get the scan disabled, and then
it protects nothing.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
# ── IT USES THE ONE STRIPPER, AND FAILS CLOSED WITHOUT IT ──────────────────
# jscomments.py is "the ONE comment stripper every SAIRN scanner should use",
# and its own header records why: a naive stripper reading 10% of a file and
# reporting CLEAN is not a weak check, it is a false one. A hand-rolled fallback
# here would be the eighth implementation and would reproduce the defect the
# file exists to end -- so there is no fallback. PR 1.11: a check that depends
# on another tool must fail CLOSED when it is absent, naming the tool.
try:
    import jscomments
except Exception as _e:                                      # noqa: BLE001
    sys.stderr.write('COULD NOT RUN: tools/jscomments.py could not be imported '
                     '(%s). Nothing was scanned. This scan does NOT carry its '
                     'own stripper: an eighth hand-rolled one is the defect '
                     'that file exists to end, and the first draft of THIS file '
                     'proved it -- its fallback treated the `//` in a URL as a '
                     'comment and called a function with two real `return` '
                     'statements bare.\n' % _e)
    sys.exit(2)

EXIT_OK, EXIT_FINDINGS, EXIT_COULD_NOT_RUN = 0, 1, 2

# The literals a caller compares against. `undefined` is excluded ON PURPOSE --
# comparing against undefined is the correct way to test a bare function.
TESTED_LITERALS = ('false', 'true', 'null', '0', "''", '""')

DEF_PATTERNS = (
    re.compile(r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('),
    re.compile(r'\bwindow\.([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\('),
    re.compile(r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\('),
)


class CouldNotRun(Exception):
    pass


def strip_comments(src):
    """Comments out, LENGTH PRESERVED, so every line number this reports is the
    line number in the real file. Delegated to jscomments.strip_comments, which
    already survives `accept="image/*"`, a URL containing `//` and a regex
    literal holding a quote -- the three shapes that destroyed the seven
    hand-rolled strippers its own header measures."""
    out = jscomments.strip_comments(src)
    if not isinstance(out, str) or len(out) != len(src):
        raise CouldNotRun('jscomments.strip_comments did not preserve length '
                          '(%d in, %s out), so every line number this would '
                          'report is shifted. Refusing rather than reporting '
                          'positions a reader cannot find.'
                          % (len(src), len(out) if isinstance(out, str) else type(out)))
    return out


def body_of(src, open_paren_end):
    """From just after a definition's `(`, find the body braces. -> (start, end)
    of the body INCLUDING its braces, or None."""
    i, depth = open_paren_end, 1
    while i < len(src) and depth:
        if src[i] == '(':
            depth += 1
        elif src[i] == ')':
            depth -= 1
        i += 1
    while i < len(src) and src[i] not in '{;':
        i += 1
    if i >= len(src) or src[i] != '{':
        return None
    start, depth = i, 0
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return (start, i + 1)
        i += 1
    return None


RETURN_RE = re.compile(r'\breturn\b([^\n;}]*)')
# Indexed once per file, keyed by the CALLEE name -- see the note in scan_text.
DIRECT_CALL_RE = re.compile(
    r'\b([A-Za-z_$][\w$]*)\s*\([^()\n]{0,200}\)\s*(?:===|!==|==|!=)\s*'
    r'([A-Za-z0-9_$\'"]+)')
BOUND_CALL_RE = re.compile(
    r'\b(?:var|let|const)?\s*([A-Za-z_$][\w$]*)\s*=\s*'
    r'(?:await\s+)?(?:\([^()\n]{0,80}\)\s*\?\s*(?:await\s+)?)?'
    r'([A-Za-z_$][\w$]*)\s*\(')
NESTED_FN_RE = re.compile(r'\bfunction\s*[\w$]*\s*\(|=>')


def classify(body):
    """-> 'bare' | 'values' | 'nested-only'.

    `bare` is the finding-eligible class: at least one `return` and every one of
    them returns nothing -- or no `return` at all.

    A `return <value>` that belongs to a NESTED function or arrow is not this
    function's return, and counting one would hide the defect: `slabSyncOne`'s
    own `.forEach(function(){ return x; })` would make it look value-returning.
    Nested bodies are removed before the returns are read.
    """
    inner = body
    # blank out nested function/arrow bodies, innermost first
    for _ in range(40):
        m = NESTED_FN_RE.search(inner)
        if not m:
            break
        # ── AN EXPRESSION-BODIED ARROW HAS NO BODY TO SKIP (fixed 2026-09-26) ──
        # `dcPoly.map(p => p.x)` has no braces, so "find the next `{`" found the
        # object literal in the function's OWN `return { x:..., y:... }` two lines
        # later and blanked it -- and the function then read as bare. All five
        # advisory findings in this scan's first real run were that, and every
        # one of them was a FALSE POSITIVE. An expression-bodied arrow cannot
        # contain a `return` statement at all, so neutralising the `=>` token is
        # both sufficient and the only safe edit.
        tail = inner[m.end():]
        braced = tail.lstrip()[:1] == '{' if m.group(0) == '=>' else True
        if not braced:
            inner = (inner[:m.start()] + '0'
                     + ' ' * (m.end() - m.start() - 1) + inner[m.end():])
            continue
        j = inner.find('{', m.end())
        if j < 0:
            inner = (inner[:m.start()] + '0' + ' ' * (m.end() - m.start() - 1)
                     + inner[m.end():])
            continue
        depth, k = 0, j
        while k < len(inner):
            if inner[k] == '{':
                depth += 1
            elif inner[k] == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        # A PLACEHOLDER, NOT BLANKS, and the first draft got this wrong.
        # Blanking `return function(t){...}` left a bare `return` behind, so
        # every function that RETURNS A FUNCTION read as bare --
        # sairnbuild's computeTaskDates() was reported on exactly that. The
        # nested body becomes `0`, which is a value, so the outer return still
        # reads as one. Length preserved either way.
        inner = (inner[:m.start()] + '0' + ' ' * (k - m.start())
                 + inner[k + 1:])
    rets = RETURN_RE.findall(inner)
    if not rets:
        return 'bare'
    return 'bare' if all(not r.strip() for r in rets) else 'values'


def line_of(src, pos):
    return src.count('\n', 0, pos) + 1


def scan_text(src, label):
    """-> (confirmed, advisory). Each item is a dict a person can read."""
    clean = strip_comments(src)
    bare = {}
    for pat in DEF_PATTERNS:
        for m in pat.finditer(clean):
            name = m.group(1)
            b = body_of(clean, m.end())
            if not b:
                continue
            # A name defined twice: the LAST definition wins at runtime, which is
            # a real hazard this repo has already recorded (three renderCustomers
            # in one file). Keep the last, and remember that it was redefined.
            kind = classify(clean[b[0]:b[1]])
            prev = bare.get(name)
            bare[name] = {'line': line_of(clean, m.start()), 'kind': kind,
                          'redefined': bool(prev)}
    # ── THE CALL SITES ARE INDEXED ONCE, NOT SEARCHED PER NAME (2026-09-26) ──
    # The first version ran two full-file regex passes for EACH bare function.
    # stonedesk.html has 1,133 of them, so that was 2,266 scans of 2.7MB, and the
    # probe driving this on the real file timed out at ten minutes. Two passes
    # total now, keyed by callee name -- same findings, and a scan nobody will
    # wait for is a scan nobody runs.
    direct_idx, bound_idx = {}, {}
    for m in DIRECT_CALL_RE.finditer(clean):
        if m.group(2) in TESTED_LITERALS:
            direct_idx.setdefault(m.group(1), []).append(
                (m.start(), m.group(0), m.group(2)))
    for m in BOUND_CALL_RE.finditer(clean):
        bound_idx.setdefault(m.group(2), []).append(
            (m.start(), m.end(), m.group(1)))

    confirmed, advisory, skipped_redefined = [], [], []
    for name, info in sorted(bare.items()):
        if info['kind'] != 'bare':
            continue
        # ── A REDEFINED NAME IS SKIPPED, NOT GUESSED (2026-09-26) ───────────
        # stonedesk.html defines `render` 23 times in 23 unrelated IIFEs. The
        # last definition wins at runtime, so matching a caller at :30570 to a
        # definition at :38046 is arithmetic, not analysis -- and it produced two
        # of the five false positives in this scan's first real run. A scan that
        # cannot tell which definition a caller reaches has to SAY that, not
        # pick. Reported as a named limit below rather than dropped silently.
        if info['redefined']:
            skipped_redefined.append((name, info['line']))
            continue
        # DIRECT: f(...) === false
        for pos, op, lit in direct_idx.get(name, ()):
            confirmed.append({
                'file': label, 'fn': name, 'fn_line': info['line'],
                'test_line': line_of(clean, pos),
                'how': 'the call is compared directly against %s' % lit,
                'redefined': info['redefined']})
        # THROUGH A VARIABLE: v = [await] f(...) ; ... v === false
        for pos, endpos, var in bound_idx.get(name, ()):
            window = clean[endpos:endpos + 1400]
            t = re.search(r'\b' + re.escape(var) + r'\s*(===|!==|==|!=)\s*([A-Za-z0-9_$\'"]+)',
                          window)
            if t and t.group(2) in TESTED_LITERALS:
                confirmed.append({
                    'file': label, 'fn': name, 'fn_line': info['line'],
                    'test_line': line_of(clean, endpos + t.start()),
                    'how': 'bound to `%s`, then compared against %s' % (var, t.group(2)),
                    'redefined': info['redefined']})
            elif t is None:
                advisory.append({
                    'file': label, 'fn': name, 'fn_line': info['line'],
                    'test_line': line_of(clean, pos),
                    'how': 'bound to `%s` and never tested' % var,
                    'redefined': info['redefined']})
    # A pair can be reported twice when a caller both binds and compares. Dedupe
    # on (fn, test_line) -- the same two lines are one finding to a reader.
    seen, out = set(), []
    for f in confirmed:
        k = (f['fn'], f['test_line'])
        if k not in seen:
            seen.add(k); out.append(f)
    seen2, out2 = set(), []
    for f in advisory:
        k = (f['fn'], f['test_line'])
        if k not in seen2 and k not in seen:
            seen2.add(k); out2.append(f)
    return out, out2, skipped_redefined


# ── THE BLIND LOCK (discipline 1): fixtures judged before anything real ─────
def fixtures():
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '\n         ' + str(detail)[:300]))
        if not cond:
            bad += 1

    # THE REAL DEFECT, REDUCED. Both halves are correct on their own.
    DEFECT = """
async function slabSyncOne(slab){
  if(typeof sdData!=='function') return;
  var lic=slabLicKey(); if(!lic) return;
  try{ await sdData('write','slabs',slab); }catch(e){}
}
window.pcToggleSlab=async function(slabId,on){
  var ok=(typeof slabSyncOne==='function') ? await slabSyncOne(sl) : null;
  notify(ok===false ? 'NOT changed on the web' : 'published', ok===false?'err':'ok');
};
"""
    c, a, _sk = scan_text(DEFECT, 'fixture')
    ck('THE ARM THAT MATTERS: the real pcToggleSlab/slabSyncOne pair is CONFIRMED',
       any(f['fn'] == 'slabSyncOne' for f in c), (c, a))

    # THE FIX. Same caller, and the callee can now answer false.
    FIXED = """
async function slabSyncOne(slab){
  if(typeof sdData!=='function') return false;
  var lic=slabLicKey(); if(!lic) return false;
  try{ var saved=await sdData('write','slabs',slab); if(saved!==null) return true; return false; }
  catch(e){ return false; }
}
window.pcToggleSlab=async function(slabId,on){
  var ok=await slabSyncOne(sl);
  notify(ok===false ? 'NOT changed on the web' : 'published');
};
"""
    c2, _, _x = scan_text(FIXED, 'fixture')
    ck('...and the FIXED pair is not reported -- the other direction, without '
       'which this scan would flag every boolean-returning function',
       not any(f['fn'] == 'slabSyncOne' for f in c2), c2)

    # A NESTED return must not make the outer function look value-returning.
    NESTED = """
function outer(){
  [1,2].forEach(function(x){ return x; });
  return;
}
var r = outer(); if (r === false) {}
"""
    c3, _, _x = scan_text(NESTED, 'fixture')
    ck('a `return` inside a NESTED function does not count as the outer '
       'function\'s -- counting one would hide the real defect',
       any(f['fn'] == 'outer' for f in c3), c3)

    # Truthiness is NOT confirmed, by decision. `!undefined` is true.
    TRUTHY = """
function g(){ return; }
if (!g()) { doThing(); }
"""
    c4, _, _x = scan_text(TRUTHY, 'fixture')
    ck('`!f()` is NOT reported as unreachable -- !undefined is true, so that '
       'branch fires every time, which may be what the guard wants',
       not c4, c4)

    # A comparison against undefined is the CORRECT test and must not be flagged.
    CORRECT = """
function h(){ return; }
var v = h(); if (v === undefined) { fine(); }
"""
    c5, a5, _x = scan_text(CORRECT, 'fixture')
    ck('comparing against `undefined` is the correct way to test a bare '
       'function and is not a finding', not c5, c5)

    # The advisory half: bound and never tested. Counted separately.
    BOUND = """
function k(){ return; }
function caller(){ var z = k(); other(); }
"""
    _, a6, _x = scan_text(BOUND, 'fixture')
    ck('a result BOUND and never tested is ADVISORY, not confirmed -- a '
       'different finding with a different fix',
       any(f['fn'] == 'k' for f in a6), a6)

    # A comment must not create a finding, and line numbers must not shift.
    COMMENTED = """
function m(){ return; }
// var q = m(); if (q === false) {}
var real = 1;
"""
    c7, a7, _x = scan_text(COMMENTED, 'fixture')
    ck('a call inside a COMMENT is not a finding -- and the strip preserves '
       'length, so reported lines are real lines', not c7 and not a7, (c7, a7))

    return out, bad


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('BLIND LOCK -- criteria judged against fixtures, nothing real')
        for l in lines:
            print(l)
        print('\n%d fixture arm(s) failed' % bad)
        return EXIT_FINDINGS if bad else EXIT_OK

    lines, bad = fixtures()
    if bad:
        sys.stderr.write('COULD NOT RUN: %d of this scan\'s own fixture arms '
                         'FAIL, so nothing real was judged. A scan whose '
                         'criteria are broken reports about itself.\n' % bad)
        for l in lines:
            sys.stderr.write(l + '\n')
        return EXIT_COULD_NOT_RUN

    targets = [a for a in argv if not a.startswith('--')]
    if not targets:
        targets = sorted(f for f in os.listdir(REPO) if f.endswith('.html'))
        targets += [os.path.join('api', '_lib', f)
                    for f in sorted(os.listdir(os.path.join(REPO, 'api', '_lib')))
                    if f.endswith('.js') and not f.endswith('.test.js')]
    if not targets:
        sys.stderr.write('COULD NOT RUN: no files to scan.\n')
        return EXIT_COULD_NOT_RUN

    allc, alla, allsk, scanned = [], [], [], 0
    for rel in targets:
        p = os.path.join(REPO, rel)
        if not os.path.isfile(p):
            print('  skipped (absent) %s' % rel)
            continue
        src = io.open(p, encoding='utf-8', errors='replace').read()
        c, a, sk = scan_text(src, rel)
        allc.extend(c); alla.extend(a); scanned += 1
        allsk.extend((rel, n, l) for n, l in sk)

    print('UNREACHABLE FAILURE PATH -- a value the caller tests for and the '
          'callee cannot return')
    print('  files scanned                 %4d' % scanned)
    print('  CONFIRMED unreachable         %4d' % len(allc))
    print('  advisory (bound, not tested)  %4d   <- a different finding, counted '
          'separately' % len(alla))
    for f in allc:
        print('  CONFIRMED  %s' % f['file'])
        print('      %s() is BARE at :%d -- every return is bare, so its only '
              'value is undefined%s'
              % (f['fn'], f['fn_line'],
                 '  [NAME REDEFINED IN THIS FILE -- the last definition wins at '
                 'runtime, so check which one the caller reaches]'
                 if f['redefined'] else ''))
        print('      :%d %s -- that branch CANNOT be taken' % (f['test_line'], f['how']))
    if alla:
        print('\n  ADVISORY, and NOT folded into the count above:')
        for f in alla[:40]:
            print('    %-26s %s() bare at :%d, %s at :%d'
                  % (f['file'], f['fn'], f['fn_line'], f['how'], f['test_line']))
        if len(alla) > 40:
            print('    ... and %d more' % (len(alla) - 40))
    if allsk:
        # NAMED, NOT SILENT. These are bare functions whose name is defined more
        # than once in their file, so which definition a caller reaches cannot be
        # told from position -- the scan refuses rather than guessing, and a
        # refusal nobody is shown is the same as not having looked.
        print('\n  NOT JUDGED -- %d bare function(s) whose NAME IS DEFINED MORE '
              'THAN ONCE in their file, so which definition a caller reaches '
              'cannot be told from position. Refused, not guessed:' % len(allsk))
        for rel, name, line in allsk[:25]:
            print('    %-26s %s() at :%d' % (rel, name, line))
        if len(allsk) > 25:
            print('    ... and %d more' % (len(allsk) - 25))
    print('\nREPORT ONLY, and not a gate by decision: this is brace matching, '
          'not a parser.')
    print('Every finding is a PAIR OF LINES a person reads. It cannot see a value '
          'returned by mutating an argument, or a caller in another file.')
    return EXIT_FINDINGS if allc else EXIT_OK


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
