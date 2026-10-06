#!/usr/bin/env python
# OWNER: cody
"""Sabotage control for the ANCHORED-VIA hop graph in
tools/citation_line_drift_check.py.

── WHY THIS EXISTS: A TIER A DISCHARGE, NOT A NEW FEATURE ───────────────────
`docs/tier-a-reviews.json` carries an OPEN obligation opened by **hank** at
2026-10-05T21:33:08Z over `tools/citation_line_drift_check.py`, resource
`sd_comms`. Discharging it adversarially means asking what would make its
verdict WRONG, not whether it runs.

The verdict under review, driven at HEAD
(`--app stonedesk.html --prefix sd_`):

    ANCHORED-VIA sd_comms  :10582   load() at :10526 reaches it in 2 hop(s)
    ANCHORED-VIA sd_comms  :10618   load() at :10526 reaches it in 2 hop(s)
    ANCHORED-VIA sd_comms  :10649   load() at :10526 reaches it in 2 hop(s)
    DRIFTED      sd_comms  :10483 -> :10527  offset +44

**THREE OF THE FOUR sd_comms VERDICTS REST ENTIRELY ON THE HOP GRAPH**, and
`tests/run_citation_line_drift_probe.py` — 22 arms, exit 0, and a good probe —
**has no arm for it.** Its G2/G3 pair covers the wrong-file attack, A1/A2 cover
declaration spans, E2/F2/F3 cover the drift arrow. The hop graph is the
uncovered half carrying most of this resource's answer.

── THE TWO ATTACK POINTS, READ OUT OF THE CODE ─────────────────────────────
`anchor_verdict()` walks `_CALL_RE` matches, finds each name's nearest
definition with `_nearest_def()`, then reads `_body_lines()` and asks
`_direct_line()` of each line.

  AP1. `_direct_line()` IS A SUBSTRING TEST OVER RAW LINES. It returns True for
       `'sd_comms'` or a storage-constant name appearing ANYWHERE in the line --
       including inside a `//` comment or a string literal. A function whose
       body merely MENTIONS the resource in prose would be credited with
       reaching it.
  AP2. `_body_lines()` IS A FLAT 60-LINE WINDOW, not a braced body, and its own
       docstring says so deliberately. A short function defined immediately
       before one that really does touch the resource has that neighbour inside
       its window, so the WRONG function can be credited.

Each attack point gets an arm below. **S3 is the paired positive** -- a real
call chain that MUST still anchor -- so a tool that simply stopped anchoring
cannot pass S1 and S2.

REPORT ONLY. Writes nothing, reads nothing but hand-built fixtures, and
imports the tool rather than driving the CLI so the verdict is attributable to
`anchor_verdict()` and not to argument handling.
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import citation_line_drift_check as C                           # noqa: E402

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


def verdict(src, cited_line, resource='zz_comms', consts=('K_COMMS',)):
    lines = src.split('\n')
    return C.anchor_verdict(lines, cited_line, resource, list(consts))


print('CITATION ANCHOR HOP -- sabotage control for the ANCHORED-VIA graph')
print('  subject : tools/citation_line_drift_check.py  anchor_verdict()')
print('  for     : tier-a-reviews.json open obligation, hank, '
      '2026-10-05T21:33:08Z, sd_comms')
print()

# ── S3 FIRST, THE PAIRED POSITIVE, AND MY FIRST VERSION OF IT WAS WRONG ────
# It put the definition AFTER the call site, and the arm failed -- correctly.
# `_nearest_def()` searches BACKWARD ONLY (`range(before-1, -1, -1)`), so a
# hoisted declaration below its call site is invisible to it. THAT IS RECORDED
# AS A COVERAGE LIMIT BELOW rather than quietly worked around, and the fixtures
# are now ordered definition-then-call so every sabotage arm is measuring the
# substring question it claims to measure and not the ordering one.
#
# Had S3 been omitted, S1/S1b/S2 would have "passed" on a tool that returned
# ('', '') for everything, and this control would have discharged a Tier A
# obligation on nothing.
_REAL = '\n'.join([
    "function realStore() {",
    "  st(K_COMMS, rows);",
    "}",
    "function callerOne() {",
    "  return realStore();",
    "}",
])
k, d = verdict(_REAL, 5)
check('S3. PAIRED POSITIVE: a real one-hop chain DOES anchor, so the sabotage '
      'arms below cannot pass by the tool simply never anchoring',
      k == 'via', (k, d))

# The same chain with the definition BELOW the call -- a hoisted declaration,
# legal JS and common. Recorded as a LIMIT, not a finding: it makes the tool
# MISS an anchor, never invent one, so it cannot turn a stale citation sound.
_HOISTED = '\n'.join([
    "function callerOne() {",
    "  return realStore();",
    "}",
    "function realStore() {",
    "  st(K_COMMS, rows);",
    "}",
])
kh, dh = verdict(_HOISTED, 2)
check('S3b. LIMIT, NOT A FINDING: a definition BELOW its call site does not '
      'anchor, because _nearest_def searches backward only. This loses '
      'anchors; it cannot manufacture one, so it fails SAFE',
      kh != 'via', (kh, dh))

# ── S1. A COMMENT-ONLY MENTION ──────────────────────────────────────────────
_COMMENT = '\n'.join([
    "function mentionsOnly() {",
    "  // K_COMMS is handled by the other module, never here",
    "  return 0;",
    "}",
    "function callerOne() {",
    "  return mentionsOnly();",
    "}",
])
k1, d1 = verdict(_COMMENT, 6)
ok1 = k1 != 'via'
check('S1. ATTACK POINT 1 -- a function body that only MENTIONS the resource '
      'in a `//` comment must NOT be credited with reaching it',
      ok1, 'got kind=%r detail=%r' % (k1, d1))
if not ok1:
    _found.append(
        'AP1 CONFIRMED -- a `//` comment naming the storage constant is enough '
        'for an ANCHORED-VIA. _direct_line() is a substring test over RAW '
        'lines, so prose about a resource reads as access to it. Reported: '
        '%r' % (d1,))

_STRING = '\n'.join([
    "function stringOnly() {",
    "  log('K_COMMS was migrated away from this path');",
    "  return 0;",
    "}",
    "function callerOne() {",
    "  return stringOnly();",
    "}",
])
k1b, d1b = verdict(_STRING, 6)
ok1b = k1b != 'via'
check('S1b. ...and nor must a STRING LITERAL naming it -- the same substring '
      'test, arriving by the other route',
      ok1b, 'got kind=%r detail=%r' % (k1b, d1b))
if not ok1b:
    _found.append(
        'AP1b CONFIRMED -- a string literal naming the storage constant also '
        'yields ANCHORED-VIA. Reported: %r' % (d1b,))

# ── S2. THE FLAT 60-LINE WINDOW SPILLING INTO THE NEIGHBOUR ────────────────
# `shortFn` touches nothing. The function defined immediately after it does
# write the resource, and it sits inside shortFn's 60-line window.
_SPILL = '\n'.join([
    "function shortFn() {",
    "  return 1;",
    "}",
    "function unrelatedNeighbour() {",
    "  st(K_COMMS, rows);",
    "}",
    "function callerOne() {",
    "  return shortFn();",
    "}",
])
k2, d2 = verdict(_SPILL, 8)
ok2 = not (k2 == 'via' and 'shortFn' in (d2 or ''))
check('S2. ATTACK POINT 2 -- the 60-line window must not credit `shortFn()` '
      'for a write that belongs to the function defined AFTER it',
      ok2, 'got kind=%r detail=%r' % (k2, d2))
if not ok2:
    _found.append(
        'AP2 CONFIRMED -- _body_lines() is a flat 60-line window, so a short '
        'function is credited with its NEIGHBOUR access and the report names '
        'the wrong accessor. Reported: %r' % (d2,))

# ── S0. AND THE DIRECT TIER HAS THE SAME SUBSTRING PROBLEM ─────────────────
# Not a hop at all: the cited line itself, in a comment.
_DIRECT_COMMENT = "  // K_COMMS used to be written here, moved in b42d9b36"
k0, d0 = verdict(_DIRECT_COMMENT, 1)
ok0 = k0 != 'direct'
check('S0. the CITED LINE being a comment that names the resource must not '
      'read as "the cited line names the resource" -- the shortest path to the '
      'same substring defect, and the one a stale citation is most likely to '
      'land on',
      ok0, 'got kind=%r detail=%r' % (k0, d0))
if not ok0:
    _found.append(
        'AP0 CONFIRMED -- a COMMENT on the cited line reads as `direct`, so a '
        'citation pointing at a comment about a moved write is reported SOUND. '
        'Reported: %r' % (d0,))

print()
if _found:
    print('FINDINGS (%d) -- against tools/citation_line_drift_check.py, which '
          'is NOT mine:' % len(_found))
    for f in _found:
        print('  ! %s' % f)
    print()
    print('WHAT THIS DOES AND DOES NOT SAY ABOUT THE sd_comms VERDICT. It does '
          'NOT show\nthose three ANCHORED-VIA rows are wrong -- `load()` at '
          ':10526 may well reach\n`sd_comms` through real code. It shows the '
          'EVIDENCE CLASS cannot tell that\nfrom a comment or a neighbouring '
          'function, so the rows are UNVERIFIED rather\nthan sound, and the '
          'obligation cannot be discharged on them as they stand.')
else:
    print('NO FINDINGS -- the hop graph survives both attack points, so the '
          'three sd_comms\nANCHORED-VIA rows rest on evidence that refuses '
          'prose and refuses a neighbour.')

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
