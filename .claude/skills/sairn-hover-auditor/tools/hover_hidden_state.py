#!/usr/bin/env python
"""hover_hidden_state.py -- for each Tier A resource, does its own handler
branch on a field the tier registry never names.

H1 batch Q item 8. docs/CRITICALITY-TIERS.md's Evidence column is supposed
to be the real basis for a resource's tier -- the field that carries money
or a regulated fact, named. If the handler code BRANCHES on a field (reads
it and makes a different decision depending on its value) that the
Evidence text never mentions, the register's stated reasoning and the
code's real behaviour have silently diverged: a reader trusting the
Evidence column does not know that field exists or matters, which is
exactly how `alf_mar`'s medication-name exposure (a real SAIRNcare
incident, 2026-08-xx per this role's own log history) stayed invisible --
the register discussed billing, the code branched on medication identity.

METHOD, EACH STEP NAMED SO THE LIMITS ARE VISIBLE RATHER THAN IMPLIED AWAY:

  1. Tier A resources and their Evidence text: read directly from
     docs/CRITICALITY-TIERS.md's own row shape (same anchor every other
     tool in this role's toolset already uses).
  2. Each resource's own handler region in api/sd-data.js: found by
     locating `resource === 'NAME'` and bounding the region to the next
     such match or 150 lines, whichever is sooner. THIS IS AN
     APPROXIMATION, NOT A PARSER -- a handler longer than 150 lines, or one
     whose next resource's own match appears sooner due to a stray string
     match, truncates or over-reads. Named, not hidden.
  3. Field-shaped branch tokens inside that region: `.name ===`, `.name !==`
     etc. A STOPLIST removes generic/infra tokens (req, res, err, length,
     i, idx, ...) that are never domain fields. The stoplist is NOT
     exhaustive and is printed in full so a reader can judge it, not trust
     it blindly.
  4. A branch field is HIDDEN if its name (case-insensitive, underscore and
     camelCase normalized to a bag of words) does not appear anywhere in
     that resource's own Evidence cell text.

THIS DOES NOT PROVE a hidden field is a real risk -- only that the register's
prose does not currently account for it. Every reported field needs the
same hand-read the Evidence column itself already requires; this tool is
the triage pass that finds candidates to read, not the verdict.

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


ROW_RE = re.compile(
    r"^\|\s*`([a-z][a-z0-9_]+)`\s*\|\s*\*?\*?(A|B|C)\*?\*?\s*\|"
    r"\s*\*?\*?(A|B)\*?\*?\s*\|([^|]*)\|([^|]*)\|(.*)\|\s*$", re.M)


def tier_a_resources(repo):
    path = os.path.join(repo, 'docs', 'CRITICALITY-TIERS.md')
    if not os.path.isfile(path):
        return {}, 'docs/CRITICALITY-TIERS.md not found'
    with open(path, encoding='utf-8') as f:
        src = f.read()
    out = {}
    for m in ROW_RE.finditer(src):
        name, tier, conf, lost, read_by_wrong, evidence = m.groups()
        if tier == 'A':
            out[name] = evidence.strip()
    return out, None


STOPLIST = {
    'req', 'res', 'err', 'error', 'e', 'i', 'idx', 'index', 'length', 'len',
    'result', 'results', 'rows', 'row', 'item', 'items', 'data', 'body',
    'payload', 'resource', 'action', 'method', 'headers', 'query', 'params',
    'undefined', 'null', 'then', 'catch', 'json', 'stringify', 'parse',
    'now', 'map', 'filter', 'push', 'join', 'trim', 'slice', 'split',
    'toLowerCase', 'toUpperCase', 'includes', 'indexOf', 'constructor',
    'statusCode', 'status_code',
    # ADDED after this tool's own first real run: 'status' alone matched on
    # 110/110 resources with a locatable handler -- a near-universal
    # lifecycle field, not a signal. A near-100% hit rate on every subject
    # is the same "probe that catches everything proves nothing about any
    # one thing" shape this role's own SKILL.md already names for other
    # checkers; a status-value-SPECIFIC field (pharmacy_status,
    # qc_status, entry_type) still surfaces because it is not literally
    # the token 'status'.
    'status', 'active', 'id',
}

FIELD_RE = re.compile(r"\.([a-zA-Z_][a-zA-Z0-9_]{1,30})\s*(===|!==|==|!=)")


def handler_regions(repo, resource_names):
    path = os.path.join(repo, 'api', 'sd-data.js')
    if not os.path.isfile(path):
        return {}, 'api/sd-data.js not found'
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    anchors = []  # (line_idx, resource_name)
    anchor_re = re.compile(r"resource\s*===\s*'([a-z][a-z0-9_]+)'")
    for i, line in enumerate(lines):
        m = anchor_re.search(line)
        if m and m.group(1) in resource_names:
            anchors.append((i, m.group(1)))
    regions = {}
    for idx, (start, name) in enumerate(anchors):
        end = anchors[idx + 1][0] if idx + 1 < len(anchors) else len(lines)
        end = min(end, start + 150)
        text = ''.join(lines[start:end])
        regions.setdefault(name, []).append(text)
    return regions, None


def _words(name):
    # split camelCase / snake_case into lowercase word bag
    parts = re.findall(r'[A-Z]?[a-z0-9]+', name)
    return set(p.lower() for p in parts if len(p) > 1)


def run(repo):
    tier_a, err = tier_a_resources(repo)
    if err:
        return {'error': err}
    regions, err2 = handler_regions(repo, set(tier_a))
    if err2:
        return {'error': err2}
    report = {'resources_checked': 0, 'resources_with_handler': 0, 'hidden': {}}
    for name, evidence in tier_a.items():
        report['resources_checked'] += 1
        texts = regions.get(name)
        if not texts:
            continue
        report['resources_with_handler'] += 1
        fields = set()
        for text in texts:
            for m in FIELD_RE.finditer(text):
                fname = m.group(1)
                if fname in STOPLIST:
                    continue
                fields.add(fname)
        evidence_words = _words(evidence.replace('`', ''))
        hidden = []
        for f in sorted(fields):
            fwords = _words(f)
            if not (fwords & evidence_words):
                hidden.append(f)
        if hidden:
            report['hidden'][name] = hidden
    return report


def main(argv):
    repo = discover_repo()
    if not repo:
        print('COULD NOT RUN: no known hover-visible clone found on disk.')
        return 2
    report = run(repo)
    if report.get('error'):
        print('COULD NOT RUN: %s' % report['error'])
        return 2
    print('Tier A resources in docs/CRITICALITY-TIERS.md: %d' % report['resources_checked'])
    print('Of those, with a locatable handler region in api/sd-data.js: %d'
          % report['resources_with_handler'])
    print('STOPLIST (printed in full, not trusted blindly): %s' % ', '.join(sorted(STOPLIST)))
    if report['hidden']:
        print('CANDIDATE hidden-state fields (branched on in code, not named in Evidence):')
        for name, fields in sorted(report['hidden'].items()):
            print('  %-28s %s' % (name, ', '.join(fields)))
    else:
        print('No candidate hidden-state fields found among resources with a locatable handler.')
    if '--json' in argv:
        print(json.dumps(report, indent=1))
    return 1 if report['hidden'] else 0


def _selftest():
    import tempfile
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, '.git'))
        os.makedirs(os.path.join(td, 'api'))
        os.makedirs(os.path.join(td, 'docs'))
        with open(os.path.join(td, 'docs', 'CRITICALITY-TIERS.md'), 'w') as f:
            f.write(
                "| `fa_billing` | A | B | money lost | none | tracks amount charged |\n"
                "| `fa_theme` | C | B | cosmetic | none | n/a |\n")
        with open(os.path.join(td, 'api', 'sd-data.js'), 'w') as f:
            f.write(
                "if (resource === 'fa_billing' && action === 'write') {\n"
                "  if (payload.amount === 0) { return; }\n"
                "  if (payload.medicationName !== null) { flagPHI(); }\n"
                "}\n")
        tier_a, err = tier_a_resources(td)
        check('fa_billing read as Tier A', tier_a.get('fa_billing') is not None)
        check('fa_theme NOT read as Tier A (is C)', 'fa_theme' not in tier_a)
        report = run(td)
        check('fa_billing has a locatable handler', report['resources_with_handler'] == 1)
        check('amount is NOT hidden (named in evidence)',
              'amount' not in report['hidden'].get('fa_billing', []))
        check('medicationName IS hidden (branched on, never named in evidence)',
              'medicationName' in report['hidden'].get('fa_billing', []))

    print()
    print('SELFTEST %s (%d/%d)' % ('PASS' if not failures else 'FAIL', 5 - len(failures), 5))
    return 0 if not failures else 1


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--selftest' in argv:
        sys.exit(_selftest())
    sys.exit(main(argv))
