#!/usr/bin/env python
# OWNER: cody
# written 2026-10-16, batch b19, item 1
r"""ABLATION: does arm Z of tests/sd_data_blob_scope_ten_routed_sites.js FIRE?

    python docs/b19-logs/ablate_arm_z.py

Exit 0 the ablation was CAUGHT (arm Z went red), 1 it was SILENT, 2 COULD NOT
RUN. Committed rather than run once and described, following the b16 precedent
(docs/b16-logs/ablate_floor_layers.py): an ablation nobody can re-run is a
sentence, not a measurement.

── WHY THIS EXISTS ────────────────────────────────────────────────────────
fourth's b25 F1: arm Z read

    if (d.id !== undefined && s.idMustSurvive) { ok('Z ...'); }

with NO `else`. When `id` is missing -- the ONE state the arm exists to catch
-- the arm emitted neither `ok` nor `bad`. It did not go red, IT DISAPPEARED.
fourth ablated the arm itself and measured BASELINE exit 0 / 16 passed / arm Z
present 1 against ABLATED exit 0 / 15 passed / arm Z present 0, so a
"correct-looking scope fix" that stripped `id` off every blob would have been
exit 0 either way. fourth's instruction was: add the `else bad(...)` and RE-RUN
THE ABLATION -- the arm does not count until it comes back RED.

── WHAT IS ABLATED, AND IT IS THE SUBJECT, NOT THE ARM ────────────────────
Removing the ARM can only ever reduce the arm count; it cannot make the arm
red, and measuring that again would only re-prove fourth's finding. The
ablation that answers "does arm Z fire" removes the PROPERTY arm Z asserts:
in a COPY of api/, the sd_slabs write branch becomes

    data: storedBlob(payload, ['id'])      <- was storedBlob(payload, [])

which is exactly the plausible scope fix the arm was written to catch --
`api/_lib/blob.js` deletes every key named in the second argument, so `id`
stops reaching the blob while every A arm (no scope key in `data`) still
passes. `sd_slabs`' own read returns `x.data` whole, so every slab record
would come back with no id.

THE LIVE CLONE IS NEVER WRITTEN. api/ is copied to a temp tree and the suite
is pointed at the copy through its own SAIRN_B15_SD_DATA / SAIRN_B15_SD_STORE
injection points, which exist for this.

── MEASURED 2026-10-16, BOTH LEGS, SAME SESSION ───────────────────────────
    PRE-FIX  BASELINE  EXIT=0  16 passed, 0 failed   arm Z ok:1 FAIL:0
    PRE-FIX  ABLATED   EXIT=0  15 passed, 0 failed   arm Z ok:0 FAIL:0  SILENT
    POST-FIX BASELINE  EXIT=0  16 passed, 0 failed   arm Z ok:1 FAIL:0
    POST-FIX ABLATED   EXIT=1  15 passed, 1 failed   arm Z ok:0 FAIL:1  CAUGHT

The PRE-FIX leg reproduces fourth's b25 numbers exactly -- 16/15 and the arm
simply vanishing -- and the POST-FIX leg is this file. **THE PRE-FIX LEG IS
DELIBERATELY NOT COMMITTED.** Committing it would require a literal copy of the
removed one-condition arm to live in the repo, and this repo has already paid
for that shape: in b17 an assertion in tests/sairnbuild_server_wins.js was
satisfied by a COMMENT inside the very function it tested, explaining that the
code "used to read" the string being asserted. A driver carrying the old arm's
source is the same hazard one layer up. The numbers above are the record; the
scratch driver that produced them was
`<scratchpad>/armz_before.py` and it is three lines of substitution over this
file's own text.

── THE CONTROL COMES FIRST ────────────────────────────────────────────────
An UNMUTATED copy must come back exit 0 with arm Z PRESENT AND PASSING. Without
it, "the ablated copy is red" is satisfied for ever by a copy that cannot run
at all -- the suite's own history has two defects of exactly that shape (a
mistyped session header, and mocks resolved from the repo instead of from the
handler under test), both of which made every site fail its PRECONDITION arm.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUITE = os.path.join(REPO, 'tests', 'sd_data_blob_scope_ten_routed_sites.js')
API = os.path.join(REPO, 'api')
TARGET = 'data: storedBlob(payload, []), updated_at: nowISO()'
ABLATED = "data: storedBlob(payload, ['id']), updated_at: nowISO()"
SLAB_GUARD = "if (resource === 'slabs' && action === 'write') {"


def die(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(2)


for p in (SUITE, API):
    if not os.path.exists(p):
        die('%s is absent.' % p)

src = io.open(os.path.join(API, 'sd-data.js'), encoding='utf-8').read()
# THE ANCHOR IS CHECKED FOR UNIQUENESS IN ITS OWN BRANCH, not globally. The
# `storedBlob(payload, [])` spelling occurs on several branches, so a global
# replace would ablate more than one site and the result would not be
# attributable to sd_slabs. The window is bounded by the NEXT branch guard, not
# by a character count.
g = src.find(SLAB_GUARD)
if g < 0:
    die('%r was not found in api/sd-data.js, so the sd_slabs write branch '
        'could not be located. Re-anchor this ablation rather than letting it '
        'mutate some other branch.' % SLAB_GUARD)
nxt = src.find("\n    if (resource === '", g + len(SLAB_GUARD))
if nxt < 0:
    die('the end of the sd_slabs write branch could not be found.')
branch = src[g:nxt]
n = branch.count(TARGET)
if n != 1:
    die('%r occurs %d times inside the sd_slabs write branch (expected 1), so '
        'the mutation would not be a single clean ablation.' % (TARGET, n))

work = tempfile.mkdtemp(prefix='b19-armz-')
rc = 2
try:
    for tag, mutate in (('BASELINE', False), ('ABLATED', True)):
        tree = os.path.join(work, tag.lower())
        shutil.copytree(API, tree)
        if mutate:
            out = src[:g] + branch.replace(TARGET, ABLATED, 1) + src[nxt:]
            io.open(os.path.join(tree, 'sd-data.js'), 'w', encoding='utf-8',
                    newline='\n').write(out)
        env = dict(os.environ,
                   SAIRN_B15_SD_DATA=os.path.join(tree, 'sd-data.js'),
                   SAIRN_B15_SD_STORE=os.path.join(tree, '_lib', 'sd-store.js'))
        r = subprocess.run(['node', SUITE], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', cwd=REPO,
                           env=env)
        o = (r.stdout or '') + (r.stderr or '')
        zok = len(re.findall(r'^  ok   Z \(', o, re.M))
        zbad = len(re.findall(r'^  FAIL Z \(', o, re.M))
        m = re.search(r'^(\d+) passed, (\d+) failed', o, re.M)
        counts = (m.group(1), m.group(2)) if m else ('?', '?')
        print('  %-9s EXIT=%-3s %s passed, %s failed   arm Z ok:%d FAIL:%d'
              % (tag, r.returncode, counts[0], counts[1], zok, zbad))
        if tag == 'BASELINE':
            if r.returncode != 0 or zok != 1 or zbad:
                print('\nCONTROL FAILED: the UNMUTATED copy must be exit 0 '
                      'with arm Z present and passing. It is not, so nothing '
                      'below is attributable to the ablation.')
                print(o[-1500:])
                sys.exit(2)
        else:
            if r.returncode == 1 and zbad == 1 and zok == 0:
                print('\nCAUGHT. Stripping `id` in the sd_slabs branch makes '
                      'arm Z RED (exit 1), where before the `else` was added '
                      'the same ablation was exit 0 with the arm simply '
                      'absent. The arm fires.')
                rc = 0
            else:
                print('\nSILENT. The ablation did NOT turn arm Z red, so the '
                      'arm still does not count.')
                print(o[-1500:])
                rc = 1
finally:
    shutil.rmtree(work, ignore_errors=True)
sys.exit(rc)
