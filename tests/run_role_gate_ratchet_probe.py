#!/usr/bin/env python
# REQUIREMENT: the role-gate ratchet must not pay out for DELETING the suite that
#   drives a resource -- removing the only driver of a `covered` resource must be
#   denied outright, and removing the only driver of an `uncovered` one must never
#   be reported as an improvement a session can re-pin downward to
#
# Run: python tests/run_role_gate_ratchet_probe.py
#
# ── THE DEFECT THIS PLANTS, AND WHY IT COULD NOT BE REACHED BEFORE ─────────
# tools/role_gate_negative_coverage.py ratcheted on `uncovered` alone. Deleting
# the only suite that drives a resource moves it uncovered -> not_driven, so
# `uncovered` FELL BY ONE and the tool printed "IMPROVED -- re-pin". Removing
# the evidence was rewarded with a better number and an invitation to lock it in.
#
# That case was unreachable by running the real tool: the static pass takes
# minutes and can only ever produce the single state the repo is in. So the
# decision was split out as the pure `compare_to_pin()` and the SUITE LIST is
# monkeypatched here -- a planted deletion, not a described one.
#
# ── TWO DIRECTIONS, BECAUSE ONE OF THEM IS NOT A REFUSAL AND SAYING SO ─────
# ── MATTERS MORE THAN THE REFUSAL DOES ────────────────────────────────────
# Section C deletes the drivers of a COVERED resource: exposure rises, exit 1.
# Section D deletes the driver of an UNCOVERED one: exposure is UNCHANGED, so
# the honest verdict is "no worse", exit 0 -- and the arm asserts the word
# IMPROVED does not appear. Claiming a refusal there would be the tool
# overstating what a static screen can see, which is the fault its own
# not_driven/blind split exists to avoid. The probe pins the limit as hard as
# it pins the fix.

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import role_gate_negative_coverage as R  # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name + (('\n       ' + detail) if not cond and detail else ''))


def section(t):
    print('\n' + t)


def analyse_without(paths):
    """Re-run the static pass with `paths` removed from the suite list.

    THE DELETION IS PLANTED IN THE INPUT, NOT DESCRIBED IN A COMMENT. Nothing
    on disk is touched -- a probe that rm'd a real test file and restored it
    would leave the repo one interrupted run away from a missing suite.
    """
    drop = set(os.path.normcase(os.path.abspath(p)) for p in paths)
    real = R.suite_files

    def fewer():
        return [p for p in real()
                if os.path.normcase(os.path.abspath(p)) not in drop]

    R.suite_files = fewer
    try:
        return R.analyse()
    finally:
        R.suite_files = real


print('role-gate ratchet -- a deleted driving suite must not pay out\n')

section('A. the baseline, measured rather than assumed')
sets, gated, unc, cov, und = R.analyse()
BASE = (len(unc), len(cov), len(und))
print('   uncovered=%d covered=%d not_driven=%d exposed=%d'
      % (BASE[0], BASE[1], BASE[2], BASE[0] + BASE[2]))
check('A1. the static pass produced a non-empty population, so every arm below '
      'is measuring something', len(gated) > 0,
      'gated_total=%d -- with no gated resources this whole probe is vacuous' % len(gated))
check('A2. there is at least one COVERED resource to delete the driver of',
      len(cov) > 0, 'nothing is covered; section C cannot be constructed')
check('A3. there is at least one UNCOVERED resource to delete the driver of',
      len(unc) > 0, 'nothing is uncovered; section D cannot be constructed')

PIN = {'uncovered': BASE[0], 'not_driven': BASE[2],
       'exposed': BASE[0] + BASE[2], 'covered': BASE[1]}

section('B. the baseline compares clean against its own pin')
code, lines = R.compare_to_pin(BASE[0], BASE[2], PIN)
check('B1. unchanged state is exit 0', code == 0, 'got %d: %s' % (code, lines))
check('B2. ...and does not claim an improvement',
      not any('IMPROVED' in l for l in lines), ' | '.join(lines))


def drivers_of(resource):
    """Every suite file whose content drives `resource` with any role."""
    src = R._read(R.SD, 'the role gates')
    all_roles = set()
    for v in R.role_sets(src).values():
        all_roles |= v
    out = []
    for p in R.suite_files():
        s = io.open(p, encoding='utf-8', errors='replace').read()
        if 'role' not in s:
            continue
        if resource in R.file_driven(s, all_roles):
            out.append(p)
    return out


section('C. PLANTED DEFECT -- delete every suite driving a COVERED resource')
# ── THE TARGET IS SEARCHED FOR, NOT PICKED ALPHABETICALLY ────────────────
# The first draft took sorted(covered)[0] -- alf_clients -- and C5 failed
# honestly: deleting its two drivers also moved OTHER resources, so `uncovered`
# ROSE and the OLD rule would have denied it too. A fixture both rules catch
# proves nothing about the change. So every covered resource is tried and the
# first DISCRIMINATING one is used: exposure rises (the new rule denies) while
# `uncovered` does not (the old rule would not have). If no such target exists
# in this repo, that is reported as a measured fact and C5 says so rather than
# quietly reverting to a fixture that proves nothing.
candidates = []
for _res in sorted(c[0] for c in cov):
    _p = drivers_of(_res)
    if not _p:
        continue
    _s, _g, _u, _c, _d = analyse_without(_p)
    _old = ('REGRESSION' if len(_u) > PIN['uncovered']
            else 'IMPROVED' if len(_u) < PIN['uncovered'] else 'OK')
    _new_exposed = len(_u) + len(_d)
    candidates.append((_res, _p, _old, _new_exposed))
discriminating = [c for c in candidates
                  if c[2] != 'REGRESSION' and c[3] > PIN['exposed']]
chosen = discriminating[0] if discriminating else (candidates[0] if candidates else None)
target, paths = (chosen[0], chosen[1]) if chosen else (None, [])
print('   covered candidates tried=%d  discriminating=%d'
      % (len(candidates), len(discriminating)))
print('   target=%s  drivers=%d' % (target, len(paths)))
check('C0. the planted deletion has something to delete', bool(paths),
      'no driver found for any covered resource -- C1..C5 would be vacuous')

u2, c2, d2 = (None, None, None)
if paths:
    _s, _g, u2, c2, d2 = analyse_without(paths)
    now = (len(u2), len(c2), len(d2))
    print('   after deletion: uncovered=%d covered=%d not_driven=%d exposed=%d'
          % (now[0], now[1], now[2], now[0] + now[2]))
    check('C1. the deletion really moved the resource out of `covered`',
          target not in set(x[0] for x in c2),
          '%s is still covered; the planted defect did not take' % target)
    check('C2. ...and into `not_driven`', target in set(x[0] for x in d2),
          '%s landed somewhere else' % target)
    code, lines = R.compare_to_pin(len(u2), len(d2), PIN)
    check('C3. THE GATE DENIES IT -- exit 1', code == 1,
          'got exit %d: %s' % (code, ' | '.join(lines)))
    check('C4. ...and the refusal names a deleted suite as the likely cause, '
          'so the next reader is not left to work it out',
          any('DELETED' in l for l in lines), ' | '.join(lines))

    section('C-control. the OLD rule would have let this through')
    # The old comparison was `uncovered` alone. Reproduced here rather than
    # described, so the claim "this catches something the old rule did not" is
    # measured. If this control ever starts failing, the two rules agree on
    # this fixture and section C has stopped being evidence for the change.
    old_verdict = ('REGRESSION' if len(u2) > PIN['uncovered']
                   else 'IMPROVED' if len(u2) < PIN['uncovered'] else 'OK')
    if discriminating:
        check('C5. CONTROL: ratcheting `uncovered` alone would have said %s, '
              'not REGRESSION -- so the new rule denies a deletion the old rule '
              'waved through' % old_verdict, old_verdict != 'REGRESSION',
              'the chosen target was meant to discriminate and did not')
    else:
        # NOT A PASS AND NOT A FAILURE -- a measured absence, printed. Every
        # covered resource in this repo happens to share drivers with other
        # resources, so deleting any of them also raises `uncovered` and the
        # old rule catches it too. The new rule is still strictly stronger
        # (section D is the case the old rule got WRONG, not merely missed),
        # but section C on this repo is not the evidence for that and must not
        # be read as if it were.
        print('  note  C5 SKIPPED -- no covered resource in this repo has '
              'drivers exclusive enough to discriminate the two rules. The old '
              'rule would also have said %s here. Section D is the '
              'discriminating case; see D2/D4.' % old_verdict)

section('D. PLANTED DEFECT -- delete the driver of an UNCOVERED resource')
# Pick an uncovered resource with exactly one driver, so the deletion is total.
cand = None
for res, _gs, _got in unc:
    ds = drivers_of(res)
    if len(ds) == 1:
        cand = (res, ds)
        break
if cand is None:
    check('D0. an uncovered resource with exactly one driver exists', False,
          'none found -- section D cannot be constructed and is NOT silently skipped')
else:
    res, ds = cand
    print('   target=%s  drivers=%d' % (res, len(ds)))
    _s, _g, u3, c3, d3 = analyse_without(ds)
    print('   after deletion: uncovered=%d covered=%d not_driven=%d exposed=%d'
          % (len(u3), len(c3), len(d3), len(u3) + len(d3)))
    check('D1. the deletion moved it uncovered -> not_driven',
          res not in set(x[0] for x in u3) and res in set(x[0] for x in d3),
          '%s did not move as expected' % res)
    check('D2. `uncovered` FELL -- this is the number the old rule ratcheted on',
          len(u3) < PIN['uncovered'],
          'uncovered %d -> %d' % (PIN['uncovered'], len(u3)))
    code, lines = R.compare_to_pin(len(u3), len(d3), PIN)
    check('D3. the sum is UNCHANGED, so the verdict is exit 0 -- stated as the '
          'limit of a static screen, not as a refusal it cannot justify',
          code == 0, 'got exit %d: %s' % (code, ' | '.join(lines)))
    check('D4. THE PAYOUT IS GONE -- the word IMPROVED does not appear, so '
          'there is no better number to re-pin to',
          not any('IMPROVED' in l for l in lines), ' | '.join(lines))
    check('D5. ...and it says out loud that a fallen `uncovered` here looks '
          'like a deleted suite', any('DELETING' in l for l in lines),
          ' | '.join(lines))

section('E. the pin-shape fallbacks, both directions')
code, lines = R.compare_to_pin(5, 5, {'uncovered': 5, 'not_driven': 5})
check('E1. a pin predating `exposed` DERIVES it from uncovered + not_driven '
      'rather than freezing every push', code == 0
      and any('derived 10' in l for l in lines), ' | '.join(lines))
code, lines = R.compare_to_pin(5, 5, {'uncovered': 5})
check('E2. a pin with neither `exposed` nor `not_driven` is exit 2 COULD NOT '
      'TELL -- never folded into a pass', code == 2, ' | '.join(lines))
code, lines = R.compare_to_pin(5, 5, {})
check('E3. a pin with no `uncovered` at all is exit 2', code == 2, ' | '.join(lines))
code, lines = R.compare_to_pin(5, 5, {'uncovered': 'seventeen', 'exposed': 10})
check('E4. a non-integer `uncovered` is exit 2, not a crash and not a pass',
      code == 2, ' | '.join(lines))

section('F. a real improvement is still reported as one')
code, lines = R.compare_to_pin(4, 5, {'uncovered': 5, 'not_driven': 5, 'exposed': 10})
check('F1. the sum falling is IMPROVED, exit 0', code == 0
      and any('IMPROVED' in l for l in lines), ' | '.join(lines))
code, lines = R.compare_to_pin(7, 5, {'uncovered': 5, 'not_driven': 5, 'exposed': 10})
check('F2. the sum rising is REGRESSION, exit 1', code == 1, ' | '.join(lines))
code, lines = R.compare_to_pin(3, 7, {'uncovered': 5, 'not_driven': 5, 'exposed': 10})
check('F3. a pure RECLASSIFICATION (uncovered 5->3, not_driven 5->7) is exit 0 '
      'and not an improvement -- the 2026-09-29 rule change that made the old '
      'pins non-comparable', code == 0
      and not any('IMPROVED' in l for l in lines), ' | '.join(lines))

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
