#!/usr/bin/env python
# OWNER: cody
# written 2026-10-19, batch b23, item 4
r"""ABLATION: do b23's sweep repairs actually bite?

    python docs/b23-logs/ablate_sweep_fixes.py

Exit 0 every mutation REFUSED, 1 one or more ACCEPTED, 2 COULD NOT RUN.

Two suites were repaired after the green-but-worthless sweep
(docs/b23-logs/green_but_worthless_sweep.py):

  tests/sairndental_amount_construction.js   MONEY. Its section-2 arms were
      substring and ORDERING tests over a raw function body, so a comment
      naming dntBadAmount above the real newId() satisfied the ordering arm
      while the real refusal sat below it -- a charge record minted with an
      amount the app had already decided it could not read.
  tests/sairndental_rollup_panel.js          TIER A PHI panel reachability.
      Its wiring arms read raw `html`, so a commented-out panel div, a
      commented-out sidebar button and a JS comment carrying nav()'s dispatch
      each satisfied them -- the exact unreachable state the suite exists for.

FIVE OF THE SEVEN MUTATIONS WERE ACCEPTED BEFORE THE REPAIR -- A1, R1, R2, R3,
R4 -- and A2 and A3 are CONTROLS that already bit. Run with `--before` to see
it: the identical mutations are driven against the suites taken out of git, so
that sentence is a differential and not a claim. It matters because an ablation
whose mutations were always caught proves nothing about the change that just
landed, and the first version of this file asserted all seven without having
measured any of them.

THE CONTROL COMES FIRST. An unmutated copy must come back exit 0 at the
baseline arm count, or nothing below is attributable to a mutation.

THE LIVE CLONE IS NEVER WRITTEN: sairndental.html is copied to a temp tree
with the layout each suite expects (ROOT/sairndental.html, ROOT/tests/x.js).
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
APP_REL = 'sairndental.html'
APP = os.path.join(REPO, APP_REL)

REAL_REFUSAL = "  if(amt===null) return dntBadAmount('charge');\n"
REAL_MINT = "  var rec={id:newId('CH'),"

CASES = [
    # (suite, name, what, old, new)
    ('tests/sairndental_amount_construction.js', 'A1',
     'the refusal moved BELOW newId(), a COMMENT left above it',
     REAL_REFUSAL + "  var pt=patients()",
     "  // if(amt===null) return dntBadAmount('charge');\n  var pt=patients()"),
    ('tests/sairndental_amount_construction.js', 'A2',
     'the refusal DELETED outright (control)',
     REAL_REFUSAL,
     ''),
    ('tests/sairndental_amount_construction.js', 'A3',
     'the parse replaced by Number(amount)||0, a COMMENT keeps the old text',
     "  var amt=dntMoneyIn(amount);\n" + REAL_REFUSAL,
     "  var amt=Number(amount)||0;\n  /* was: var amt=dntMoneyIn(amount); "
     "if(amt===null) return dntBadAmount('charge'); */\n"),

    ('tests/sairndental_rollup_panel.js', 'R1',
     'the real sdnData read deleted, a COMMENT carries dnt_rollup',
     "  var b=await sdnData('read','dnt_rollup',{});",
     "  // var b=await sdnData('read','dnt_rollup',{});\n  var b=null;"),
    ('tests/sairndental_rollup_panel.js', 'R2',
     "nav()'s dispatch commented out, the COMMENT carries it",
     "  if(id==='rollup')rRollup();",
     "  // if(id==='rollup')rRollup();"),
    # ── R3 AND R4 ARE SINGLE-LAYER, AND THE FIRST VERSIONS WERE NOT ────────
    # They commented the element out AND renamed the live one
    # (`panel-rollup-disabled`, `sb-rollup-off`). Driven against the
    # PRE-REPAIR suites both came back REFUSED -- by the census arm catching
    # the RENAME, not by anything noticing the comment. A mutation that
    # changes two things cannot attribute a refusal to either, which is
    # exactly the error cross-domain item 12 is about, committed inside the
    # ablation written to honour it. Now the element is commented out and
    # NOTHING else changes.
    ('tests/sairndental_rollup_panel.js', 'R3',
     'the panel div commented out with an HTML comment carrying its id',
     '      <div class="panel" id="panel-rollup">',
     '      <!-- <div class="panel" id="panel-rollup"> -->'),
    ('tests/sairndental_rollup_panel.js', 'R4',
     'the sidebar button commented out, the comment carrying its id',
     '      <button class="sb" id="sb-rollup" onclick="nav(\'rollup\')"><span class="sico">&#127970;</span>Office Roll-Up</button>',
     '      <!-- <button class="sb" id="sb-rollup" onclick="nav(\'rollup\')"><span class="sico">&#127970;</span>Office Roll-Up</button> -->'),
]


def die(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(2)


BEFORE = '--before' in sys.argv
BEFORE_REF = 'HEAD'


def suite_source(suite_rel):
    """The repaired suite, or -- with --before -- the one at HEAD.

    `--before` is how the closing claim of this file is MEASURED rather than
    asserted: the identical mutations are driven against the PRE-REPAIR
    suites taken out of git, so "every one of these was accepted before" is a
    differential and not a sentence. It needs the repair to be uncommitted or
    BEFORE_REF moved to the commit before it.
    """
    if not BEFORE:
        return io.open(os.path.join(REPO, suite_rel), encoding='utf-8',
                       errors='replace').read()
    r = subprocess.run(['git', 'show', BEFORE_REF + ':' + suite_rel],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        die('git show %s:%s failed: %s' % (BEFORE_REF, suite_rel,
                                           (r.stderr or '').strip()))
    return r.stdout


def run(suite_rel, old, new):
    work = tempfile.mkdtemp(prefix='b23-sweep-')
    try:
        os.makedirs(os.path.join(work, 'tests'))
        src = io.open(APP, encoding='utf-8', newline='').read()
        if old is not None:
            n = src.count(old)
            if n != 1:
                return (None, None, None, [],
                        'anchor occurs %d times, expected 1 -- NOT APPLIED' % n)
            src = src.replace(old, new, 1)
        io.open(os.path.join(work, APP_REL), 'w', encoding='utf-8',
                newline='').write(src)
        io.open(os.path.join(work, suite_rel), 'w', encoding='utf-8',
                newline='\n').write(suite_source(suite_rel))
        # tests/sairndental_amount_construction.js also require()s
        # api/_lib/safe-number.js -- it compares dntMoneyIn against the shared
        # measureNumber. THE CONTROL CAUGHT THIS, which is the whole reason it
        # runs first: without the copy the baseline was exit 1 and every
        # "REFUSED" below would have been a copy that could not run.
        lib = os.path.join(REPO, 'api', '_lib')
        if os.path.isdir(lib):
            shutil.copytree(lib, os.path.join(work, 'api', '_lib'))
        r = subprocess.run(['node', os.path.join(work, suite_rel)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=work)
        o = (r.stdout or '') + (r.stderr or '')
        # ANCHORED to each suite's own summary line. An unanchored count regex
        # reads the number out of an assertion's own failure text, which is
        # how b23's first ablation harness reported six false ACCEPTEDs.
        m = re.search(r'^ALL (\d+) .* PASS$', o, re.M)
        reds = re.findall(r'^  FAIL (.+)$', o, re.M)
        return (r.returncode, int(m.group(1)) if m else None, None, reds, o)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if not os.path.isfile(APP):
    die('%s is absent.' % APP_REL)
for s in sorted(set(c[0] for c in CASES)):
    if not os.path.isfile(os.path.join(REPO, s)):
        die('%s is absent.' % s)

print('ABLATION -- b23 sweep repairs, on a COPY. Live clone never written.')
if BEFORE:
    print('  --before: the suites are taken from %s, i.e. PRE-REPAIR. Every '
          'case below is EXPECTED to be ACCEPTED; that is the measurement '
          'this file\'s closing claim rests on.' % BEFORE_REF)
print('')

base = {}
for suite in sorted(set(c[0] for c in CASES)):
    rc, p, _f, reds, o = run(suite, None, None)
    print('  CTRL %-10s %-52s exit=%-3s %s arms pass'
          % ('', suite, rc, p))
    if rc != 0 or not p:
        print('')
        print('CONTROL FAILED for %s. Nothing below is attributable.' % suite)
        print(o[-1500:])
        sys.exit(2)
    base[suite] = p
print('')

accepted, refused, notapplied = [], [], []
for suite, name, what, old, new in CASES:
    rc, p, _f, reds, o = run(suite, old, new)
    if rc is None:
        print('  %-4s %-62s %s' % (name, what[:62], reds or o))
        notapplied.append(name)
        continue
    if rc != 0 and reds:
        verdict = 'REFUSED'
        refused.append(name)
    else:
        verdict = '*** ACCEPTED -- THE LAYER IS UNPROTECTED ***'
        accepted.append(name)
    print('  %-4s %-62s exit=%-3s %s' % (name, what[:62], rc, verdict))
    for rn in reds[:2]:
        print('         red arm: %s' % rn.strip()[:92])

print('')
print('%d REFUSED, %d ACCEPTED, %d not applied'
      % (len(refused), len(accepted), len(notapplied)))
if accepted:
    print('ACCEPTED (unprotected): %s' % ', '.join(accepted))
print('')
print('MEASURED BOTH LEGS, SAME SESSION, with --before and without:')
print('  PRE-REPAIR  (suites from git)  5 ACCEPTED, 2 REFUSED')
print('              ACCEPTED: A1, R1, R2, R3, R4')
print('              REFUSED : A2, A3  -- CONTROLS, already caught')
print('  POST-REPAIR (suites on disk)   0 ACCEPTED, 7 REFUSED')
print('')
print('FIVE of the seven were ACCEPTED before b23 repaired the two suites,')
print('NOT all seven -- and the first version of this script claimed all')
print('seven without having measured it. A2 and A3 are controls that already')
print('bit; their refusing in BOTH legs is what makes A1 attributable to the')
print('repair rather than to the mutation being a careless one.')
sys.exit(1 if (accepted or notapplied) else 0)
