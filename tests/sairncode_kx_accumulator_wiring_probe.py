r"""The KX accumulator must be CALLED, and no threshold verdict may rest on a typed box alone.

Run: python tests/sairncode_kx_accumulator_wiring_probe.py

WHY A WIRING PROBE AND NOT ONLY THE UNIT SUITE.
`api/_lib/sairncode-kx-accumulator.test.js` drives the engine, 20 arms, both
directions. It is blind by construction to the thing that was actually wrong:
the KX RULES in `sairncode.html` were already correct and CMS-cited, and the
YEAR-TO-DATE NUMBER they were compared against was typed into a text box.
A coder who keyed 2400 got a clean "KX not required" with nothing behind it.

THIS IS THE THIRD TIME THIS SHAPE HAS BEEN PAID FOR ON THIS PLATFORM TONIGHT --
`900374e0` (a flag implemented and never proven wired), the IOLTA reconciler
(a correct engine whose only mention in the app was a comment), and this. The
unit test is not the control for "is it reached".

WHAT THE ARMS ASSERT, and each is a sentence about a specific way a coder gets
a wrong answer on a federal threshold:

  1-2  the accumulator is reachable end to end -- registered as a verb, called
       by the handler, and called by the app. A verb nothing invokes, or a
       handler branch no client reaches, is the defect all over again.
  3    a FLOOR is not rendered as a total. `is_floor` must change the words on
       screen; if a partial count and a complete one read the same, rule 3 of
       the accumulator has been undone at the last step and the engine's
       honesty never reaches a human.
  4    a FAILED computation is never "KX not required". This is the answer the
       typed box could not give and the one a coder most needs.
  5    the typed box may still exist -- a beneficiary treated elsewhere has a
       real total this practice cannot see -- but it must be labelled as an
       override, and a hand-entered figure must SAY it was hand-entered.
  6    the claim-entry form captures the three fields, and refuses a therapy
       claim with no beneficiary key rather than silently unattributing it.
  7    BILLED is never accumulated. The form must send `allowed_amount`, not
       `amount`, because overstating a year-to-date total attaches KX to a
       claim that did not need it -- an attestation of medical necessity, not
       a rejection letter.

AND FIVE MUTATION ARMS put each defect back and assert this probe refuses it.

COMMENTS ARE STRIPPED BEFORE EVERY CODE SEARCH. Both the broken state and the
repaired state MENTION the accumulator -- the repaired one mentions it in
prose too -- so a raw-text search cannot tell a call from a citation. Arm 0
drives the stripper itself with fixtures, in both directions.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, 'sairncode.html')
HANDLER = os.path.join(REPO, 'api', 'sd-data.js')
REGISTRY = os.path.join(REPO, 'api', '_resources', 'sairncode.js')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def strip_comments(js):
    """Blank // and /* */ spans, string-aware, preserving length.

    STRING-AWARE, because these files carry URLs and regexes and a naive `//`
    strip would blank from the middle of `https://` to end of line -- deleting
    real code from the probe's view, which fails OPEN.
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


def code_of(path):
    return strip_comments(io.open(path, encoding='utf-8', errors='replace').read())


# ── THE CHECKS, SHARED BY THE POSITIVE AND THE MUTATION ARMS ─────────────
CLIENT_CALL = re.compile(r"scData\s*\(\s*'therapy_accumulator'\s*,\s*'sc_claims'")
HANDLER_CALL = re.compile(r"kxAccumulator\s*\.\s*accumulateTherapy\s*\(")
HANDLER_BRANCH = re.compile(r"action\s*===\s*'therapy_accumulator'")


def client_calls(app):
    return bool(CLIENT_CALL.search(app))


def handler_calls(h):
    return bool(HANDLER_CALL.search(h)) and bool(HANDLER_BRANCH.search(h))


def verb_registered(reg):
    return "'therapy_accumulator'" in reg


def floor_reaches_the_screen(app):
    """`is_floor` must change the VERDICT, not just be carried in the payload.

    ── ANCHORED ON THE BRANCH, NOT ON THE SENTENCE (and the first spelling was
    ── anchored on the sentence, which was the same defect it was checking for)
    The first version looked for the words 'FLOOR, NOT A TOTAL' in the page.
    That is a check on the WORDING of a message, and the code it was checking
    had the identical flaw: `isFloorAnswer = provenance.indexOf('THIS IS A
    FLOOR') !== -1`, so rephrasing the sentence for clarity would silently
    promote a floor back to a clearance. Both are fixed: the app carries a real
    boolean and this asserts the BRANCH exists -- `is_floor` reaches a variable,
    and that variable gates the `not_required` verdict.
    """
    return ('is_floor' in app
            and 'isFloor' in app
            and re.search(r"isFloorAnswer\s*=\s*acc\.isFloor", app) is not None
            and re.search(r"r\.status\s*===\s*'not_required'\s*&&\s*isFloorAnswer",
                          app) is not None)


def failure_is_not_a_clearance(app):
    """A failed computation must reach the STOP branch, never not_required."""
    return ('acc.failed' in app
            and 'Cannot determine' in app
            and 'DU_STYLE_STOP' in app)


def override_is_labelled(app):
    """A hand-entered figure must say so on screen."""
    return 'ENTERED BY HAND' in app.upper()


def form_captures(app):
    return ("rec.discipline" in app and "rec.beneficiary_id" in app
            and "rec.allowed_amount" in app)


def form_refuses_unattributed_therapy(app):
    return re.search(r'if\s*\(\s*discipline\s*&&\s*!\s*beneficiaryId\s*\)', app) is not None


def allowed_not_billed(app):
    """The accumulator field must be fed from the ALLOWED input, never Amount."""
    return ("clm-add-allowed" in app
            and re.search(r"rec\.allowed_amount\s*=\s*allowed\b", app) is not None
            and re.search(r"rec\.allowed_amount\s*=\s*amount\b", app) is None)


print('KX accumulator wiring -- the engine must be reached, and a floor must '
      'never read as a clearance\n')

for p in (APP, HANDLER, REGISTRY):
    if not os.path.isfile(p):
        print('COULD NOT RUN: no %s. Nothing was verified.' % p)
        sys.exit(3)

APP_CODE = code_of(APP)
H_CODE = code_of(HANDLER)
REG_CODE = code_of(REGISTRY)

# ── ARM 0: THE STRIPPER, DRIVEN ──────────────────────────────────────────
COMMENT_ONLY = ("// it now calls scData('therapy_accumulator','sc_claims',{})\n"
                "var x = 1;\n")
REAL = "await scData('therapy_accumulator','sc_claims',{year:2026});\n"
URLY = "var u = 'https://example.com/x'; var y = 2;\n"
check('0a. a call that exists ONLY in a comment does NOT count as wired',
      not client_calls(strip_comments(COMMENT_ONLY)),
      'a probe that accepts a commented call would have passed on the broken file')
check('0b. ...and a real call DOES count, so 0a is not a stripper that blanks all',
      client_calls(strip_comments(REAL)))
check('0c. ...and a `//` inside a string does not eat the rest of the line',
      'var y = 2;' in strip_comments(URLY))

# ── ARMS 1-7: THE REPAIR IS PRESENT ──────────────────────────────────────
check('1. the verb is REGISTERED and the handler branch CALLS the engine',
      verb_registered(REG_CODE) and handler_calls(H_CODE),
      'registered=%s handler=%s' % (verb_registered(REG_CODE), handler_calls(H_CODE)))
check('2. sairncode.html actually CALLS it (not in a comment)',
      client_calls(APP_CODE),
      'the accumulator is unreachable from the product -- the defect again')
check('3. a FLOOR changes the words on screen, it is not merely carried',
      floor_reaches_the_screen(APP_CODE),
      'a partial count and a complete one would read identically')
check('4. a FAILED computation reaches the STOP branch, never "KX not required"',
      failure_is_not_a_clearance(APP_CODE))
check('5. a hand-entered override is LABELLED as hand-entered',
      override_is_labelled(APP_CODE))
check('6. the claim form captures all three fields AND refuses a therapy claim '
      'with no beneficiary key',
      form_captures(APP_CODE) and form_refuses_unattributed_therapy(APP_CODE),
      'captures=%s refuses=%s' % (form_captures(APP_CODE),
                                  form_refuses_unattributed_therapy(APP_CODE)))
check('7. the accumulator field is fed from ALLOWED, never from the billed Amount',
      allowed_not_billed(APP_CODE),
      'accumulating billed charges crosses the threshold before Medicare does, '
      'and crossing early is a false attestation rather than a denial')

# ── ARMS 8-12: PUT EACH DEFECT BACK ──────────────────────────────────────
RAW_APP = io.open(APP, encoding='utf-8', errors='replace').read()
RAW_H = io.open(HANDLER, encoding='utf-8', errors='replace').read()
MUTATIONS = [
    ('8. reverting the client call to a comment-only mention is REFUSED',
     RAW_APP, lambda s: CLIENT_CALL.sub("/* scData('therapy_accumulator','sc_claims'", s, 1),
     lambda code: client_calls(code)),
    ('9. removing the handler branch is REFUSED',
     RAW_H, lambda s: HANDLER_BRANCH.sub("action === 'never_matches_'", s, 1),
     lambda code: handler_calls(code)),
    ('10. letting a FLOOR reach the same verdict as a total is REFUSED',
     RAW_APP, lambda s: s.replace("r.status === 'not_required' && isFloorAnswer",
                                  "r.status === 'never_'", 1),
     lambda code: floor_reaches_the_screen(code)),
    ('10b. ...and so is severing is_floor from the variable that gates it',
     RAW_APP, lambda s: s.replace('isFloorAnswer = acc.isFloor',
                                  'isFloorAnswer = false', 1),
     lambda code: floor_reaches_the_screen(code)),
    ('11. dropping the hand-entered label is REFUSED',
     RAW_APP, lambda s: s.replace('ENTERED BY HAND', 'computed', 1),
     lambda code: override_is_labelled(code)),
    ('12. feeding the accumulator the BILLED amount is REFUSED',
     RAW_APP, lambda s: s.replace('rec.allowed_amount = allowed',
                                  'rec.allowed_amount = amount', 1),
     lambda code: allowed_not_billed(code)),
]
for label, raw, mutate, predicate in MUTATIONS:
    m = mutate(raw)
    if m == raw:
        check(label, False,
              'THE MUTATION PLANTED NOTHING -- its anchor no longer matches, so '
              'this arm is not testing what it says it tests. Fix the anchor, '
              'not the subject.')
        continue
    check(label, not predicate(strip_comments(m)),
          'the mutated file still passed the check it was built to break')

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
