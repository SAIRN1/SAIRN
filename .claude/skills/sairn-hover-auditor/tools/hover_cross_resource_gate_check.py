#!/usr/bin/env python
"""Independent cross-resource gate-parity screen: for resource === 'x' &&
action === 'y' dispatch files, group branches by the TABLE each one reads
and flag a table read by two different resources where one branch checks
a role and the other does not.

Own tool, own location. Built 2026-10-06 (H1, corrected batch H, item 3).
Design logged before this file was written. DELIBERATELY INDEPENDENT of
tools/gate_parity_check.py -- not imported, not called, not read as part of
this tool's own logic. That tool's output may be used AFTER a run, by hand,
as a spot-check comparison only, never as this tool's detection method.

WHAT IT LOOKS FOR, PER BRANCH:
  1. Branch marker: resource === 'NAME' && action === 'VERB' (or the
     reverse order). Span runs to the next such marker or end of the
     module.exports handler body (never past it -- see
     hover_identity_attribution_check.py's own EOF-boundary lesson, applied
     here too rather than re-learned the hard way a second time).
  2. TABLE READ: the first rest('TABLE?...' or rest('TABLE') call in the
     span -- the same lexical convention every branch on this platform
     already uses.
  3. ROLE CHECK: does the span consult session.role or caller.role
     anywhere (any spelling -- SOME_ROLES[session.role], session.role ===
     'x', etc)? Coarser than assignment-gate tracking -- role presence
     only, named as a real narrowing of scope versus a fuller parity tool.

GROUPING: by TABLE. A table read by branches from more than one DISTINCT
resource, where role-check presence disagrees, is flagged. Same-resource
multi-action disagreement is a DIFFERENT question this tool does not ask
(diluting cross-resource signal with same-resource noise was not the goal
given the time this batch has for a first build).

CANNOT SEE: a role check reached through a named helper function (an
indirect `roleGate(session)` call rather than `session.role` inline) --
the SAME platform-wide limit every gate-shaped regex screen on this
codebase already carries, named rather than hidden. A table reached via a
variable built across several lines, not a literal `rest('TABLE?...')`
call, is invisible too.
"""
import os
import re
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-hover'

BRANCH_RE = re.compile(
    r"(?:resource\s*===\s*'(\w+)'\s*&&\s*action\s*===\s*'(\w+)'"
    r"|action\s*===\s*'(\w+)'\s*&&\s*resource\s*===\s*'(\w+)')"
)
TABLE_RE = re.compile(r"rest\(\s*'(\w+)(?:\?|')")
ROLE_RE = re.compile(r"\b(?:session|caller)\.role\b")

EXPORTS_RE = re.compile(r"module\.exports\s*=\s*async\s*(?:function\s*\*?\s*\w*\s*)?\([^)]*\)\s*(?:=>)?\s*\{")


def _matching_brace_text(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
    return text[open_idx:]


def _handler_body_end(text):
    m = EXPORTS_RE.search(text)
    if not m:
        return len(text)
    brace_idx = text.index('{', m.start())
    body = _matching_brace_text(text, brace_idx)
    return brace_idx + len(body)


def find_branches(text):
    marks = []
    for m in BRANCH_RE.finditer(text):
        if m.group(1):
            resource, action = m.group(1), m.group(2)
        else:
            action, resource = m.group(3), m.group(4)
        marks.append((m.start(), resource, action))
    hard_end = _handler_body_end(text)
    spans = []
    for i, (pos, resource, action) in enumerate(marks):
        natural_end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        end = min(natural_end, hard_end) if pos < hard_end else natural_end
        spans.append((resource, action, pos, end))
    return spans


def analyze_file(path):
    """One unit PER TABLE a branch reads, not one unit per branch. FOUND
    NECESSARY ON THE FIRST REAL RUN: api/sd-data.js's alf_compliance_rules/
    evaluate branch reads THREE tables (alf_compliance_rules, alf_staff,
    alf_staff_credentials) -- taking only the FIRST rest('TABLE?...') match
    per branch made every table after the first invisible, which is exactly
    why alf_staff never appeared on this tool's own first run even though
    this role already confirmed it by hand (seq 963). Every table a branch
    touches now gets its own unit, carrying that branch's role-check state."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    spans = find_branches(text)
    units = []
    for resource, action, start, end in spans:
        span_text = text[start:end]
        tables = list(dict.fromkeys(m.group(1) for m in TABLE_RE.finditer(span_text)))
        has_role = bool(ROLE_RE.search(span_text))
        if not tables:
            units.append({'resource': resource, 'action': action, 'table': None, 'role': has_role})
            continue
        for table in tables:
            units.append({'resource': resource, 'action': action, 'table': table, 'role': has_role})
    return units


def cross_resource_groups(units):
    by_table = {}
    for u in units:
        if not u['table']:
            continue
        by_table.setdefault(u['table'], []).append(u)
    flagged = []
    for table, us in by_table.items():
        resources = set(u['resource'] for u in us)
        if len(resources) < 2:
            continue
        roles = set(u['role'] for u in us)
        if len(roles) > 1:
            flagged.append({'table': table, 'units': us})
    return flagged


# ---------------------------------------------------------------------------
# Selftest: a fixture file with a REAL cross-resource disagreement (two
# resources reading one table, only one role-checked) and a CONTROL pair
# (same table, both role-checked -- must NOT flag).
# ---------------------------------------------------------------------------

FIXTURE = """
module.exports = async (req, res) => {
  if (resource === 'widget_admin' && action === 'read') {
    const r = await fetch(rest('shared_table?license_hash=eq.x'), { headers });
    return;
  }
  if (resource === 'widget_view' && action === 'peek') {
    if (!ROLES[session.role]) { res.status(403); return; }
    const r = await fetch(rest('shared_table?license_hash=eq.x'), { headers });
    return;
  }
  if (resource === 'gizmo_a' && action === 'read') {
    if (!ROLES[session.role]) { res.status(403); return; }
    const r = await fetch(rest('gizmo_table?license_hash=eq.x'), { headers });
    return;
  }
  if (resource === 'gizmo_b' && action === 'read') {
    if (!ROLES[caller.role]) { res.status(403); return; }
    const r = await fetch(rest('gizmo_table?license_hash=eq.x'), { headers });
    return;
  }
  if (resource === 'multi_reader' && action === 'evaluate') {
    const a = await fetch(rest('multi_reader?license_hash=eq.x'), { headers });
    const b = await fetch(rest('secondary_table?license_hash=eq.x'), { headers });
    return;
  }
  if (resource === 'secondary_table' && action === 'read') {
    if (!ROLES[session.role]) { res.status(403); return; }
    const r = await fetch(rest('secondary_table?license_hash=eq.x'), { headers });
    return;
  }
};
"""


def _selftest():
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(FIXTURE)
    try:
        units = analyze_file(path)
        flagged = cross_resource_groups(units)
        tables_flagged = set(f['table'] for f in flagged)
        ok = 0
        total = 4
        if 'shared_table' in tables_flagged:
            ok += 1
            print('  ok   shared_table (role disagreement) correctly FLAGGED')
        else:
            print('  FAIL shared_table expected flagged, got %r' % tables_flagged)
        if 'gizmo_table' not in tables_flagged:
            ok += 1
            print('  ok   gizmo_table (both role-checked, control) correctly NOT flagged')
        else:
            print('  FAIL gizmo_table should not be flagged (both role-checked)')
        if 'secondary_table' in tables_flagged:
            ok += 1
            print('  ok   secondary_table FLAGGED via multi_reader\'s SECOND table read -- the exact bug the real run found (alf_staff hidden behind a first-table-only read)')
        else:
            print('  FAIL secondary_table expected flagged via multi-table detection, got %r' % tables_flagged)
        multi_units = [u for u in units if u['resource'] == 'multi_reader']
        if len(multi_units) == 2:
            ok += 1
            print('  ok   multi_reader branch produced 2 units, one per table it reads')
        else:
            print('  FAIL multi_reader expected 2 units, got %d' % len(multi_units))
        print('%d/%d fixture checks correct' % (ok, total))
        return ok == total
    finally:
        os.remove(path)


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--file' in argv:
        path = argv[argv.index('--file') + 1]
    else:
        path = os.path.join(REPO, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        print('COULD NOT RUN: %s does not exist' % path)
        return 2
    units = analyze_file(path)
    flagged = cross_resource_groups(units)
    print('CROSS-RESOURCE GATE CHECK (own, independent tool) -- %s' % path)
    print('  branches found: %d' % len(units))
    no_role_units = [u for u in units if u['table'] and not u['role']]
    print('  tables flagged: %d' % len(flagged))
    for f in flagged:
        print('! table %s' % f['table'])
        for u in f['units']:
            print('    %s/%s  role=%s' % (u['resource'], u['action'], u['role']))
    return 1 if flagged else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
