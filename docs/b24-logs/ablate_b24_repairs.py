#!/usr/bin/env python
# OWNER: cody
# written 2026-10-19, batch b24
r"""ABLATION: do b24's two repairs bite, and did they bite before?

    python docs/b24-logs/ablate_b24_repairs.py            POST-REPAIR leg
    python docs/b24-logs/ablate_b24_repairs.py --before    PRE-REPAIR leg

Exit 0 every mutation REFUSED, 1 one or more ACCEPTED, 2 COULD NOT RUN.
`--before` is EXPECTED to exit 1: it takes the suites out of git and drives the
identical mutations, so "these were accepted before the repair" is a
differential and not a sentence. b23 shipped an ablation whose closing claim
had measured nothing and it was wrong by two; this file exists in both legs
from the start.

── WHAT IS ABLATED ─────────────────────────────────────────────────────────
ITEM 1, sairnroofing.html + api/: Michael's decision that the default-location
answer comes from the SERVER -- `is_default` per row -- rather than from two
hardcoded 'LOC-DEFAULT' comparisons in the client. api/_lib/location-scope.js
added isDefaultLocation() FOR those two sites and they could not reach it: that
module is CommonJS and the app is a single HTML file with no loader and no
build step. Arm E passed for weeks and proved the function WORKS, not that
anything USES it.

ITEM 2, sairnlaw.html: the ordering that makes a double-press on the
Outstanding button harmless -- st() and rTrust() both run BEFORE the await, so
the re-render removes the button before a second click can be delivered. The
only place it was recorded was a REPORT-ONLY probe that printed the fact and
exited 0 whatever it found, and which computed it over RAW text with three bare
indexOf calls.

── THE CONTROL COMES FIRST ─────────────────────────────────────────────────
An unmutated copy must come back exit 0 for every suite, or nothing below is
attributable. b23's first run of its own ablation FAILED ITS CONTROL because a
suite required a file the temp tree did not carry -- without the control, every
"REFUSED" after it would have been a copy that could not run.

── SINGLE-LAYER MUTATIONS ──────────────────────────────────────────────────
Each case changes ONE thing. b23's first R3/R4 commented an element out AND
renamed the live one, and both came back REFUSED pre-repair -- by a different
arm catching the RENAME. A mutation that changes two things cannot attribute a
refusal to either.

THE LIVE CLONE IS NEVER WRITTEN: the app and api/ are copied to a temp tree.
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

BEFORE = '--before' in sys.argv
BEFORE_REF = 'HEAD'

# (suite, app_file, name, what, old, new)
CASES = [
    # ── ITEM 1 ────────────────────────────────────────────────────────────
    ('api/_lib/location-scope.test.js', None, 'L1',
     'the sentinel re-typed into sairnroofing.html EXECUTABLE code',
     ('sairnroofing.html',
      "  if(!id)return true;                      /* absent IS the implicit default */",
      "  if(!id)return true;\n  if(id==='LOC-DEFAULT')return true;")),
    ('api/_lib/location-scope.test.js', None, 'L2',
     'CONTROL: the sentinel in a COMMENT only -- must stay GREEN',
     ('sairnroofing.html',
      "function rfIsDefaultLoc(id){",
      "/* a note mentioning LOC-DEFAULT, which is not code */\nfunction rfIsDefaultLoc(id){")),
    ('tests/sairnroofing_default_location_from_server.js', None, 'L3',
     "the row's is_default ignored, the response id compared instead",
     ('sairnroofing.html',
      "      return typeof rfLocations[i].is_default==='boolean'?rfLocations[i].is_default:null;",
      "      return rfDefaultLocId===null?null:id===rfDefaultLocId;")),
    ('tests/sairnroofing_default_location_from_server.js', None, 'L4',
     'UNKNOWN collapsed into false -- a guess presented as an answer',
     ('sairnroofing.html',
      "  return rfDefaultLocId===null?null:id===rfDefaultLocId;\n}",
      "  return id===rfDefaultLocId;\n}")),
    ('tests/sairnroofing_default_location_from_server.js', None, 'L5',
     'the call site switched to a TRUTHINESS test, so null reads as not-default',
     ('sairnroofing.html',
      "el.value=(selected&&rfIsDefaultLoc(selected)!==true)?selected:'';",
      "el.value=(selected&&!rfIsDefaultLoc(selected))?selected:'';")),
    ('tests/sairnroofing_default_location_from_server.js', None, 'L6',
     'rfLoadLocations stops capturing default_location_id off the response',
     ('sairnroofing.html',
      "    if(r.ok&&r.data&&typeof r.data.default_location_id==='string')rfDefaultLocId=r.data.default_location_id;",
      "    rfDefaultLocId='LOC-DEFAULT';")),

    # ── ITEM 2 ────────────────────────────────────────────────────────────
    ('tests/sairnlaw_trust_clearance.js', None, 'T1',
     'rTrust() MOVED AFTER the await -- the named edit to watch',
     ('sairnlaw.html',
      "  st('law_trusttx',list);\n  rTrust();\n  var syncResult=await sdnData('write','law_trusttx',t);",
      "  st('law_trusttx',list);\n  var syncResult=await sdnData('write','law_trusttx',t);\n  rTrust();")),
    ('tests/sairnlaw_trust_clearance.js', None, 'T2',
     'the local write MOVED AFTER the await',
     ('sairnlaw.html',
      "  st('law_trusttx',list);\n  rTrust();\n  var syncResult=await sdnData('write','law_trusttx',t);",
      "  rTrust();\n  var syncResult=await sdnData('write','law_trusttx',t);\n  st('law_trusttx',list);")),
    ('tests/sairnlaw_trust_clearance.js', None, 'T3',
     'rTrust() moved after the await, a COMMENT left before it carrying the call',
     ('sairnlaw.html',
      "  st('law_trusttx',list);\n  rTrust();\n  var syncResult=await sdnData('write','law_trusttx',t);",
      "  st('law_trusttx',list);\n  /* rTrust(); used to run here */\n  var syncResult=await sdnData('write','law_trusttx',t);\n  rTrust();")),
    ('tests/sairnlaw_trust_clearance.js', None, 'T4',
     'the local write DELETED outright -- an absent anchor is not "in order"',
     ('sairnlaw.html',
      "  st('law_trusttx',list);\n  rTrust();",
      "  rTrust();")),
    ('tests/sairncode_pt_gp_modifier.js', None, 'S1',
     'the pt-gp input commented out, the HTML comment carrying its id',
     ('sairncode.html', 'id="pt-gp"', '<!-- id="pt-gp" -->')),
    ('tests/sairncode_pt_gp_modifier.js', None, 'S2',
     "runPtCheck's read commented out, a COMMENT carrying it",
     ('sairncode.html',
      "gp_applied_codes: scParseList(document.getElementById('pt-gp').value)",
      "/* gp_applied_codes: scParseList(document.getElementById('pt-gp').value) */ gp_applied_codes: []")),
]

APP_DEPS = ('sairnroofing.html', 'sairnlaw.html', 'sairndental.html',
            'sairncode.html')


def die(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(2)


def suite_source(rel):
    if not BEFORE:
        return io.open(os.path.join(REPO, rel), encoding='utf-8',
                       errors='replace').read()
    r = subprocess.run(['git', 'show', BEFORE_REF + ':' + rel], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        # A suite that did not exist before the repair cannot be driven in the
        # PRE leg. That is reported, never silently skipped.
        return None
    return r.stdout


def app_source(rel):
    """The app file. ALWAYS from disk, in BOTH legs, and that is the design.

    The PRE leg's question is "would the OLD SUITE have caught this mutation",
    so the subject must be the same in both legs; taking the app from git too
    would change two things at once and make a refusal unattributable.
    """
    return io.open(os.path.join(REPO, rel), encoding='utf-8',
                   newline='').read()


def run(suite_rel, mutation):
    work = tempfile.mkdtemp(prefix='b24-')
    try:
        src = suite_source(suite_rel)
        if src is None:
            return (None, [], 'the suite does not exist at %s -- NOT DRIVEN'
                    % BEFORE_REF)
        for sub in ('tests', os.path.join('api', '_lib')):
            os.makedirs(os.path.join(work, sub), exist_ok=True)
        # ── ORDER MATTERS AND THE FIRST VERSION HAD IT WRONG ────────────────
        # api/_lib is copied WHOLESALE because these suites require() modules
        # out of it (b23's control caught that being absent). But the first
        # version wrote the suite FIRST and then copytree'd api/_lib OVER it --
        # so for any suite that LIVES inside api/_lib, the `--before` leg
        # silently drove the DISK copy and reported a pre-repair measurement it
        # had never taken. Measured: L1 came back REFUSED in the PRE leg with
        # arm F named, and arm F does not exist at HEAD.
        #
        # THE LIBRARY GOES DOWN FIRST, THE SUITE GOES ON TOP, AND THE RESULT IS
        # VERIFIED. A silent clobber is exactly the class this whole batch is
        # about, committed inside the tool measuring it -- the third time in two
        # batches, so it gets an assertion rather than a careful ordering.
        lib = os.path.join(REPO, 'api', '_lib')
        if os.path.isdir(lib):
            shutil.rmtree(os.path.join(work, 'api', '_lib'), ignore_errors=True)
            shutil.copytree(lib, os.path.join(work, 'api', '_lib'))
        dst = os.path.join(work, suite_rel)
        io.open(dst, 'w', encoding='utf-8', newline='\n').write(src)
        back = io.open(dst, encoding='utf-8', errors='replace').read()
        if back != src:
            return (None, [], 'the suite on disk in the temp tree is NOT the '
                    'source this leg asked for -- something overwrote it, so '
                    'the result would be about the wrong file. NOT DRIVEN')
        for a in APP_DEPS:
            p = os.path.join(REPO, a)
            if not os.path.isfile(p):
                continue
            text = app_source(a)
            if mutation is not None and mutation[0] == a:
                old, new = mutation[1], mutation[2]
                n = text.count(old)
                if n != 1:
                    return (None, [], 'anchor occurs %d times in %s, expected 1'
                            ' -- MUTATION NOT APPLIED' % (n, a))
                text = text.replace(old, new, 1)
            io.open(os.path.join(work, a), 'w', encoding='utf-8',
                    newline='').write(text)
        r = subprocess.run(['node', os.path.join(work, suite_rel)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=work)
        o = (r.stdout or '') + (r.stderr or '')
        reds = re.findall(r'^(?:  FAIL |FAIL |✖ |not ok )(.+)$', o, re.M)
        if 'COULD NOT RUN' in o:
            reds.append('COULD NOT RUN (third state, counted as a refusal '
                        'only if the exit code is non-zero)')
        return (r.returncode, reds, '')
    finally:
        shutil.rmtree(work, ignore_errors=True)


print('ABLATION -- b24 repairs, on a COPY. Live clone never written.')
if BEFORE:
    print('  --before: suites taken from %s (PRE-REPAIR). Cases are EXPECTED '
          'to be ACCEPTED; that is the differential.' % BEFORE_REF)
print('')

suites = []
for c in CASES:
    if c[0] not in suites:
        suites.append(c[0])

for s in suites:
    rc, reds, note = run(s, None)
    if rc is None:
        print('  CTRL %-56s %s' % (s, note))
        continue
    print('  CTRL %-56s exit=%s' % (s, rc))
    if rc != 0:
        print('')
        print('CONTROL FAILED for %s -- nothing below is attributable.' % s)
        for r_ in reds[:6]:
            print('    red: %s' % r_[:100])
        sys.exit(2)
print('')

accepted, refused, notdriven = [], [], []
for suite_rel, _unused, name, what, mutation in CASES:
    rc, reds, note = run(suite_rel, mutation)
    if rc is None:
        print('  %-3s %-58s %s' % (name, what[:58], note))
        notdriven.append(name)
        continue
    control = name in ('L2',)
    if control:
        ok = (rc == 0)
        verdict = 'GREEN (correct for a control)' if ok \
            else '*** RED -- the control broke ***'
        (refused if ok else accepted).append(name)
    elif rc != 0 and reds:
        verdict = 'REFUSED'
        refused.append(name)
    else:
        verdict = '*** ACCEPTED -- THE LAYER IS UNPROTECTED ***'
        accepted.append(name)
    print('  %-3s %-58s exit=%-3s %s' % (name, what[:58], rc, verdict))
    for r_ in reds[:2]:
        print('        red arm: %s' % r_.strip()[:92])

print('')
print('%d as expected, %d NOT, %d not driven'
      % (len(refused), len(accepted), len(notdriven)))
if accepted:
    print('UNEXPECTED: %s' % ', '.join(accepted))
if notdriven:
    print('NOT DRIVEN (suite absent at %s): %s'
          % (BEFORE_REF, ', '.join(notdriven)))
print('')
print('L2 IS A CONTROL AND MUST STAY GREEN IN BOTH LEGS: a comment mentioning')
print('the sentinel is not a client copy of it, and an arm that flagged the')
print('note documenting its own repair is a defect this repo has paid for.')
sys.exit(1 if (accepted or notdriven) else 0)
