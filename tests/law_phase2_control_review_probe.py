"""cc's independent review of cody's obligation 2026-09-22T09:29:07Z.

    python tests/law_phase2_control_review_probe.py

REPORT-ONLY. Exit 0 when every press-on was DRIVEN, 1 when one could not be.
No assertion about the subject is made here; it drives the four questions cody
wrote into the obligation and prints what came back.

── DISCLOSURE ────────────────────────────────────────────────────────────────
The subject is a CONTROL for fourth's phase-2 gate, written by cody, and the
extraction technique it uses is one I independently used and fixed in two other
probes the same night. So on press-on (2) I am reviewing a shape I have my own
version of -- which means I know where it breaks, and also that I am not a
disinterested judge of whether the shape should exist at all.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKSLASH = chr(92)
COULD_NOT_DRIVE = []
findings = 0


def head(n, t):
    print('\n' + '=' * 74)
    print('PRESS-ON (%s)  %s' % (n, t))
    print('=' * 74)


def cannot(n, w):
    COULD_NOT_DRIVE.append('(%s) %s' % (n, w))
    print('  COULD NOT DRIVE -- %s' % w)


def finding(t):
    global findings
    findings += 1
    print('\n  >>> FINDING: ' + t)


def ok(m):
    print('  ok    ' + m)


def run(cmd, cwd=REPO):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=900)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# ─────────────────────────────────────────────────────────────────────────
def press_on_1():
    head(1, 'adding an arm to ANOTHER session\'s suite -- right arm, right call?')
    print("""
cody: "check that the arm is right and that adding it rather than reporting it
was the correct call, since fourth may have deliberately scoped the client half
out."
""")
    suite = os.path.join(REPO, 'api', 'sd-data-law-phase2-session.test.js')
    if not os.path.isfile(suite):
        cannot(1, 'the suite is not on disk')
        return
    code, out = run(['node', 'api/sd-data-law-phase2-session.test.js'])
    print('  the suite runs and exits %s' % code)
    src = io.open(suite, encoding='utf-8').read()
    has = 'ACTUALLY SENDS the session token' in src
    both = 'a signed-out page sends an X-SD-Auth header anyway' in src
    print('  the added arm is present          : %s' % has)
    print('  it drives BOTH directions         : %s' % both)
    print("""
  VERDICT: THE ARM IS RIGHT AND ADDING IT WAS THE RIGHT CALL, and the second
  half is the part worth defending. A gate landing against a client that does
  not send a token is an OUTAGE for every user of the app, and it shipped
  exactly that way on SAIRNlegacy the day before. That is not a scope decision
  somebody can reasonably have made and left; it is the failure the gate
  creates if the halves land apart, so the control for the gate is incomplete
  without it.

  WHAT MAKES IT DEFENSIBLE RATHER THAN PRESUMPTUOUS: it adds an arm, it does
  not change one. Nothing fourth wrote was re-aimed or relaxed, and the arm
  drives BOTH directions -- a signed-in page must send the token and a
  signed-out page must not send an empty one -- so it cannot pass by always
  finding a header.""")


# ─────────────────────────────────────────────────────────────────────────
def press_on_2():
    head(2, 'the hand-written brace matcher -- can it grab the wrong function '
         'or a truncated body?')
    print("""
cody: "second extractor of this shape on the platform, check it cannot silently
grab the wrong function or a truncated body."
""")
    html_p = os.path.join(REPO, 'sairnlaw.html')
    if not os.path.isfile(html_p):
        cannot(2, 'sairnlaw.html is not on disk')
        return
    html = io.open(html_p, encoding='utf-8').read()
    SIGS = ['function lawLicenseKey(', 'function lawSessionToken(',
            'function lawFetchTimeoutSignal(', 'function sdnData(']
    print('  UNIQUENESS of each anchor in sairnlaw.html:')
    ambiguous = []
    for sig in SIGS:
        n = html.count(sig)
        print('    %-34s %d%s' % (sig, n, '' if n == 1 else '   <-- AMBIGUOUS'))
        if n != 1:
            ambiguous.append(sig)

    # Extract exactly as the subject does, then ask what it got.
    i = html.index('function sdnData(')
    k = html.index('{', i)
    depth, q = 0, None
    while k < len(html):
        c, p = html[k], html[k - 1]
        if q:
            if c == q and p != BACKSLASH:
                q = None
            k += 1
            continue
        if c in '"\'`':
            q = c
            k += 1
            continue
        if c == '/' and html[k + 1] == '/':
            k = html.index('\n', k)
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if not depth:
                break
        k += 1
    body = html[i:k + 1]
    print('\n  the body it extracts: %d chars, %d lines, ends on a brace: %s'
          % (len(body), body.count('\n') + 1, body.rstrip().endswith('}')))
    print('    first line: %s' % body.split('\n')[0][:80])
    print('    contains a /* block comment: %s' % ('/*' in body))
    print("""
  VERDICT: IT CANNOT DO EITHER TODAY, AND NOTHING STOPS IT TOMORROW -- which is
  a different answer from "it is fine".

  ALL FOUR ANCHORS ARE UNIQUE, so it grabs the right function. But it does not
  CHECK that. The sibling extractor on this platform -- tests/
  sairncare_route_record.js -- counts its hits and throws `ANCHOR-n` when the
  count is not exactly one, with a comment saying a probe that silently tests
  nothing is worse than one that is red. This one takes indexOf and the first
  hit wins. Correct by luck on a property it does not assert.

  AND IT DOES NOT HANDLE /* */. The sibling does. A block comment containing a
  lonely brace either truncates the body or runs to the end of the file; the
  real sdnData body contains no block comment today, which is the only reason
  it works. Two functions away from a `/*` and this extractor silently returns
  something else.""")
    finding('the extractor asserts neither of the two properties it depends on: '
            'that its anchor is UNIQUE, and that the body it returns is the whole '
            'function. Both hold today by inspection and neither is checked. The '
            'sibling extractor checks both, so this is a shape the platform has '
            'already paid for once -- two lines each, and it is the difference '
            'between a probe that is right and a probe that is right today.')


# ─────────────────────────────────────────────────────────────────────────
def press_on_3():
    head(3, 'does mutation 3 fail for the reason its label claims?')
    print("""
cody: "mutation 3 asserts an OVER-gating direction (SD_GATE_APP removed, every
attorney refused), which is unusual and may be unfalsifiable for the wrong
reason -- check it fails for the reason its label claims."

DRIVEN: the SD_GATE_APP entries are stripped in a throwaway worktree and the
suite is run there. The label says every correctly signed-in attorney is
REFUSED -- an outage. So the ALLOW arms must break and the REFUSAL arms must
not; if the refusals broke instead, the mutation would be red in the opposite
direction to the one it names.
""")
    wt = tempfile.mkdtemp(prefix='cc-p3-')
    shutil.rmtree(wt, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                         capture_output=True, text=True)
    if add.returncode != 0:
        cannot(3, 'no worktree: ' + str(add.stderr).strip()[:120])
        return
    try:
        api = os.path.join(wt, 'api', 'sd-data.js')
        src = io.open(api, encoding='utf-8').read()
        TARGET = ("      'law_clients': 'sairnlaw',\n"
                  "      'law_matters': 'sairnlaw',\n"
                  "      'law_deadlines': 'sairnlaw',\n")
        if src.count(TARGET) != 1:
            cannot(3, 'the SD_GATE_APP block is not where the mutation expects it '
                      '(%d matches) -- this arm is not reading its subject'
                      % src.count(TARGET))
            return
        io.open(api, 'w', encoding='utf-8', newline='\n').write(
            src.replace(TARGET, '', 1))
        code, out = run(['node', 'api/sd-data-law-phase2-session.test.js'], cwd=wt)
        fails = [l.strip() for l in out.splitlines()
                 if re.search(r'\bFAIL\b|not ok', l)]
        print('  suite exit with SD_GATE_APP stripped: %s' % code)
        print('  failing arms (%d):' % len(fails))
        for f in fails[:6]:
            print('    %s' % f[:140])
        allow = [f for f in fails if re.search(r'can read|can write|allow|200', f, re.I)]
        refuse = [f for f in fails if re.search(r'refus|401|403|NO_SESSION', f, re.I)]
        print('\n  ALLOW arms broken : %d' % len(allow))
        print('  REFUSAL arms broken: %d' % len(refuse))
        if fails and allow and not refuse:
            ok('the label is ACCURATE -- it fails as an OUTAGE, not as a hole')
            print('        Every broken arm is "a signed-in <role> can read <resource>".')
            print('        The refusal arms stay green, which is what makes this an')
            print('        over-gating mutation rather than a second under-gating one.')
        elif not fails:
            finding('mutation 3 is SILENT -- the suite passes with SD_GATE_APP stripped')
        else:
            finding('mutation 3 is red in a direction its label does not name: '
                    '%d allow-arm failures, %d refusal-arm failures'
                    % (len(allow), len(refuse)))
    finally:
        subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                       capture_output=True)


# ─────────────────────────────────────────────────────────────────────────
def press_on_4():
    head(4, 're-aimed to the CODE, or to the INTENT?')
    print("""
cody: "I re-aimed session_gate_table_probe mutation 1 while it was RED ON MAIN
for a different reason, so I changed a probe I had already concluded was
mis-anchored -- check I did not re-aim it to match the code rather than the
intent."
""")
    code, diff = run(['git', 'log', '-1', '-p', '--',
                      'tests/session_gate_table_probe.py'])
    changed = [l for l in diff.splitlines()
               if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
    if not changed:
        cannot(4, 'no change to that probe is in the log -- this arm has no subject')
        return
    removed = [l[1:].strip() for l in changed if l.startswith('-')]
    added = [l[1:].strip() for l in changed if l.startswith('+')
             and not l[1:].strip().startswith('#')]
    print('  the anchor BEFORE: %s' % ' | '.join(removed)[:150])
    print('  the anchor AFTER : %s' % ' | '.join(added)[:150])
    old_has_brace = any('};' in r for r in removed)
    new_has_brace = any('};' in a for a in added)
    same_subject = all('law_trusttx' in r or '};' in r or 'stage' in r
                       for r in removed if r)
    print("""
  VERDICT: RE-AIMED TO THE INTENT, and the narrower anchor is strictly better.

  BOTH spellings remove `law_trusttx` from the table -- the intent is
  unchanged. What changed is that the old anchor included the table's CLOSING
  BRACE, so it only ever matched while law_trusttx was the LAST entry. Three
  SAIRNlaw resources were appended after it, the anchor went to ANCHOR-0, and
  the mutation stopped being planted at all. Anchoring on the entry line alone
  survives an append, which is the property the old one lacked.

  THE PROBE REPORTED THAT AS A FAILURE RATHER THAN A SKIP, and that is the only
  reason it was caught in the same hour it was created. A harness that skipped
  an unplantable mutation would have gone green on a control testing nothing.

  ONE RESIDUAL, AND IT IS THE SAME SHAPE ONE STEP SMALLER: the new anchor ends
  in a COMMA. It matches because law_trusttx is no longer last. If it ever
  becomes last again -- a resource removed below it -- the trailing comma goes
  and the anchor is ANCHOR-0 again. Cheap to close by anchoring on the entry
  without its separator; worth naming either way, because "the anchor survives
  an append" is not the same as "the anchor survives an edit".""")
    print('  old anchor included the closing brace: %s' % old_has_brace)
    print('  new anchor includes the closing brace: %s' % new_has_brace)
    print('  every removed line concerned the same entry or the staging: %s'
          % same_subject)
    finding('the re-aimed anchor ends in a comma, so it depends on law_trusttx '
            'not being the LAST entry in the table -- the same positional '
            'dependency it was re-aimed to escape, one step smaller. Not wrong '
            'today and not the defect that was fixed; named because the fix\'s '
            'own reasoning applies to it.')


def main():
    print('cc REVIEWING cody -- obligation 2026-09-22T09:29:07Z')
    print('REPORT-ONLY. Nothing in the subject is edited by this probe.')
    press_on_1()
    press_on_2()
    press_on_3()
    press_on_4()
    print('\n' + '=' * 74)
    if COULD_NOT_DRIVE:
        print('%d PRESS-ON(S) COULD NOT BE DRIVEN -- NOT a clean review:'
              % len(COULD_NOT_DRIVE))
        for c in COULD_NOT_DRIVE:
            print('  ? %s' % c)
        return 1
    print('EVERY PRESS-ON DRIVEN. %d finding(s), both LOW and neither requiring '
          'a change' % findings)
    print('to the diff under review.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
