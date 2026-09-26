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

# The per-app transports.
#
# ── THE COMMENT HERE SAID "DERIVED FROM A GREP" AND THE LIST WAS NOT DERIVED,
# ── AND IT WENT STALE BY SEVEN NAMES AND 58 WRITE SITES (fixed 2026-09-25) ──
# It read: *"Derived from a grep of every app HTML rather than remembered -- a
# transport missing from this list is a whole app scoring zero, which is the
# silent-pass shape this tool is about."* That sentence describes how the list
# was FIRST WRITTEN, not a mechanism, and there was no mechanism. Measured:
#
#   scpData        22 writes   sairnscape.html
#   sdData         17 writes   stonedesk.html          <- the platform's largest app
#   bldData         9 writes   sairnbuild.html
#   subxCall        4 writes   stonedesk.html          (api/sd-sub-data)
#   mechData        3 writes   sairnmechanical.html
#   hrCall          2 writes   stonedesk-hr.html       <- THE WHOLE FILE scored zero
#   sbBackupFetch   1 write    sairnbiz.html
#
# 58 write sites invisible against a denominator of 294 -- so every figure this
# tool printed was computed over 83% of the population while reading as complete,
# and `stonedesk-hr.html` was the exact failure the old comment names: a file
# with no known transport produces no rows, and a file with no rows is skipped by
# `if not n: continue`, so it never appeared in the output at all. An app absent
# from a report is indistinguishable from an app with nothing to report.
#
# TWO OF THE SEVEN CARRIED REAL DISCARDED WRITES. See the run output.
#
# IT IS A LIST PLUS A CONTROL, NOT A DERIVATION (and that is deliberate). A fully
# derived list would silently absorb any local helper that happens to take
# `'write'` as its first argument, moving the denominator with nothing saying so
# -- the same class one step along. So the list stays explicit and reviewable,
# and `unknown_transports()` below runs on EVERY invocation: a `foo('write', ...)`
# callee that is in neither list is reported as a third state and makes the exit
# code non-zero. A new transport can no longer arrive unnoticed, and a
# non-transport cannot enter without somebody naming it.
TRANSPORTS = ('sdnData', 'grdData', 'svData', 'scData', 'senData', 'alfData',
              'rfDataRaw', 'sbData', 'dntData', 'sfData', 'legData',
              # Added 2026-09-25. Every one confirmed to be a real per-app server
              # transport by reading its body: each POSTs to an /api/ endpoint and
              # each returns something falsy when the write did not land, which is
              # the property this tool's whole verdict rests on.
              'scpData', 'sdData', 'bldData', 'mechData', 'subxCall', 'hrCall',
              'sbBackupFetch')

# Callees that take a literal 'write' and are NOT server transports.
# AN ENTRY HERE NEEDS A SENTENCE, because excluding a real transport is how a
# whole app scores zero -- which is the defect this dict exists to stop being
# repeatable, not a convenience.
NOT_A_TRANSPORT = {
    # A CONSOLE LOGGER, not a transport. `sdDataFailed(action, resource, why)` is
    # stonedesk.html's own reporter for a write that did NOT reach the server, so
    # its first argument is the literal 'write' and it matches. It sends nothing.
    # Caught by unknown_transports() on the FIRST run after that control was
    # added -- against code written minutes earlier in the same session, which is
    # the control doing exactly what it is for on the smallest possible sample.
    'sdDataFailed': 'the console reporter for a failed write, not a transport',
}

# Any `name('write'` callee, so a transport nobody added can be reported.
ANY_WRITE_CALLEE = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(\s*'write'")

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
    # ── THE NAIVE SPLIT WAS THE ONE THAT FAILED OPEN (fixed 2026-09-25) ──────
    # This read `lines[j].split('//')[0]`, which is the exact thing the
    # strip_line_comment docstring further down says not to do -- and HERE the
    # consequence is the worse direction. A previous line carrying a `//` inside
    # a STRING, e.g. `var u = 'http://x';`, truncates to `var u = 'http:` which
    # ends in `:` -- one of OPENS -- so this returned True and the call below was
    # scored READ. A false PASS, on the function whose whole job is to stop false
    # findings. Routed through the quote-aware stripper, which is in this same
    # file and was written for precisely this.
    for j in range(i - 1, max(-1, i - 4), -1):
        t = strip_line_comment(lines[j]).rstrip()
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
    # ── A BLOCK OPENER IS NOT A CONSUMER EITHER (2026-09-25) ────────────────
    # `if (c && c.id) { try { sdData('write','sd_customers',c); } catch (e) {} }`
    # scored UNREADABLE, and a permanent could-not-tell on a real discarded write
    # is the weakest of the three answers this tool can give. The prefix ends in
    # `{`, so the call is the FIRST STATEMENT OF A BLOCK -- which is exactly a
    # bare statement, one nesting level in.
    #
    # `{` CAN ALSO OPEN AN OBJECT LITERAL, and that case is already handled
    # without needing to distinguish it: `{ foo: sdData(...) }` puts a `:` at the
    # end of the prefix and BOUND matches it first. A `{` IMMEDIATELY before a
    # call, with nothing between, can only be a block.
    #
    # STATEMENT POSITION IS THE TEST, NOT AN EMPTY PREFIX. The first attempt at
    # this fix tried to STRIP the prefix down to nothing and could not: stripping
    # the `{` off `if (c && c.id) { try {` leaves `try`, then `if (c && c.id)`,
    # and each strip needs another rule. What actually matters is one character.
    # A call whose prefix's last non-space character is `{`, `;` or `}` is at the
    # start of a statement -- a block was just opened, a statement just ended, or
    # a block just closed -- and there is nothing there to receive a result. It is
    # the same fact as an empty prefix, one nesting level in.
    #
    # `await` is re-stripped after that character, because `try{ await x(...)`
    # carries two constructs on one prefix.
    if re.match(r'^[{;}]$', p[-1:]):
        p = ''
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


# ── THE BENIGN TEST MATCHED A SUBSTRING OF THE WHOLE CALL (fixed 2026-09-25) ──
# It was `any(("'" + b + "'") in call for b in BENIGN_RESOURCES)`, so a benign
# resource NAME appearing anywhere inside the call text -- in the payload, in a
# nested string, in a field value -- silenced a real discarded write on a
# DIFFERENT resource. `sdData('write','sd_customers',{tag:'shared_knowledge'})`
# would have been filed as fire-and-forget-on-purpose.
#
# Zero live instances today, which is why this is a residue rather than a defect
# record. It is fixed because the whole point of the BENIGN list is that it is a
# NARROW, named exemption, and an exemption that can be triggered by an unrelated
# string is not narrow -- it is the widest possible match wearing a short list.
RESOURCE_ARG = re.compile(r"\(\s*'write'\s*,\s*'([^']*)'")


def resource_arg(call):
    """The resource the call actually names -- its SECOND argument, not any
    string inside it. Returns '' when the second argument is not a literal
    (a variable, a template, a concatenation), which can never equal a name in
    BENIGN_RESOURCES, so an unparseable resource stays a finding rather than
    becoming an exemption."""
    m = RESOURCE_ARG.search(call)
    return m.group(1) if m else ''


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


def unknown_transports(path):
    """Callees taking a literal 'write' that are in NEITHER list.

    THIS IS THE CONTROL ON THE LIST ABOVE, and it is what makes the list safe to
    keep by hand. Comments are stripped the same way the scanner strips them, so
    a comment quoting a removed call cannot invent a transport -- the fifth
    false-positive class recorded further down this file, arriving here for free
    rather than a sixth time.
    """
    src = io.open(path, encoding='utf-8', errors='replace').read()
    seen = {}
    for raw in src.split('\n'):
        ln = strip_line_comment(raw)
        if "'write'" not in ln:
            continue
        for m in ANY_WRITE_CALLEE.finditer(ln):
            name = m.group(1)
            if name in TRANSPORTS or name in NOT_A_TRANSPORT:
                continue
            seen[name] = seen.get(name, 0) + 1
    return seen


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
            if resource_arg(m.group('call')) in BENIGN_RESOURCES:
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
    unknown = {}
    for t in targets:
        path = t if os.path.isabs(t) else os.path.join(REPO, t)
        if not os.path.isfile(path):
            print('COULD NOT RUN: %s does not exist. Naming a file that is not '
                  'there is not a clean scan.' % t)
            return 2
        for name, cnt in unknown_transports(path).items():
            unknown.setdefault(name, {})[os.path.basename(path)] = cnt
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
    if unknown:
        print()
        print('TRANSPORT NOT IN THE LIST -- %d callee(s). THESE WRITE SITES WERE NOT'
              % len(unknown))
        print('SCANNED AT ALL, so every figure above is over a SMALLER population than')
        print('the codebase has. This is the defect that made the list stale by seven')
        print('names and 58 write sites until 2026-09-25; it is a third state now.')
        for name in sorted(unknown, key=lambda k: -sum(unknown[k].values())):
            print('   %-16s %3d write(s)   %s'
                  % (name, sum(unknown[name].values()),
                     ', '.join('%s:%d' % kv for kv in sorted(unknown[name].items()))))
        print('   Add a real transport to TRANSPORTS, or name it in NOT_A_TRANSPORT')
        print('   with a sentence. Do not leave it here.')

    print()
    print('A RETURNED write is NOT a pass for the feature -- it moves the decision to')
    print('the caller, and this tool does not follow callers. A READ write is not a')
    print('pass either: binding a result and never testing it scores READ here and is')
    print('the next shape along. Neither is folded into a claim this cannot support.')
    # ── "N UNREADABLE, NO DISCARDS" USED TO EXIT 0 (fixed 2026-09-25) ────────
    # The line was `return 1 if total_d else 0`, so a run that could not classify
    # a single write site -- or could not classify forty -- reported SUCCESS as
    # long as none of the ones it COULD read were discarded. The whole top of
    # this file argues that a could-not-tell is a third state and is never folded
    # into a pass; the exit code, which is the only thing a gate or a CI step
    # reads, folded it into a pass. A caller checking `$? -eq 0` was told this
    # file was clean on evidence it had just printed as unreadable.
    #
    # THREE CODES NOW, and the order matters: a FINDING outranks a
    # could-not-tell, because a confirmed discarded write is worse news than an
    # unread line and must not be downgraded by one arriving beside it.
    #   1  at least one DISCARDED write        -- a finding
    #   2  no findings, but something was not read: an UNREADABLE line or a
    #      transport this tool does not know about -- COULD NOT TELL
    #   0  every write site classified, and none discarded
    if total_d:
        return 1
    if total_u or unknown:
        print()
        print('EXIT 2 -- COULD NOT TELL, NOT A PASS: %d unreadable line(s) and %d '
              'unknown transport(s).' % (total_u, len(unknown)))
        print('No DISCARDED write was found among the sites that could be read. That is')
        print('not the same as none existing, and this exit code is the difference.')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
