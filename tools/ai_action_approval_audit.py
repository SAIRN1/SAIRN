"""ai_action_approval_audit.py -- can an AI-PROPOSED action reach storage with
nobody having approved it?

    python tools/ai_action_approval_audit.py
    python tools/ai_action_approval_audit.py --json
    python tools/ai_action_approval_audit.py --selftest

── THE QUESTION, AND WHY A DOCUMENT CANNOT ANSWER IT ─────────────────────────
Every AI feature on this platform is described as advisory. `sairn-app-scaffold`
requires photo -> Claude -> structured output where "staff reviews before
saving, never auto-submitted". Several app headers say the same in their own
words. That is a rule written down.

A RULE WRITTEN DOWN AND A GATE IN THE CODE ARE INDISTINGUISHABLE UNTIL THE DAY
IT MATTERS, and this file is the mechanical half. It asks one narrow question
per AI call site:

    in the function that receives the model's answer, is there a path that
    WRITES -- to storage, or to the server -- without a separate, human-
    initiated step in between?

A function that renders the answer into the DOM, or drops it into a form field
for somebody to read and save, is gated BY CONSTRUCTION: the save is a second
function reached by a click. A function that receives an answer and calls a
write in the same body is not, and that is the shape worth a human reading.

── IT IS A LOCATOR, NOT A DETECTOR, AND THE COUNT IS NOT A SCORE ────────────
Same standing as tools/accepted_risk_scan.py. It reads structure, not intent:

  * a write guarded by a `confirm()` two functions away reads as UNGATED here;
  * an AI handler that writes a CACHE or a chat transcript reads the same as
    one that writes an invoice, because both are writes;
  * an `await` boundary inside one function is a real human-approval point in
    some UI patterns and this cannot see which.

So every finding is a READ-LIST ENTRY. Driving the number to zero is not the
goal and would mostly mean moving writes into helpers. What the list is for is
that NOBODY HAS EVER ENUMERATED THESE, and a financial or customer-facing one
hiding among the chat transcripts is exactly what nobody would find by reading.

── WHAT IT DELIBERATELY DOES NOT CLAIM ──────────────────────────────────────
It does not say a finding is a defect. It does not rank apps. It does not read
the model's output or reason about what the AI might propose. And a CLEAN app is
reported as "no AI handler writes", which is a statement about this scanner's
reach and not a safety certificate -- stated here because that sentence is
exactly what a reader would otherwise take from a zero.

REPORT ONLY. Exit 0 with findings, exit 2 when it could not look.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import jscomments                                                # noqa: E402

# The transports. A call to any of these IS the AI round trip on this platform;
# every app either posts to the shared proxy or wraps it in a named helper.
#
# COVERAGE WAS WRONG ON THE FIRST RUN, AND FIXING IT IS WHAT MAKES THE NUMBER
# WORTH ANYTHING. The first pattern matched the literal `api/claude` plus the
# named wrappers, and reported 38 sites across SEVEN apps -- while seventeen app
# files mention AI at all. The missing ten do not spell the URL at the call
# site: they hold it in a module constant
# (`var PROXY='https://sairn.vercel.app/api/claude'`) and post to `PROXY`.
#
# A scanner that reads one spelling reports a clean sweep over every app using
# the other, which is the false-coverage shape this platform keeps finding --
# and it would have read as "ten apps have no AI writes" rather than as "this
# tool cannot see ten apps". `\bPROXY\b` is here for exactly that.
AI_CALL = re.compile(
    r'(?:'
    r'\bapi/claude|\bcallAnthropic\b|\bPROXY\b|'
    r'\bscAiFetch\b|\bsdnAiFetch\b|\blawAiFetch\b|\bdntAiFetch\b|'
    r'\blegAiFetch\b|\bbldAiFetch\b|\bsairnCallClaude\b|\bcallAI\b|'
    r'\bscpCallAI\b|\baiFetch\b'
    r')')

# A WRITE: it leaves the function and lands somewhere that outlives the click.
# Broad on purpose -- the cost of an extra read-list entry is one look, and the
# cost of a missed one is the thing this file exists to find.
WRITE = re.compile(
    r'\b(?:'
    r'localStorage\.setItem|sessionStorage\.setItem|'
    r'st\s*\(|save[A-Z]\w*\s*\(|'
    r'sdData\s*\(|sdnData\s*\(|scData\s*\(|lawData\s*\(|dntData\s*\(|'
    r'legData\s*\(|bldData\s*\(|rfData\s*\(|senData\s*\(|grdData\s*\(|'
    r'sbData\s*\(|svData\s*\(|scpData\s*\('
    r')')
# A POST/PATCH/PUT through fetch is a write even when it is not one of the
# named helpers -- an app that talks to its own endpoint directly still writes.
#
# ── AND THE AI CALL IS ITSELF A POST, WHICH THE FIRST VERSION COUNTED ──────
# CAUGHT BY SPOT-CHECKING THREE FINDINGS RATHER THAN BY READING THE CODE. The
# first version matched `method:'POST'` anywhere in the body, and the AI round
# trip on this platform IS a POST to the proxy -- so EVERY AI handler counted as
# writing, and the headline read 59 ungated writes when the real POST in
# `sdInvAI`, `commsAIReply` and `invSmartReorder` was the model call itself.
#
# A number that large would have been acted on. It was wrong, and it was wrong
# in the direction that manufactures alarm, which is how a locator gets ignored.
# Now each `fetch(` is examined on its own: a POST counts only when that
# PARTICULAR call is not the AI transport.
MUTATING = re.compile(r"method\s*:\s*['\"](?:POST|PATCH|PUT|DELETE)['\"]")


def mutating_fetch(body):
    """True when some fetch() in this body mutates something OTHER than the
    model endpoint. Window-based rather than paren-matched: an options object
    is next to its URL in every call site on this platform, and paren matching
    across template literals is its own source of wrong answers."""
    # THE WORD BOUNDARY HERE WAS A LITERAL BACKSPACE FOR ONE REVISION (0x08),
    # so the regex could never match, this function returned False for every
    # body, and the AI-POST fix silently did nothing. It is the defect this
    # codebase already records -- 'a regex that shipped with a literal
    # backspace and could never match' -- reproduced by writing the file
    # through a shell heredoc that ate the escape. THE SELFTEST CAUGHT IT;
    # reading the source did not, twice.
    for m in re.finditer(r'\bfetch\s*\(', body):
        window = body[m.start():m.start() + 400]
        if not MUTATING.search(window):
            continue
        if AI_CALL.search(window):
            continue          # this POST is the model call, not a data write
        return True
    return False

# An explicit human step INSIDE the same body. Narrow deliberately: these are
# the only ones a scanner can see, and a gate it cannot see is reported as
# absent, which is the safe direction for a locator.
# NO TRAILING \b. The first version had one, and it silently broke every
# alternative ending in `(` -- after `confirm(` the next character is a quote,
# and `(` to `'` is not a word boundary, so `confirm('save?')` did not match and
# a genuinely gated write was reported UNGATED. Caught by the selftest fixture
# below rather than by reading, which is the entire argument for having one.
GATE = re.compile(
    r'(?:\bconfirm\s*\(|\bwindow\.confirm\s*\(|'
    r'\brequireApproval\b|\bawaitApproval\b|\bapprovedBy\b|'
    r'\bapproval_required\b|\bhuman_approved\b|\breviewedBy\b)')

# Rendering only -- the answer goes somewhere a person must act on next.
RENDER = re.compile(r'\b(?:innerHTML|textContent|\.value\s*=|appendChild|insertAdjacentHTML)\b')


def app_files():
    out = subprocess.run(['git', '-C', REPO, 'ls-files', '*.html'],
                         capture_output=True, encoding='utf-8', errors='replace')
    if out.returncode != 0:
        return None
    return [f for f in out.stdout.split('\n')
            if f and not f.startswith(('archive/', 'docs/'))]


def functions(src):
    """(name, body) for every `function name(...) {...}`, brace-matched.

    Brace matching rather than a regex to the next `function`: a nested helper
    would otherwise truncate its parent's body and hide a write that really is
    in the same function.
    """
    out = []
    for m in re.finditer(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', src):
        name = m.group(1)
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
        if depth == 0:
            out.append((name, src[i:j + 1]))
    return out


def classify(body):
    writes = bool(WRITE.search(body) or mutating_fetch(body))
    if not writes:
        return 'RENDER_ONLY' if RENDER.search(body) else 'NO_WRITE'
    return 'GATED_IN_BODY' if GATE.search(body) else 'WRITES_UNGATED'


def audit():
    files = app_files()
    if files is None:
        return None
    rows = []
    for rel in files:
        path = os.path.join(REPO, rel)
        try:
            raw = io.open(path, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        src = jscomments.strip_comments(raw)
        for name, body in functions(src):
            if not AI_CALL.search(body):
                continue
            rows.append({'app': rel, 'function': name,
                         'verdict': classify(body), 'size': len(body)})
    return rows


def selftest():
    """Lock the criteria against synthetic bodies before believing a real
    number. A classifier that has only ever run on real input has not been
    shown to discriminate -- three tools on this platform were wrong in exactly
    that way and each was caught by a control built to make it fail."""
    cases = [
        ("{ const r = await scAiFetch(p); el.innerHTML = r.text; }", 'RENDER_ONLY'),
        ("{ const r = await scAiFetch(p); localStorage.setItem('k', r.text); }", 'WRITES_UNGATED'),
        ("{ const r = await scAiFetch(p); if (confirm('save?')) st('k', r); }", 'GATED_IN_BODY'),
        ("{ const r = await callAnthropic(p); await fetch(u, {method:'POST'}); }", 'WRITES_UNGATED'),
        # THE FALSE POSITIVE THAT INFLATED THE FIRST REAL RUN: the AI call is
        # itself a POST. A body whose only mutating fetch IS the model call
        # must not read as a data write.
        ("{ const r = await fetch(PROXY, {method:'POST', body: p}); el.innerHTML = r; }",
         'RENDER_ONLY'),
        ("{ const r = await fetch(PROXY, {method:'POST'}); await fetch('/api/sd-data', {method:'POST'}); }",
         'WRITES_UNGATED'),
        ("{ const r = await scAiFetch(p); return r.text; }", 'NO_WRITE'),
        ("{ const r = await scAiFetch(p); saveQuote(r); }", 'WRITES_UNGATED'),
    ]
    bad = 0
    for body, want in cases:
        got = classify(body)
        ok = got == want
        bad += 0 if ok else 1
        print('  %s expected %-14s got %-14s | %s'
              % ('ok  ' if ok else 'FAIL', want, got, body[:56]))
    # And the transport detector itself, in both directions.
    assert AI_CALL.search('await scAiFetch(x)'), 'transport not detected'
    if AI_CALL.search('await saveQuote(x)'):
        print('  FAIL a non-AI call matched the transport pattern'); bad += 1
    else:
        print('  ok   a non-AI call does NOT match the transport pattern')
    print('')
    if bad:
        print('  %d of %d fixtures misclassified -- the real numbers would be '
              'meaningless. Fix the criteria first.' % (bad, len(cases) + 1))
    else:
        print('  all %d fixtures classified correctly, in BOTH directions '
              '(a gated write and an ungated one, an AI call and a non-AI one).'
              % (len(cases) + 1))
    return 2 if bad else 0


def main():
    if '--selftest' in sys.argv:
        return selftest()
    rows = audit()
    if rows is None:
        print('COULD NOT CHECK: `git ls-files` failed, so NOTHING WAS MEASURED.')
        print('Zero findings here is not a clean sweep.')
        return 2
    if '--json' in sys.argv:
        print(json.dumps(rows, indent=1))
        return 0

    order = ['WRITES_UNGATED', 'GATED_IN_BODY', 'RENDER_ONLY', 'NO_WRITE']
    counts = dict((k, 0) for k in order)
    for r in rows:
        counts[r['verdict']] = counts.get(r['verdict'], 0) + 1

    print('AI-PROPOSED ACTIONS AND WHETHER A HUMAN HAS TO APPROVE THEM')
    print('  report only -- the count is a READ-LIST, not a score')
    print('')
    print('  AI call sites found : %d across %d app file(s)'
          % (len(rows), len(set(r['app'] for r in rows))))
    print('')
    print('  WRITES_UNGATED %3d  the handler that receives the model answer also'
          % counts['WRITES_UNGATED'])
    print('                      WRITES, with no human step this can see')
    print('  GATED_IN_BODY  %3d  it writes, and there is an explicit confirm/approval'
          % counts['GATED_IN_BODY'])
    print('  RENDER_ONLY    %3d  the answer goes to the DOM or a form field -- the'
          % counts['RENDER_ONLY'])
    print('                      save is a separate click, gated BY CONSTRUCTION')
    print('  NO_WRITE       %3d  neither writes nor renders (helpers, transports)'
          % counts['NO_WRITE'])
    print('')
    for v in order:
        sel = [r for r in rows if r['verdict'] == v]
        if not sel or v in ('NO_WRITE',):
            continue
        print('── %s ──────────────────────────────────' % v)
        for r in sorted(sel, key=lambda x: (x['app'], x['function'])):
            print('  %-26s %s' % (r['app'], r['function']))
        print('')

    print('WHAT A ZERO WOULD AND WOULD NOT MEAN. "No AI handler writes" is a')
    print('statement about THIS SCANNER\'S REACH, not a safety certificate: a')
    print('write behind a helper, or a confirm() two functions away, reads as')
    print('the wrong thing here in both directions. Every line above is a')
    print('POINTER TO READ A FUNCTION, never a verdict about one.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
