"""tools/sync_write_result_check.py -- find SERVER WRITES whose result is thrown away.

    python tools/sync_write_result_check.py            # every app HTML
    python tools/sync_write_result_check.py sairnlegacy.html

── WHAT THIS IS, AND WHAT IT IS NOT ──────────────────────────────────────
Every SAIRN app pushes a record to the server through a per-app transport --
`sdnData('write', ...)`, `grdData('write', ...)`, `svData`, `scData`, `senData`,
`alfData`, `rfDataRaw`. Every one of them returns something falsy when the write
did NOT land. The failure is already computed and already correct.

THIS FINDS THE CALL SITES THAT NEVER LOOK. A write that is fired and forgotten
is indistinguishable from one that succeeded: the local copy is already saved,
the panel already re-rendered, and the toast -- if there is one -- says the
record was saved. It was, on one device. Nothing else will ever see it.

It is NOT `discarded_verdict_check.py`. That one finds a REFUSAL that is
computed and ignored -- a gate that says no and is not consulted. This finds a
WRITE that failed and is not consulted. Different direction, different fix: a
discarded refusal lets something through, a discarded write result loses data
quietly and tells the user it is safe.

── HOW IT DECIDES, AND WHERE IT REFUSES TO GUESS ─────────────────────────
For each transport call with the literal action 'write', the line is classified:

  READ       the result is bound (`var x = await ...`) or consumed inline
             (`.then(`, `if (await ...)`, passed to something). PASS.
  RETURNED   the call is the function's own `return`, so the DECISION is the
             caller's. PASS here, and the caller is a separate question this
             tool does not follow -- said in the output rather than implied.
  DISCARDED  the statement is the bare call, awaited or not, with nothing
             bound and nothing chained. FINDING.

  UNREADABLE the line does not parse into any of the three. Reported as a
             THIRD STATE and counted apart. A could-not-tell is never folded
             into a pass -- that rule is the reason this file exists at all.

A DISCARDED write is reported with its nearest enclosing toast, when there is
one, because "saved" printed next to a discarded write result is the harm, and a
discarded write with no claim attached is a smaller thing than one that lies.

── WHAT IT CANNOT SEE ────────────────────────────────────────────────────
Whether the caller of a RETURNED write reads it. Whether a READ result is read
CORRECTLY -- binding a variable and never testing it passes here and is the next
shape along. And anything built by string concatenation rather than written as a
call. Stated rather than left for a reader to assume the number is complete.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The per-app transports. Derived from a grep of every app HTML rather than
# remembered -- a transport missing from this list is a whole app scoring zero,
# which is the silent-pass shape this tool is about.
TRANSPORTS = ('sdnData', 'grdData', 'svData', 'scData', 'senData', 'alfData',
              'rfDataRaw', 'sbData', 'dntData', 'sfData', 'legData')

CALL = re.compile(
    r"(?P<prefix>[^\n]*?)(?P<call>(?:" + '|'.join(TRANSPORTS) + r")\s*\(\s*'write'[^\n]*)")

# A result is CONSUMED when the call is bound, awaited into something, chained,
# or handed on. Deliberately generous: a false PASS here costs a missed finding,
# and every finding this tool reports has to survive a human read anyway.
# `[` is in this set because an ARRAY ELEMENT is consumed by whatever consumes
# the array. Omitting it reported the three writes inside SAIRNgrounds'
# `Promise.all([...])` as discarded when the very next line filters on
# `!results[i]` and names which record failed to sync -- three false
# positives on code that is not merely correct but unusually careful.
BOUND = re.compile(r"(?:=\s*|return\s+|\(\s*|\[\s*|,\s*|&&\s*|\|\|\s*|\?\s*|:\s*)$")

# ── A DELIBERATELY FIRE-AND-FORGET RESOURCE IS NOT A FINDING, AND IS NOT
# ── HIDDEN EITHER ───────────────────────────────────────────────────────
# `shared_knowledge` is the platform's AI context sink: six apps push word
# lists to it and none reads the result, on purpose -- losing one carries no
# record and no claim, and there is no toast to be wrong. Counting it as a
# defect would put six permanent findings in front of every future reader,
# which is how a report stops being read.
#
# It is COUNTED AND PRINTED under its own heading rather than filtered out.
# A tool that silently drops a class is making a judgement the reader cannot
# see; this one makes the same judgement visibly.
BENIGN_RESOURCES = ('shared_knowledge',)


# A CALL CAN BE A CONTINUATION OF A CONSTRUCT THAT OPENED ON AN EARLIER LINE,
# and the first version could not see that either. SAIRNgrounds' DreamClose
# writes sit inside `var results=await Promise.all([` with the array opening on
# the line ABOVE, so their own line has nothing but indentation in front of
# them and they scored DISCARDED -- while the next line filters `!results[i]`
# and names which record failed to sync. Three false positives on unusually
# careful code, for the second time in this file, from the same root cause:
# reading a line instead of a construct.
OPENS = ('[', '(', ',', '&&', '||', '?', ':')


def continues_open_construct(lines, i):
    for j in range(i - 1, max(-1, i - 4), -1):
        t = lines[j].split('//')[0].rstrip()
        if not t:
            continue
        return any(t.endswith(o) for o in OPENS)
    return False


def classify(prefix, call, lines=None, i=None):
    # `await` is not a consumer, it is punctuation. The first version of this
    # function did not strip it and scored `var saved=await senData(...)` as
    # UNREADABLE -- 242 of 294 call sites, which is what made the bug obvious:
    # a classifier that cannot read the commonest line in the codebase is not
    # reporting a third state, it is broken. Kept as a comment because the
    # number is what exposed it, not the code.
    p = re.sub(r'\bawait\s*$', '', prefix.rstrip()).rstrip()
    if re.search(r'\breturn$', p):
        return 'RETURNED'
    if BOUND.search(p):
        return 'READ'
    if p == '':
        if '.then(' in call or '.catch(' in call:
            return 'READ'
        if lines is not None and i is not None and continues_open_construct(lines, i):
            return 'READ'
        # A genuinely bare statement: nothing binds it and nothing chains it.
        return 'DISCARDED'
    if '.then(' in call or '.catch(' in call:
        return 'READ'
    return 'UNREADABLE'


TOAST = re.compile(r"\b(?:toast|showToast)\s*\(")


def nearest_claim(lines, i):
    """A success sentence printed near a discarded write is what makes it a lie."""
    for j in range(i, min(i + 6, len(lines))):
        if TOAST.search(lines[j]):
            m = re.search(r"['\"]([^'\"]{4,70})['\"]", lines[j])
            return (m.group(1) if m else lines[j].strip())[:70]
    return None


# ── A CALL IS NOT A LINE, AND THE FIRST VERSION OF THIS TOOL ASSUMED IT WAS ──
# Line-based classification reported 12 phantom findings in sairnroofing.html
# alone: `rfDataRaw('write','rf_proposals',{` opens a multi-line object and the
# `.then(...)` that consumes it sits four lines below. A scanner that stops at
# the newline calls every one of those discarded.
#
# That is the exact failure tools/sairn_dead_button_audit.py records costing 58
# phantom findings on StoneDesk, and the lesson there was the same: a naive
# regex over a construct that spans lines produces confident wrong answers.
#
# So the call is CLOSED first -- read forward counting parentheses until the
# call's own paren balances -- and the tail after it is what decides.
def call_tail(lines, i, start_col):
    depth, seen = 0, False
    for j in range(i, min(i + 40, len(lines))):
        text = lines[j][start_col:] if j == i else lines[j]
        for k, ch in enumerate(text):
            if ch == '(':
                depth += 1
                seen = True
            elif ch == ')':
                depth -= 1
                if seen and depth == 0:
                    rest = text[k + 1:]
                    return rest, j
    return None, None            # never closed inside the window


# ── A CALL INSIDE A COMMENT IS NOT A CALL. FIFTH FALSE-POSITIVE CLASS,
# ── FOUND 2026-09-24 ────────────────────────────────────────────────────────
# Four were already found and fixed: `await` read as a consumer, a `.then()`
# arriving several lines below, an array element inside `Promise.all([`, and a
# bracket opened on an earlier line. This is the fifth, and unlike the others it
# leaves a PERMANENT mark rather than one wrong verdict.
#
# THREE LINES, ALL PROSE, ALL COUNTED AS WRITES:
#   sairndental.html:5264   // sdnData('write','dnt_complaints',...). All real
#   sairndesign.html:2394   // Was sdnData('write','specitems_bulk',{...}) -- a
#   sairngrounds.html:1683  // grdData('write', ...)` followed by a toast
#
# Every one is a comment EXPLAINING a write, and two explain a write that was
# deliberately REMOVED. They were reported as COULD NOT TELL, which is the right
# answer to the wrong question: there is nothing to tell, because there is no
# call.
#
# IT COSTS IN THREE DIRECTIONS AND THE THIRD IS THE WORST:
#   * the write COUNT is the denominator of every figure this tool prints, and
#     it was over by three;
#   * three could-not-tells sat permanently unresolvable, and a third-state
#     column that can never reach zero is one people stop reading -- the same
#     "a disclosure that is always on stops being read" failure this codebase
#     already names elsewhere;
#   * a comment quoting a call it REMOVED would be reported forever, so the
#     honest act of writing down what you took out makes this tool noisier. A
#     checker that penalises good documentation is one people route around.
#
# AND THIS CODEBASE HAS PAID FOR THIS EXACT CLASS BEFORE.
# tools/sairn_dead_button_audit.py records 58 phantom findings on StoneDesk from
# scanning comments, and its fix was to strip them with a real state machine
# rather than a regex. That lesson was written down and had not reached here.
#
# QUOTE-AWARE, NOT `split('//')[0]`. A naive split truncates
# `scData('write','x',{url:'http://a'})` at the URL and LOSES a real call --
# trading three false positives for a false negative, which is the worse trade.
# One helper further up this file still does the naive thing on a narrower
# input; this is the correct version and both behaviours are pinned by fixtures.
def strip_line_comment(line):
    """`line` with any `//` comment removed, ignoring `//` inside strings."""
    q = None
    i = 0
    while i < len(line):
        c = line[i]
        p = line[i - 1] if i else ''
        if q:
            if c == q and p != chr(92):
                q = None
        elif c in ('"', "'", '`'):
            q = c
        elif c == '/' and line[i + 1:i + 2] == '/':
            return line[:i]
        i += 1
    return line


def scan(path):
    src = io.open(path, encoding='utf-8', errors='replace').read()
    lines = src.split('\n')
    out = {'READ': 0, 'RETURNED': 0, 'DISCARDED': [], 'UNREADABLE': [], 'BENIGN': []}
    for i, raw in enumerate(lines):
        ln = strip_line_comment(raw)
        if "'write'" not in ln:
            continue
        m = CALL.search(ln)
        if not m:
            continue
        tail, endline = call_tail(lines, i, m.start('call'))
        if tail is None:
            out['UNREADABLE'].append(
                (i + 1, ln.strip()[:100] + '   [call does not close within 40 lines]'))
            continue
        verdict = classify(m.group('prefix'), m.group('call') + tail, lines, i)
        if verdict in ('READ', 'RETURNED'):
            out[verdict] += 1
        elif verdict == 'DISCARDED':
            if any(("'" + b + "'") in m.group('call') for b in BENIGN_RESOURCES):
                out['BENIGN'].append((i + 1, ln.strip()[:100]))
            else:
                out['DISCARDED'].append((i + 1, ln.strip()[:100], nearest_claim(lines, i)))
        else:
            out['UNREADABLE'].append((i + 1, ln.strip()[:100]))
    return out


def main(argv):
    targets = [a for a in argv[1:] if not a.startswith('-')]
    if not targets:
        targets = sorted(f for f in os.listdir(REPO) if f.endswith('.html'))
    total_d = total_u = total_ok = total_b = 0
    for t in targets:
        path = t if os.path.isabs(t) else os.path.join(REPO, t)
        if not os.path.isfile(path):
            print('COULD NOT RUN: %s does not exist. Naming a file that is not '
                  'there is not a clean scan.' % t)
            return 2
        r = scan(path)
        n = (r['READ'] + r['RETURNED'] + len(r['DISCARDED']) + len(r['UNREADABLE'])
             + len(r['BENIGN']))
        if not n:
            continue
        total_ok += r['READ'] + r['RETURNED']
        total_d += len(r['DISCARDED'])
        total_u += len(r['UNREADABLE'])
        total_b += len(r['BENIGN'])
        print('%-22s %3d write(s): %d read, %d returned-to-caller, %d DISCARDED, '
              '%d unreadable, %d benign-sink'
              % (os.path.basename(path), n, r['READ'], r['RETURNED'],
                 len(r['DISCARDED']), len(r['UNREADABLE']), len(r['BENIGN'])))
        for lineno, text in r['BENIGN']:
            print('   benign sink   %s:%d  %s' % (os.path.basename(path), lineno, text))
        for lineno, text, claim in r['DISCARDED']:
            print('   DISCARDED %s:%d' % (os.path.basename(path), lineno))
            print('     %s' % text)
            if claim:
                print('     ...and says: %r' % claim)
        for lineno, text in r['UNREADABLE']:
            print('   COULD NOT TELL %s:%d  %s' % (os.path.basename(path), lineno, text))

    print()
    print('WRITES_CONSUMED:%d' % total_ok)
    print('WRITES_DISCARDED:%d' % total_d)
    print('WRITES_UNREADABLE:%d' % total_u)
    print('WRITES_BENIGN_SINK:%d   (%s -- fire-and-forget on purpose, counted not hidden)'
          % (total_b, ', '.join(BENIGN_RESOURCES)))
    print()
    print('A RETURNED write is NOT a pass for the feature -- it moves the decision to')
    print('the caller, and this tool does not follow callers. A READ write is not a')
    print('pass either: binding a result and never testing it scores READ here and is')
    print('the next shape along. Neither is folded into a claim this cannot support.')
    return 1 if total_d else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
