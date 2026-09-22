r"""The IOLTA reconciler must be CALLED, and the verdict that cannot fail must stay gone.

Run: python tests/law_trust_reconcile_wiring_probe.py

WHY A SECOND PROBE WHEN tests/law_trust_reconcile_probe.py ALREADY EXISTS.
That one drives `api/_lib/law-trust-reconcile.js` and it is thorough. It is
also, by construction, blind to the defect that actually shipped: the engine
was correct, the suite was green, and `sairnlaw.html` NEVER CALLED IT. The only
occurrence of the string `law_trust_reconcile` in the app was a code comment.
A unit test cannot see an absent caller.

This platform has already paid for that exact gap once -- commit 900374e0,
*"--body-file was implemented and never proven WIRED; the probe unit-tested the
helper and could not see the caller"*. This file is the caller half for the
trust reconciler.

WHAT SHIPPED WHILE THE ENGINE SAT UNREACHABLE, because it is the reason this
probe is worth its maintenance. `sairnlaw.html` computed its own verdict:

    ledgerVsClient = round2(ledgerBal) === round2(clientSum)
    ledgerVsBank   = bankBal === null ? null : round2(ledgerBal) === round2(bankBal)
    matches        = ledgerVsClient && (ledgerVsBank === null || ledgerVsBank === true)

`clientSum` partitions the same array `ledgerBal` sums whole -- including the
rows with no client_id, which form their own group and are summed like any
other -- so leg one is a tautology. Leg two is `null` until somebody enters a
bank statement, and `matches` read `null` as agreement. The panel then rendered

    "Reconciled -- all three balances match"

on attorney client trust money: a green three-way verdict from one comparison
that cannot fail and one that was never made. The dashboard suppressed its
Trust Alert on the same value, so the screen said "Nothing needs attention"
precisely when nothing had been checked.

THE ARMS RUN IN BOTH DIRECTIONS. Four of them assert the repair is present;
four MUTATE a copy of the file to put each half of the defect back and assert
this probe goes red. An assertion suite that has never refused anything is one
nobody knows can, and that is the failure this whole subject is about.

COMMENTS ARE STRIPPED BEFORE ANY SEARCH, and that is not tidiness. The defect
state and the repaired state both MENTION `law_trust_reconcile` -- the defect
mentioned it in a comment and nowhere else. A probe that searched raw text
would have passed on the broken file. It is the one thing this probe must get
right, so it is arm 0 and it is driven with a fixture.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.environ.get('SAIRN_LAW_HTML') or os.path.join(REPO, 'sairnlaw.html')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def strip_comments(js):
    """Blank // and /* */ spans, string-aware, preserving length.

    STRING-AWARE MATTERS HERE. This file contains URLs and regexes; a naive
    `//` strip would blank from the middle of `https://` to end of line and
    silently delete real code from the probe's view -- which fails OPEN, the
    one direction a wiring probe must not fail in.
    """
    out = list(js)
    i, n = 0, len(js)
    while i < n:
        c = js[i]
        if c in '\'"`':
            q, i = c, i + 1
            while i < n:
                if js[i] == '\\':
                    i += 2
                    continue
                if js[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == '/' and i + 1 < n and js[i + 1] == '/':
            while i < n and js[i] != '\n':
                out[i] = ' '
                i += 1
            continue
        if c == '/' and i + 1 < n and js[i + 1] == '*':
            j = js.find('*/', i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
            continue
        i += 1
    return ''.join(out)


# ── THE CHECKS, AS FUNCTIONS, SO THE MUTATION ARMS CAN CALL THEM ──────────
# Each returns True when the repaired state is present. The positive arms run
# them on the real file; the negative arms run them on a mutated copy and
# assert False. Sharing one implementation is the point -- a probe whose
# assertion and whose control test different code proves nothing about either.

CALL_RE = re.compile(r"sdnData\s*\(\s*'read'\s*,\s*'law_trust_reconcile'")
TAUTOLOGY_VERDICT = 'all three balances match'


def has_real_call(code):
    """Is law_trust_reconcile CALLED, not merely mentioned? `code` is stripped."""
    return bool(CALL_RE.search(code))


def verdict_string_gone(code):
    """The green three-way sentence must not be RENDERABLE.

    ── THIS ARM SEARCHED RAW TEXT FIRST AND WENT RED ON ITS OWN FIX ────────
    The repair's comment in sairnlaw.html quotes the sentence, in order to say
    what it was and why it is gone. A raw-text search cannot tell a sentence
    the app RENDERS from a sentence a comment CITES, and it flagged the
    explanation as the defect.

    Second instance of that class in one session -- `criticality_tier_check.py`
    refused a register row for quoting the boilerplate it had been rescued
    from, on the same day -- and this repo's standing note says it plainly: a
    comment quoting the old code makes the scanner re-flag the fix.

    So this searches the COMMENT-STRIPPED code. String literals survive
    stripping, so a sentence the app can put on screen is still caught (arm 7
    drives exactly that), while an explanation of it is not. The requirement
    was never "the words must not appear" -- it is "the app must not be able to
    say them".
    """
    return TAUTOLOGY_VERDICT not in code


def tautology_gone(code):
    """No `ledgerVsClient`, and no function named reconcileTrust."""
    return ('ledgerVsClient' not in code
            and not re.search(r'function\s+reconcileTrust\s*\(', code))


def figures_kept(code):
    """THE PAIRED POSITIVE. Deleting the panel entirely would satisfy every
    check above. The figures must still be computed and still be rendered."""
    return (bool(re.search(r'function\s+trustFigures\s*\(', code))
            and code.count('trustFigures(') >= 3
            and "$('tr-ledgerbal')" in code)


def unavailable_is_not_agreement(code):
    """A failed or forbidden call must not reach the agreement branch.

    Anchored on the two things that make that true: the request result is
    checked for `ok` before the status is read, and the explain button is
    offered only on a server DISAGREES.
    """
    return ('if(!v.ok)' in code or 'if (!v.ok)' in code) \
        and "d.status==='DISAGREES'" in code


def read(path):
    raw = io.open(path, encoding='utf-8', errors='replace').read()
    return raw, strip_comments(raw)


print('IOLTA reconciler wiring -- the engine must be CALLED, and the verdict '
      'that cannot fail must stay gone\n')

if not os.path.isfile(APP):
    print('COULD NOT RUN: no %s. Nothing was verified.' % APP)
    sys.exit(3)

RAW, CODE = read(APP)

# ── ARM 0: THE STRIPPER ITSELF, DRIVEN ───────────────────────────────────
# Everything below depends on it, and its failure mode is silent: a stripper
# that blanks too much makes a missing caller look present-then-absent, and one
# that blanks too little makes a COMMENT satisfy the wiring check -- which is
# precisely the state that shipped.
FIX_COMMENT_ONLY = (
    "// the note about law_trust_reconcile and sdnData('read','law_trust_reconcile',{})\n"
    "var x = 1;\n")
FIX_REAL_CALL = (
    "// the note about law_trust_reconcile\n"
    "sdnData('read','law_trust_reconcile',{client_total_cents:0});\n")
FIX_URL = "var u = 'https://example.com/a'; var y = 2;\n"
check('0a. a call that exists ONLY inside a comment does NOT count as wired',
      not has_real_call(strip_comments(FIX_COMMENT_ONLY)),
      'the stripper left a commented call visible -- this is the exact state '
      'that shipped, and a probe that accepts it proves nothing')
check('0b. ...and a real call DOES count, so 0a is not a stripper that blanks '
      'everything',
      has_real_call(strip_comments(FIX_REAL_CALL)))
check('0c. ...and a `//` inside a string literal does not eat the rest of the line',
      'var y = 2;' in strip_comments(FIX_URL),
      strip_comments(FIX_URL))

# ── ARMS 1-4: THE REPAIR IS PRESENT ──────────────────────────────────────
check('1. sairnlaw.html actually CALLS law_trust_reconcile (not in a comment)',
      has_real_call(CODE),
      'the server reconciler is unreachable from the product again')
check('2. the sentence "Reconciled -- all three balances match" is not RENDERABLE',
      verdict_string_gone(CODE),
      'a green three-way verdict is renderable again')
check('3. the tautological leg and its function are gone',
      tautology_gone(CODE),
      'ledgerVsClient or reconcileTrust() is back -- a verdict that cannot fail')
check('4. THE PAIRED POSITIVE: the figures are still computed and displayed, '
      'so arms 1-3 are not satisfied by deleting the panel',
      figures_kept(CODE))
check('5. a failed or forbidden reconciliation cannot reach the agreement branch',
      unavailable_is_not_agreement(CODE))

# ── ARMS 6-9: PUT THE DEFECT BACK, AND THIS PROBE MUST REFUSE IT ─────────
# Mutations are applied to an in-memory copy. Nothing on disk is touched --
# this repo's own precedent is that a probe which edits a tracked file is
# indistinguishable from residue when it dies, and sairnlaw.html is a file a
# reader would trust on sight.
MUTATIONS = [
    ('6. reverting to the comment-only mention is REFUSED',
     lambda raw: CALL_RE.sub("/* sdnData('read','law_trust_reconcile'", raw, count=1),
     lambda raw, code: has_real_call(code)),
    ('7. restoring the green three-way sentence is REFUSED',
     lambda raw: raw.replace('Not verified',
                             'Reconciled -- all three balances match', 1),
     lambda raw, code: verdict_string_gone(code)),
    ('8. reintroducing the tautological leg is REFUSED',
     lambda raw: raw.replace('function trustFigures(){',
                             'function trustFigures(){var ledgerVsClient=1;', 1),
     lambda raw, code: tautology_gone(code)),
    ('9. deleting the figures to satisfy arms 1-3 is REFUSED',
     lambda raw: raw.replace('function trustFigures(', 'function gone_(', 1),
     lambda raw, code: figures_kept(code)),
]
for label, mutate, predicate in MUTATIONS:
    mraw = mutate(RAW)
    if mraw == RAW:
        check(label, False,
              'THE MUTATION PLANTED NOTHING -- its anchor no longer matches, so '
              'this arm is not testing what it says it tests. Fix the anchor, '
              'not the subject.')
        continue
    check(label, not predicate(mraw, strip_comments(mraw)),
          'the mutated file still passed the check it was built to break')

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
