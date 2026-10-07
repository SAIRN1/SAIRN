#!/usr/bin/env python
"""hover_session_gate_parity_check.py -- does a resource's own handler
branch reach a DIFFERENT resource's table through a side door that skips
the SESSION gate the other resource's own branch requires.

RENAMED FROM hover_cross_resource_gate_check.py, H1 batch S item 3.
Batch R item 6 concluded that name was never committed to this repo and
logged a HIGH-severity finding to that effect (seq1125) -- WRONG, found
and corrected the same batch: the file exists and has existed since
2026-10-06, just in this role's own EXTERNAL working directory
(`C:\\Users\\marsh\\.claude\\projects\\...\\hover-audit-log\\`, alongside
the chain log itself), which batch R's search never checked. That
original tool asks a DIFFERENT question -- ROLE-check parity (does
`session.role` get consulted) grouped by TABLE across every resource that
touches it. THIS file (built before the discovery, under the name the
missing-tool search was looking for) asks a narrower, different question
-- SESSION-presence parity (does `verifySessionToken(` get called at
all) for one resource cross-reading another's table. Both are real and
complementary; keeping them under the same name after the original turned
up would have made two different checks answer to one name, so this one
was renamed rather than deleted or left colliding.

INDEPENDENT OF tools/gate_parity_check.py BY DESIGN, same constraint the
rediscovered original states for itself: not imported, not called, not
read before this tool's own logic was written. That file is a build
agent's tool and reading it would blur whether this tool's answer is
independently derived or copied.

METHOD:
  1. Every known resource name, read from api/_resources/*.js (the same
     live registry hover_completeness_probe.py already reads).
  2. Every `resource === 'NAME'` branch in api/sd-data.js and
     api/sd-sub-data.js, bounded the same way hover_hidden_state.py
     bounds a handler region (next anchor or +150 lines).
  3. CREDITS EVERY `rest('TABLE?...')` CALL IN THE REGION, NOT JUST THE
     FIRST -- this is the exact bug the original tool's own history (seq975)
     named and fixed: a first-match-only scan made a branch's SECOND table
     read invisible. Fixture-locked here so it cannot regress unnoticed a
     second time.
  4. A table reference is CROSS-RESOURCE if its name is itself a known
     resource name (step 1) and differs from the branch's own resource.
  5. GATE PRESENCE for a resource = true if ANY of its own branches contain
     `verifySessionToken(` or `credentialStillActive(`. A FLAG is a branch
     for resource R, UNGATED, that cross-reads a table belonging to
     resource T, where T's OWN branches ARE gated -- the side door: T is
     supposed to need a session, and reaching T's data through R's branch
     does not go through that check.

NOT the same question as hover_hidden_state.py (branches on an unnamed
field) or hover_completeness_probe.py (a resource missing from the
register entirely) -- this is specifically about GATE COVERAGE leaking
across a table boundary.

Read-only.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def discover_repo():
    for cand in (os.environ.get('HOVER_PROBE_REPO'),
                 r'C:\Users\marsh\Documents\SAIRN-hover'):
        if cand and os.path.isdir(os.path.join(cand, '.git')):
            return cand
    return None


def all_known_resources(repo):
    res_dir = os.path.join(repo, 'api', '_resources')
    names = set()
    if not os.path.isdir(res_dir):
        return names, 'api/_resources not found'
    for fname in sorted(os.listdir(res_dir)):
        if not fname.endswith('.js') or fname.endswith('.test.js') or fname == 'index.js':
            continue
        with open(os.path.join(res_dir, fname), encoding='utf-8') as f:
            src = f.read()
        m = re.search(r"resources:\s*\[(.*?)\]", src, re.S)
        if not m:
            continue
        code_only = '\n'.join(re.sub(r'//.*$', '', line) for line in m.group(1).splitlines())
        names |= set(re.findall(r"'([a-z][a-z0-9_]+)'", code_only))
    return names, None


ANCHOR_RE = re.compile(r"resource\s*===\s*'([a-z][a-z0-9_]+)'")
REST_RE = re.compile(r"rest\(\s*'([a-z][a-z0-9_]+)")
GATE_RE = re.compile(r"verifySessionToken\(|credentialStillActive\(")


def extract_branches(path, max_region=150):
    """[(resource, start_line, region_text), ...] -- EVERY anchor, not
    deduped by resource, because gate presence is evaluated per-resource
    across ALL its branches, and table reads must be credited per-branch."""
    if not os.path.isfile(path):
        return None, 'not found'
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    anchors = []
    for i, line in enumerate(lines):
        m = ANCHOR_RE.search(line)
        if m:
            anchors.append((i, m.group(1)))
    out = []
    for idx, (start, name) in enumerate(anchors):
        end = anchors[idx + 1][0] if idx + 1 < len(anchors) else len(lines)
        end = min(end, start + max_region)
        out.append((name, start + 1, ''.join(lines[start:end])))
    return out, None


def _indent(line):
    return len(line) - len(line.lstrip(' '))


def gated_resources_in_file(lines):
    """Every resource name covered by a verifySessionToken/
    credentialStillActive call ANYWHERE in the file, found by walking
    BACKWARD from each such call to its own enclosing `if (` condition and
    reading every `resource === 'NAME'` mentioned there -- not just a
    forward-bounded window from the resource's own anchor.

    FOUND DURING THIS TOOL'S OWN FIRST REAL RUN, HAND-VERIFIED: a gate is
    very often declared ONCE for a GROUP of resources in an outer wrapper
    -- `if ((resource === 'rf_prequal_documents' || resource === 'rf_bonding')
    && ...) { const session = verifySessionToken(...); ... }` -- with the
    individual `if (resource === 'rf_bonding' && action === ...)` branches
    nested INSIDE it, never calling verifySessionToken themselves. A
    forward-only scan from each inner anchor cannot see that outer call at
    all. This was not a hypothetical risk named in advance -- it is the
    reason the tool's first real run produced 7 flags, all 7 of which
    turned out to be exactly this shape on hand-verification, not real
    gate gaps."""
    gate_line_idx = [i for i, line in enumerate(lines) if GATE_RE.search(line)]
    gated = set()
    for gi in gate_line_idx:
        gate_indent = _indent(lines[gi])
        # walk backward to the nearest shallower-or-equal-indent line that
        # opens an `if (` -- the condition may itself span multiple lines
        # up to the matching `{`, so once found, walk FORWARD from there
        # to the `{` collecting every resource mention.
        j = gi
        cond_start = None
        while j >= 0:
            line = lines[j]
            stripped = line.strip()
            if stripped and _indent(line) < gate_indent and re.match(r'if\s*\(', stripped):
                cond_start = j
                break
            if stripped and _indent(line) < gate_indent and not stripped.startswith('if'):
                # hit an enclosing non-if line at shallower indent (e.g. a
                # plain block or another statement) -- no if-wrapper here
                break
            j -= 1
        if cond_start is None:
            continue
        k = cond_start
        cond_text = ''
        while k < len(lines):
            cond_text += lines[k]
            if '{' in lines[k]:
                break
            k += 1
            if k - cond_start > 10:
                break
        gated |= set(ANCHOR_RE.findall(cond_text))
    return gated


def tables_in_region(text):
    """EVERY rest('TABLE...') match, not just the first -- the exact bug
    the lost original's own history (seq975) named and fixed."""
    return set(REST_RE.findall(text))


def run(repo):
    known, err = all_known_resources(repo)
    if err:
        return {'error': err}
    results = {}
    for relpath in ('api/sd-data.js', 'api/sd-sub-data.js'):
        path = os.path.join(repo, relpath)
        branches, berr = extract_branches(path)
        if berr:
            results[relpath] = {'error': berr}
            continue
        with open(path, encoding='utf-8') as f:
            all_lines = f.readlines()
        # whole-file backward-scan gate detection -- also credits a
        # per-branch inline call directly, in case one exists with no
        # enclosing if-wrapper at all (the simple, common case).
        gated_resources = gated_resources_in_file(all_lines)
        for name, _, text in branches:
            if GATE_RE.search(text):
                gated_resources.add(name)
        flags = []
        for name, line, text in branches:
            tables = tables_in_region(text)
            own_gated = name in gated_resources
            for t in tables:
                if t == name or t not in known:
                    continue
                # cross-resource: t is itself a known resource, != name
                target_gated = t in gated_resources
                if target_gated and not own_gated:
                    flags.append({
                        'branch_resource': name, 'branch_line': line,
                        'foreign_table': t, 'branch_gated': own_gated,
                        'foreign_resource_gated': target_gated,
                    })
        results[relpath] = {
            'branches': len(branches),
            'distinct_resources': len(set(b[0] for b in branches)),
            'flags': flags,
        }
    return {'results': results}


def main(argv):
    repo = discover_repo()
    if not repo:
        print('COULD NOT RUN: no known hover-visible clone found on disk.')
        return 2
    report = run(repo)
    if report.get('error'):
        print('COULD NOT RUN: %s' % report['error'])
        return 2
    total_flags = 0
    for relpath, r in report['results'].items():
        if r.get('error'):
            print('%s: COULD NOT RUN (%s)' % (relpath, r['error']))
            continue
        print('%s: %d branches, %d distinct resources, %d flagged' %
              (relpath, r['branches'], r['distinct_resources'], len(r['flags'])))
        total_flags += len(r['flags'])
        for fl in r['flags']:
            print('  FLAG resource=%s (line %d, gated=%s) reads table %s (that resource IS gated)'
                  % (fl['branch_resource'], fl['branch_line'], fl['branch_gated'], fl['foreign_table']))
    if '--json' in argv:
        print(json.dumps(report, indent=1))
    return 1 if total_flags else 0


def _selftest():
    import tempfile
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, '.git'))
        os.makedirs(os.path.join(td, 'api', '_resources'))
        with open(os.path.join(td, 'api', '_resources', 'fakeapp.js'), 'w') as f:
            f.write("module.exports = {\n  app: 'fakeapp',\n  resources: [\n    'fa_orders',\n    'fa_customers',\n  ],\n};\n")

        # Case 1: planted DIRECTLY -- fa_orders' branch is ungated and
        # reads fa_customers (a SECOND table, not the first) which IS
        # gated elsewhere. Regression lock for the real "first-match-only"
        # bug the lost original's history named: fa_orders reads
        # fa_orders_meta FIRST, then fa_customers SECOND.
        with open(os.path.join(td, 'api', 'sd-data.js'), 'w') as f:
            f.write(
                "if (resource === 'fa_orders' && action === 'read') {\n"
                "  const a = await fetch(rest('fa_orders_meta?x'));\n"
                "  const b = await fetch(rest('fa_customers?y'));\n"
                "}\n"
                "if (resource === 'fa_customers' && action === 'read') {\n"
                "  const session = verifySessionToken(tokenFromRequest(req), licHash, 'fakeapp');\n"
                "  const c = await fetch(rest('fa_customers?z'));\n"
                "}\n")
        report = run(td)
        flags = report['results']['api/sd-data.js']['flags']
        check('fa_orders flagged for reading gated fa_customers',
              any(f['branch_resource'] == 'fa_orders' and f['foreign_table'] == 'fa_customers' for f in flags))
        check('the SECOND table read (fa_customers) was credited, not just the first (fa_orders_meta)',
              not any(f['foreign_table'] == 'fa_orders_meta' for f in flags))

        # Case 2: reached via the REAL TRANSITION -- start from a CLEAN
        # state (fa_orders gated, matching fa_customers' own gate), then
        # apply the same kind of edit that creates the bug for real: a
        # session-gate line REMOVED from fa_orders' own branch while its
        # cross-read of fa_customers stays, same shape as a gate
        # regressing out from under an existing cross-table read rather
        # than a hand-built bad fixture.
        with open(os.path.join(td, 'api', 'sd-data.js'), 'w') as f:
            f.write(
                "if (resource === 'fa_orders' && action === 'read') {\n"
                "  const session = verifySessionToken(tokenFromRequest(req), licHash, 'fakeapp');\n"
                "  const b = await fetch(rest('fa_customers?y'));\n"
                "}\n"
                "if (resource === 'fa_customers' && action === 'read') {\n"
                "  const session = verifySessionToken(tokenFromRequest(req), licHash, 'fakeapp');\n"
                "  const c = await fetch(rest('fa_customers?z'));\n"
                "}\n")
        report_clean = run(td)
        check('clean state (both gated) has 0 flags',
              len(report_clean['results']['api/sd-data.js']['flags']) == 0)
        # the real transition: the gate line is removed from fa_orders only
        with open(os.path.join(td, 'api', 'sd-data.js'), 'w') as f:
            f.write(
                "if (resource === 'fa_orders' && action === 'read') {\n"
                "  const b = await fetch(rest('fa_customers?y'));\n"
                "}\n"
                "if (resource === 'fa_customers' && action === 'read') {\n"
                "  const session = verifySessionToken(tokenFromRequest(req), licHash, 'fakeapp');\n"
                "  const c = await fetch(rest('fa_customers?z'));\n"
                "}\n")
        report_regressed = run(td)
        check('removing fa_orders\' own gate (the real transition) is caught',
              any(f['branch_resource'] == 'fa_orders' for f in report_regressed['results']['api/sd-data.js']['flags']))

        # Case 3, found on THIS TOOL'S OWN FIRST REAL RUN against
        # api/sd-data.js (not anticipated in advance): a SHARED outer
        # wrapper gates TWO resources together with one verifySessionToken
        # call, and each resource's own `if (resource === ...)` branch is
        # NESTED inside it rather than calling the gate itself. A
        # forward-only per-anchor scan cannot see the outer call. Regression
        # lock, planted DIRECTLY as the real shape (rf_prequal_documents /
        # rf_bonding's actual structure, renamed):
        with open(os.path.join(td, 'api', 'sd-data.js'), 'w') as f:
            f.write(
                "if ((resource === 'fa_orders' || resource === 'fa_billing') &&\n"
                "    (action === 'read' || action === 'write')) {\n"
                "  const session = verifySessionToken(tokenFromRequest(req), licHash, 'fakeapp');\n"
                "  if (resource === 'fa_orders' && action === 'read') {\n"
                "    const b = await fetch(rest('fa_customers?y'));\n"
                "  }\n"
                "  if (resource === 'fa_billing' && action === 'write') {\n"
                "    const c = await fetch(rest('fa_billing?z'));\n"
                "  }\n"
                "}\n"
                "if (resource === 'fa_customers' && action === 'read') {\n"
                "  const session = verifySessionToken(tokenFromRequest(req), licHash, 'fakeapp');\n"
                "  const c = await fetch(rest('fa_customers?z'));\n"
                "}\n")
        report_wrapped = run(td)
        check('a resource gated only via a SHARED OUTER wrapper is not a false flag',
              not any(f['branch_resource'] == 'fa_orders' for f in report_wrapped['results']['api/sd-data.js']['flags']))
        # the real transition: the OUTER wrapper's gate call itself is
        # removed (e.g. an edit that trusts the inner branches too much) --
        # both grouped resources lose their gate at once, and the flag
        # must reappear.
        with open(os.path.join(td, 'api', 'sd-data.js'), 'w') as f:
            f.write(
                "if ((resource === 'fa_orders' || resource === 'fa_billing') &&\n"
                "    (action === 'read' || action === 'write')) {\n"
                "  if (resource === 'fa_orders' && action === 'read') {\n"
                "    const b = await fetch(rest('fa_customers?y'));\n"
                "  }\n"
                "}\n"
                "if (resource === 'fa_customers' && action === 'read') {\n"
                "  const session = verifySessionToken(tokenFromRequest(req), licHash, 'fakeapp');\n"
                "  const c = await fetch(rest('fa_customers?z'));\n"
                "}\n")
        report_wrapper_regressed = run(td)
        check("removing the OUTER wrapper's gate (the real transition) is caught",
              any(f['branch_resource'] == 'fa_orders' for f in report_wrapper_regressed['results']['api/sd-data.js']['flags']))

    print()
    print('SELFTEST %s (%d/%d)' % ('PASS' if not failures else 'FAIL', 6 - len(failures), 6))
    return 0 if not failures else 1


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--selftest' in argv:
        sys.exit(_selftest())
    sys.exit(main(argv))
