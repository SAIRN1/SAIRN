#!/usr/bin/env python
# OWNER: cody
"""Sabotage control for the SCOPE of tools/blob_conversion_coverage.py.

── WHY THIS EXISTS: THE MOST OVERDUE TIER A DISCHARGE ──────────────────────
`docs/tier-a-reviews.json` carries an obligation opened by **fourth** at
2026-09-26T18:53:22Z over `api/sd-data.js`, `api/sd-sub-data.js`,
`tools/blob_conversion_coverage.py` and its probe -- *"11 stored-blob writes
converted to storedBlob() from api/_lib/blob.js"*. **236 hours open**, assigned
to `cloud`, a session `sairn_status.py` reports DEAD, and past the 48h takeover
window.

Discharging it adversarially means asking what would make its coverage number
WRONG rather than whether the eleven conversions happened.

── THE ATTACK POINT, READ OUT OF THE CODE ──────────────────────────────────
`api_files()` enumerates with `os.listdir(API)` and filters on `.endswith('.js')`.
**`os.listdir` IS FLAT.** Every file in an `api/` SUBDIRECTORY is outside the
universe, and the tool reports a coverage figure without saying so.

MEASURED 2026-10-06 at HEAD:

    api/*.js        non-test  : 49 files, 461 `data:`+license_hash sites
    api/**/ subdir  non-test  : 124 files,  10 `data:`+license_hash sites
                                            ^^ INVISIBLE TO THE TOOL

**TWO OF THE TEN ARE BOUND VARIABLES, NOT `storedBlob(...)`:**

    api/_lib/sd-store.js:166                     data: slab,
    api/sairndental/public-complaint-submit.js:136   data: data,

`writeSlab()` POSTs to `sd_slabs` with `slab_id: String(slab.id)` as a COLUMN
and `data: slab` unstripped beside it -- **`id` duplicated into the blob, which
is the exact shape `storedBlob(rec, ['id'])` exists to remove.**

**THIS IS A SCOPE DEFECT, NOT A CLASSIFIER DEFECT, AND S3 BELOW PROVES WHICH.**
The classifier would have reported those sites correctly; it was never given
them. Reporting "the classifier is broken" would be the wrong finding, and the
difference is what tells fourth where to fix it.

REPORT ONLY. Reads the repo and hand-built strings; writes nothing.
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import blob_conversion_coverage as B                            # noqa: E402

_pass, _fail, _found = 0, 0, []


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


print('BLOB COVERAGE SCOPE -- sabotage control for api_files()')
print('  subject : tools/blob_conversion_coverage.py  api_files()')
print('  for     : tier-a-reviews.json, fourth, 2026-09-26T18:53:22Z (236h)')
print()

scanned = set(os.path.abspath(p) for p in B.api_files())
api = os.path.join(REPO, 'api')
on_disk = set()
for root, _dirs, files in os.walk(api):
    for n in files:
        if n.endswith('.js') and not n.endswith('.test.js'):
            on_disk.add(os.path.abspath(os.path.join(root, n)))
missed = sorted(on_disk - scanned)

# ── S0, THE PAIRED POSITIVE, FIRST ──────────────────────────────────────────
# If api_files() returned nothing, S1 would "pass" against a tool that scans
# nothing at all, and this control would discharge a 236h obligation on a
# measurement of zero.
check('S0. PAIRED POSITIVE: api_files() returns a non-empty set of real files, '
      'so the arms below are measuring a scope GAP and not a dead function',
      len(scanned) > 10 and all(os.path.isfile(p) for p in scanned),
      'scanned=%d' % len(scanned))

check('S1. ATTACK POINT -- every non-test api/**/*.js on disk is INSIDE the '
      'scanned universe. os.listdir() is flat, so a subdirectory write is '
      'outside the coverage figure without the figure saying so',
      not missed,
      '%d file(s) on disk and NOT scanned, e.g. %s'
      % (len(missed), [os.path.relpath(p, REPO).replace(os.sep, '/')
                       for p in missed[:4]]))
if missed:
    _found.append(
        'SCOPE: api_files() uses os.listdir(api) -- FLAT -- so %d non-test '
        '.js files in api/ subdirectories are outside the coverage universe. '
        'The reported figure is a floor and does not say so.' % len(missed))

# ── S2. AND THE GAP IS NOT EMPTY: real `data:` write sites live out there ───
DATA_SITES = [
    ('api/_lib/sd-store.js', 166, 'slab'),
    ('api/sairndental/public-complaint-submit.js', 136, 'data'),
]
unseen = []
for rel, ln, expr in DATA_SITES:
    p = os.path.join(REPO, rel.replace('/', os.sep))
    if not os.path.isfile(p):
        continue
    line = io.open(p, encoding='utf-8', errors='replace').read().split('\n')[ln - 1]
    if 'data:' in line and 'storedBlob(' not in line:
        unseen.append((rel, ln, line.strip()[:70]))
check('S2. ...and the unscanned region is NOT EMPTY -- it holds `data:` writes '
      'whose expression is a BOUND VARIABLE rather than storedBlob(), which is '
      'the gap this tool exists to count',
      not unseen,
      'unclassified: %s' % (unseen,))
if unseen:
    _found.append(
        'LIVE: %d `data:` write site(s) outside the universe bind a plain '
        'variable, not storedBlob() -- %s. api/_lib/sd-store.js writeSlab() '
        'also puts slab_id as a COLUMN beside the unstripped blob, so `id` is '
        'duplicated: the exact shape storedBlob(rec, [\'id\']) removes.'
        % (len(unseen), [u[0] + ':' + str(u[1]) for u in unseen]))

# ── S3. WHICH HALF IS BROKEN -- scope, or the classifier? ──────────────────
# This is the arm that makes the finding ACTIONABLE. If the classifier would
# mis-score these expressions too, the fix is in classify(); if it scores them
# correctly, the fix is in api_files() alone.
def _no_binding(_name, _at):
    return None


kinds = {e: B.classify(e, 0, _no_binding) for e in ('slab', 'data', 'payload',
                                                    "storedBlob(rec, ['id'])")}
check('S3. THE CLASSIFIER IS NOT THE DEFECT: it still scores a converted '
      'expression CONVERTED and a bare `payload` RAW, so the fix belongs in '
      'api_files() and NOT in classify()',
      kinds["storedBlob(rec, ['id'])"] == 'CONVERTED' and kinds['payload'] == 'RAW',
      kinds)
check('S3b. ...and a bound name with no resolvable binding falls to BUILT, '
      'which is why these sites would read as BUILT rather than RAW even once '
      'in scope -- a SECOND, narrower finding for fourth, not a reason to '
      'widen nothing',
      kinds['slab'] == 'BUILT' and kinds['data'] == 'BUILT', kinds)

print()
if _found:
    print('FINDINGS (%d) -- against tools/blob_conversion_coverage.py, which is '
          'NOT mine:' % len(_found))
    for f in _found:
        print('  ! %s' % f)
    print()
    print('WHAT THIS DOES AND DOES NOT SAY ABOUT THE OBLIGATION. It does NOT '
          'show the eleven\nconversions were wrong -- they are in '
          'api/sd-data.js and api/sd-sub-data.js, both\nscanned, and the '
          'classifier handles them. It shows THE COVERAGE NUMBER IS A FLOOR\n'
          'OVER A UNIVERSE NARROWER THAN THE CODE, with at least two '
          'unconverted-shaped\nwrites outside it, so the obligation cannot be '
          'discharged as "coverage proven".')
else:
    print('NO FINDINGS -- the scanned universe equals the non-test .js files on '
          'disk.')

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
