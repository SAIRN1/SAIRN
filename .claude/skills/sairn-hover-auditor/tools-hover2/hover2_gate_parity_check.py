#!/usr/bin/env python
"""hover2_gate_parity_check.py -- this role's OWN sibling-action gate-
asymmetry checker, independent of tools/gate_parity_check.py (hank's).

GOAL: a gate-parity conclusion for the vertical sweep must not rest on
trusting one implementation. This is a separate parser over the same
source file, built from scratch, kept in this role's own location, never
run against or depended on as this role's method for the sweep itself
(hank's tool is read ONLY as evidence when verifying HIS flags, per the
explicit instruction boundary -- never as the engine behind this role's
own vertical-by-vertical sweep).

NON-GOALS: cross-resource (one table read from two different resource
branches) is explicitly OUT of scope here -- that is hank's tool's own
2026-10-06 extension and re-implementing it would just be a second copy of
his algorithm with this role's name on it, not an independent check.
This tool answers the SAME-RESOURCE question only: do this resource's own
sibling actions (read vs write vs any named verb) agree on whether a role
check and an employee-assignment check gate them.

ALTERNATIVES CONSIDERED:
  1. Wrap/call tools/gate_parity_check.py and just re-print its result --
     rejected outright: the whole point is a result that does not depend
     on his code being correct.
  2. A full AST parser (esprima/acorn) for exact control-flow analysis --
     rejected for this pass: the existing hand-verification convention on
     this file (grep-bounded blocks, read the match) already works and a
     second heavyweight parser is not yet justified by a measured failure
     of the regex approach. Revisit if the regex approach is shown wrong.
  3. Per-resource exhaustive AST diffing of EVERY branch field -- rejected
     as over-scoped for a sweep tool; role/assignment are the two axes
     every hand-verification in this log has actually used.

CROSS-CUTTING: reads only (api/sd-data.js); writes nothing to the platform
repo. Shares no code with tools/gate_parity_check.py and was not consulted
while writing the detection patterns below (written from the role/
assignment vocabulary already used by hand in this role's own prior log
entries, e.g. seq622/632/634, not from reading hank's source).

LIMIT, MEASURED NOT ASSUMED: this tool's first real run (against rf_,
2026-10-06) under-detected rf_claims' assess_damage/reconcile assignment
gate -- both call rfAuth.ownsRow(session, claim), a named helper the first
version of ASSIGN_PAT could not see, so they printed assignment=False when
the real code assignment-gates them. Fixed in this same session before
first use by adding the ONE named helper found; this is LEXICAL, same as
tools/gate_parity_check.py's own documented limit, and a DIFFERENT helper
name is still invisible to it. Not claimed complete.

DETECTION (same two axes this role has used by hand all batch):
  role       -- a role-set membership check against session.role
                (SOMETHING_ROLES[session.role] or a roleSet(...) literal
                compared against session.role in the block)
  assignment -- a check comparing session.employee_id against a row's
                assigned_employee_id / employee_id field

Per resource with 2+ actions in the given app's RESOURCE region (keyed by
a caller-supplied prefix, e.g. --prefix rf_), reports each action's
(role, assignment) booleans and flags a GROUP where they disagree.

Usage:
  python hover2_gate_parity_check.py --prefix rf_ [--repo PATH]
  python hover2_gate_parity_check.py --selftest
"""
import argparse
import os
import re
import sys

BLOCK_START = re.compile(r"if \(resource === '(\w+)' && action === '(\w+)'\) \{")
ROLE_PAT = re.compile(r'\b[A-Z][A-Z0-9_]*_ROLES\b')
# Was `\b[A-Z][A-Z0-9_]*_ROLES\[session\.role\]` -- too narrow. rf_schedule's
# set_status (api/sd-data.js:9898) passes rfAuth.MANAGEMENT_ROLES and
# rfAuth.BROAD_READ_ROLES as ARGUMENTS into roofingLocations.canSeeSchedule(),
# never indexed inline, so the indexing-only pattern missed a real role gate
# on this tool's own first real run (same batch as the ownsRow fix above).
# Widened to "a _ROLES identifier appears anywhere in the block" -- looser,
# deliberately: an audit tool that under-detects a gate manufactures the
# exact false asymmetry it exists to rule out, which is worse than a rare
# over-detection (a _ROLES identifier referenced for an unrelated reason).
ASSIGN_PAT = re.compile(r'session\.employee_id\s*[=!]==?\s*\w|'
                        r'\w+\.assigned_employee_id\s*[=!]==?\s*session\.employee_id|'
                        r'session\.employee_id\s*[=!]==?\s*\w*\.?assigned_employee_id|'
                        # WIDENED batch J, sen_clients' write (api/sd-data.js:5834):
                        # `existingRow.assigned_employee_id !== session.employee_id`
                        # -- a NEGATED comparison, found on this tool's first real run
                        # against a fourth vertical (sen_). The three patterns above
                        # only matched `===`/`==`; a refusal written as "if NOT equal,
                        # forbid" is the equally common inverse phrasing and was
                        # invisible to an equality-only regex. Same discipline as every
                        # other widening here: under-detecting a real assignment check
                        # manufactures a false asymmetry, which is worse than the rare
                        # case of `!=` appearing for an unrelated reason.
                        # NAMED helper, found on this tool's own first real run against
                        # rf_claims: rfAuth.ownsRow(session, claim) reads as an inline
                        # assignment check (api/sd-data.js:8899), invisible to the three
                        # literal patterns above. LEXICAL, same as hank's own tool's
                        # documented limit -- a DIFFERENT helper name is still invisible
                        # here. Named rather than claimed complete.
                        r'\w+Auth\.ownsRow\(|'
                        # SECOND named helper, same batch, rf_schedule/read+write:
                        # roofingLocations.canSeeSchedule(session, row, assignee, ...)
                        # performs BOTH the role and the per-row assignee check in one
                        # call -- the role half is already caught by the _ROLES-anywhere
                        # widening above, this catches the assignment half of the SAME
                        # call. Stopping at two named helpers rather than chasing every
                        # possible name: diminishing returns past the shapes actually
                        # found this run, and this tool's docstring already states it
                        # is lexical and not claimed complete.
                        r'canSeeSchedule\(')


def _brace_close(src, start):
    """Returns the index of the `}` that closes the `{` this block's own
    BLOCK_START match ended on (depth 1 at `start`). Found by this role's
    own batch N gate-parity sweep: the prior version bounded a block by
    the NEXT literal BLOCK_START match regardless of distance, which is
    wrong whenever a DIFFERENT dispatch shape (e.g. `if (isScResource)
    {`, which this tool's regex does not match) sits between two literal
    matches -- the block absorbed hundreds of lines of a totally
    unrelated resource's code (law_trusttx's write block this way picked
    up SAIRNcode's SC_TIER_A_WRITE_ROLES and reported a false asymmetry
    that did not exist). Brace-counting finds the block's REAL end
    regardless of what dispatch shape follows it."""
    depth = 1
    i = start
    while depth > 0 and i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
        i += 1
    return i if depth == 0 else len(src)


def blocks(src, prefix):
    matches = list(BLOCK_START.finditer(src))
    out = []
    for i, m in enumerate(matches):
        resource, action = m.group(1), m.group(2)
        if not resource.startswith(prefix):
            continue
        start = m.end()
        next_match_start = matches[i + 1].start() if i + 1 < len(matches) else len(src)
        brace_end = _brace_close(src, start)
        # The TRUE end is the brace close, UNLESS it is somehow past the
        # next literal match (should not happen for well-formed JS, but
        # capping here means a bug in brace-counting fails toward the
        # OLD, already-shipped behaviour rather than a new, wider one).
        end = min(brace_end, next_match_start)
        out.append((resource, action, src[start:end]))
    return out


DEAD_GUARD_RE = re.compile(r'if\s*\(\s*(?:false|0)\s*\)\s*\{')


def strip_dead_code(body):
    """Removes the body of any `if (false) { ... }` / `if (0) { ... }`
    block before pattern-matching -- found by this role's OWN seeded-
    defect drill (item 17, batch K): a role/assignment check wrapped in
    an always-false guard is textually present but never executes, and
    the plain presence-check this tool used before this fix cannot tell
    that apart from live code. Brace-counts from the guard's own open
    brace to find the matching close -- a real mini-parse, not another
    regex guess, because getting this wrong silently in the OTHER
    direction (stripping a brace it should not) would make a real check
    invisible, which is worse than the gap this fixes."""
    out = []
    i = 0
    for m in DEAD_GUARD_RE.finditer(body):
        out.append(body[i:m.start()])
        depth = 1
        j = m.end()
        while depth > 0 and j < len(body):
            if body[j] == '{':
                depth += 1
            elif body[j] == '}':
                depth -= 1
            j += 1
        i = j
    out.append(body[i:])
    return ''.join(out)


def analyze(src, prefix):
    per_resource = {}
    for resource, action, body in blocks(src, prefix):
        live_body = strip_dead_code(body)
        per_resource.setdefault(resource, {})[action] = {
            'role': bool(ROLE_PAT.search(live_body)),
            'assignment': bool(ASSIGN_PAT.search(live_body)),
        }
    return per_resource


def report(per_resource):
    groups_flagged = 0
    lines = []
    for resource in sorted(per_resource):
        actions = per_resource[resource]
        if len(actions) < 2:
            continue
        roles = set(v['role'] for v in actions.values())
        assigns = set(v['assignment'] for v in actions.values())
        if len(roles) > 1 or len(assigns) > 1:
            groups_flagged += 1
            diffs = []
            if len(roles) > 1:
                diffs.append('role')
            if len(assigns) > 1:
                diffs.append('assignment')
            lines.append('! %s differs on: %s' % (resource, ', '.join(diffs)))
            for action in sorted(actions):
                v = actions[action]
                lines.append('    %-20s role=%-5s assignment=%s' %
                             (action, v['role'], v['assignment']))
    return groups_flagged, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix')
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.prefix:
        print('usage: --prefix PREFIX_ | --selftest')
        sys.exit(2)

    path = os.path.join(args.repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        print('COULD NOT RUN: %s not found' % path)
        sys.exit(2)
    src = open(path, encoding='utf-8').read()
    per_resource = analyze(src, args.prefix)
    if not per_resource:
        print('COULD NOT RUN: no resources matching prefix %r found' % args.prefix)
        sys.exit(2)

    groups_flagged, lines = report(per_resource)
    print('resources examined: %d (prefix %r)' % (len(per_resource), args.prefix))
    for l in lines:
        print(l)
    print('%d group(s) flagged' % groups_flagged)
    sys.exit(1 if groups_flagged else 0)


def selftest():
    fixture = """
    if (resource === 'fx_a' && action === 'read') {
      if (!FX_ROLES[session.role]) { return; }
      const ok = row.assigned_employee_id === session.employee_id;
    }
    if (resource === 'fx_a' && action === 'write') {
      if (!FX_ROLES[session.role]) { return; }
    }
    if (resource === 'fx_clean' && action === 'read') {
      if (!FX_ROLES[session.role]) { return; }
    }
    if (resource === 'fx_clean' && action === 'write') {
      if (!FX_ROLES[session.role]) { return; }
    }
    if (resource === 'fx_helper' && action === 'read') {
      if (!xyAuth.ownsRow(session, row)) { return; }
    }
    if (resource === 'fx_argrole' && action === 'read') {
      if (!canSeeRow(session, entry, xyAuth.MANAGEMENT_ROLES)) { return; }
    }
    if (resource === 'fx_sched' && action === 'read') {
      const ok = canSeeSchedule(session, row, assignee, xyAuth.MANAGEMENT_ROLES);
    }
    if (resource === 'fx_negated' && action === 'write') {
      if (existingRow.assigned_employee_id !== session.employee_id) { return; }
    }
    if (resource === 'fx_deadcode' && action === 'read') {
      if (!FX_ROLES[session.role]) { return; }
      const ok = row.assigned_employee_id === session.employee_id;
    }
    if (resource === 'fx_deadcode' && action === 'write') {
      if (false) {
        if (existingRow.assigned_employee_id !== session.employee_id) { return; }
      }
      if (!FX_ROLES[session.role]) { return; }
    }
    if (resource === 'fx_boundary' && action === 'write') {
      if (!FX_ROLES[session.role]) { return; }
    }
    if (isUnrelatedDispatchShape) {
      // A DIFFERENT dispatch pattern this tool's BLOCK_START regex does
      // not match -- found in the real file between law_trusttx's write
      // and sc_settings (batch N). Contains an UNRELATED assignment-
      // pattern match that must NOT be absorbed into fx_boundary's write
      // (which has none of its own) -- under the pre-fix boundary bug
      // this line alone would have made fx_boundary wrongly FLAG as a
      // read/write divergence that does not exist.
      if (otherRow.assigned_employee_id !== session.employee_id) { return; }
    }
    if (resource === 'fx_boundary' && action === 'read') {
      if (!FX_ROLES[session.role]) { return; }
    }
"""
    per_resource = analyze(fixture, 'fx_')
    groups_flagged, lines = report(per_resource)
    ok = (groups_flagged == 2 and
          per_resource['fx_a']['read'] == {'role': True, 'assignment': True} and
          per_resource['fx_a']['write'] == {'role': True, 'assignment': False} and
          per_resource['fx_clean']['read'] == per_resource['fx_clean']['write'] and
          per_resource['fx_helper']['read']['assignment'] is True and
          per_resource['fx_argrole']['read']['role'] is True and
          per_resource['fx_sched']['read'] == {'role': True, 'assignment': True} and
          per_resource['fx_negated']['write']['assignment'] is True and
          # fx_deadcode's write-side assignment check is wrapped in `if
          # (false)` -- unreachable, must read as NOT present (False),
          # same as fx_a's write, which is a REAL divergence from its own
          # read and must flag. Found by this role's own seeded-defect
          # drill (item 17, batch K) as a real miss on this tool's first
          # post-drill run before this ablation arm and the fix existed.
          per_resource['fx_deadcode']['write']['assignment'] is False and
          # fx_boundary: write's own block closes on ITS OWN brace before
          # an unrelated, non-matching dispatch shape carrying a stray
          # assignment-pattern reference -- that reference must NOT leak
          # into fx_boundary's write. Both read and write stay
          # assignment=False, matching each other -- no false flag.
          per_resource['fx_boundary']['write'] == {'role': True, 'assignment': False} and
          per_resource['fx_boundary']['read'] == {'role': True, 'assignment': False})
    print('SELFTEST %s: %d group(s) flagged (expected 2: fx_a and fx_deadcode, both assignment divergence); fx_clean correctly unflagged; fx_helper, fx_argrole, fx_sched, fx_negated (four named-helper/negated-comparison shapes) correctly detected; fx_deadcode (if-false-wrapped check) correctly read as NOT present; fx_boundary (brace-close vs next-literal-match, batch N) correctly ignores an unrelated non-matching block stray assignment pattern' %
          ('PASS' if ok else 'FAIL', groups_flagged))
    return 0 if ok else 1


if __name__ == '__main__':
    main()
