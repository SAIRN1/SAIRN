#!/usr/bin/env python
r"""defect_density_weighting.py -- a real, driven rotation input: which files
and modules have this role's own self-log ACTUALLY produced findings against,
not which Tier a build agent declared. Built 2026-09-16, direct instruction.

WHY THIS IS A GENUINE, NAMED FOURTH AXIS, NOT A RESTATEMENT OF TIER. Tier
(A/B/C) is a DECLARED, static judgment about how much a resource matters if it
goes wrong -- set once, by a build agent, largely unchanging. Evidence-margin
weighting (already in SKILL.md's Rotation section) is about how CONTESTED a
given finding was. This is a third thing again: an empirically MEASURED,
UPDATING signal -- where has this role's OWN history of real findings actually
landed -- read from the one dataset nothing else on this platform has: the
hash-chained self-log. Real, adjacent precedent this is explicitly modeled on
(named in SKILL.md's Rotation section already): predictive, trend-driven
re-prioritization is the TOP rung of mature audit-maturity models (financial
audit risk-based sampling that updates on prior-year misstatement patterns;
aviation SMS programs that re-target inspection based on incident history)
-- everything else about this role's design already sits there; this closes
the one piece that was still a fixed schedule rather than a learning one.

WHAT COUNTS AS A REAL DEFECT-DENSITY SIGNAL, STATED BEFORE THE DATA IS READ.
Only `type == 'finding'` entries count -- a `check` that came back clean is a
real result (Safe Harbor) and must not count AGAINST a file, or a thoroughly-
verified-clean file would rank as if it had never been looked at. Only
`target != 'self'` entries count toward PLATFORM file/module weighting --
findings about this role's own tooling (hover_self_health.py, this file
itself) are a genuinely different population and are reported separately,
never blended into the platform-file signal a rotation pick would read.

HOW A FINDING IS ATTRIBUTED TO A FILE, AND THE HONEST LIMIT ON IT. The
self-log's own `ref` field was written freehand across 29 findings and is not
a structured format: a bare commit sha, a sha plus prose, a bare file path, or
pure prose with neither (entries 36, 39, 41, 47, 64, 74 -- process-level
findings with no single file to attribute to). This tool tries TWO
extractions per finding, independently, and unions the result:
  1. any 7-40 character hex substring, checked against THIS repo's own object
     database (`git cat-file -t`) -- a string that merely LOOKS like a sha but
     is not a real commit here is silently not a commit, not a false hit;
  2. any substring matching a real path shape (`[\w./-]+\.(?:py|js|html|json
     |md|sql)`), read literally, no existence check against the working tree
     REQUIRED (a path can legitimately name a file from HISTORY that no
     longer exists at HEAD).
A finding with NEITHER extraction succeeding is counted as UNATTRIBUTABLE and
named as such in the report, never silently dropped from the denominator.

DISCLOSED, NOT HIDDEN: with only 29 real findings across this role's whole
history, most files this reports will have a density of 1. This is a REAL
STATEMENT about how much history exists, not a flaw in the tool -- the report
prints total findings and total attributed alongside every ranking so a
reader is never handed a ranking with the sample size implied only by its own
confidence.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
REPO = r'C:\Users\marsh\Documents\SAIRN-hover'

SHA_RE = re.compile(r'\b[0-9a-f]{7,40}\b', re.I)
PATH_RE = re.compile(r'[\w./\\-]+\.(?:py|js|html|json|md|sql)')

# Module attribution: a coarse, disclosed heuristic, not a claim of precision.
# An app name embedded in the filename wins; otherwise the top-level directory.
APP_HINTS = ('sairnbiz', 'sairnvet', 'sairnlaw', 'sairndental', 'sairncode',
            'sairncash', 'sairncare', 'sairnsenior', 'sairnroofing', 'sairnbuild',
            'sairnscape', 'sairndesign', 'sairnfreedom', 'sairngrounds', 'stonedesk')


def load_entries(path):
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def git(*args):
    r = subprocess.run(['git', '-C', REPO] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout, r.stderr


def is_real_commit(token):
    code, out, _ = git('cat-file', '-t', token)
    return code == 0 and out.strip() == 'commit'


def files_touched_by(sha):
    # --root REQUIRED, and found only by testing against this repo's own real
    # root commit: diff-tree normally diffs against the parent, and a root
    # commit has none, so it silently returns nothing without --root -- a
    # false ZERO that looks identical to "this commit touched no files".
    code, out, _ = git('diff-tree', '--no-commit-id', '--name-only', '-r', '--root', sha)
    if code != 0:
        return []
    return [l.strip() for l in out.split('\n') if l.strip()]


def module_of(path):
    base = os.path.basename(path).lower()
    for hint in APP_HINTS:
        if hint in base:
            return hint
    parts = path.replace('\\', '/').split('/')
    return parts[0] if parts else path


def attribute(finding):
    """(files, modules, method) for one finding entry.

    method is 'sha', 'path', 'sha+path', or 'unattributed' -- reported
    per-finding in --verbose so a reader can see WHY a file was credited,
    not just that it was.
    """
    ref = finding.get('ref') or ''
    files = set()
    used_sha, used_path = False, False

    for tok in SHA_RE.findall(ref):
        if is_real_commit(tok):
            touched = files_touched_by(tok)
            if touched:
                files.update(touched)
                used_sha = True

    for tok in PATH_RE.findall(ref):
        files.add(tok.replace('\\', '/'))
        used_path = True

    if used_sha and used_path:
        method = 'sha+path'
    elif used_sha:
        method = 'sha'
    elif used_path:
        method = 'path'
    else:
        method = 'unattributed'

    modules = {module_of(f) for f in files}
    return sorted(files), sorted(modules), method


def _fixture_control():
    """Blind control: synthetic entries with a KNOWN correct attribution,
    checked before the real log is trusted. Uses this repo's own real,
    stable root commit (never rewritten) as the one real sha fixture, so the
    control does not depend on any commit created during a live session."""
    code, root_sha, _ = git('rev-list', '--max-parents=0', 'HEAD')
    root_sha = root_sha.strip().split('\n')[0] if code == 0 else None
    cases = []
    if root_sha:
        real_files = files_touched_by(root_sha)
        cases.append((
            'a finding whose ref is the real root commit sha attributes to its real files',
            {'type': 'finding', 'target': 'x', 'ref': root_sha},
            lambda files, modules, method: method in ('sha', 'sha+path') and set(files) == set(real_files),
        ))
    cases.append((
        'a finding whose ref is a bare, non-existent-looking hex string is NOT credited as a commit',
        {'type': 'finding', 'target': 'x', 'ref': 'deadbeefcafebabe0000000000000000000000'},
        lambda files, modules, method: method == 'unattributed',
    ))
    cases.append((
        'a finding whose ref names a real-shaped path with no sha is attributed by path alone',
        {'type': 'finding', 'target': 'x', 'ref': 'api/_lib/my_invented_module.js'},
        lambda files, modules, method: method == 'path' and files == ['api/_lib/my_invented_module.js'],
    ))
    cases.append((
        'a finding whose ref is pure prose with neither shape is UNATTRIBUTED, not silently dropped',
        {'type': 'finding', 'target': 'x', 'ref': 'entry 17 re-confirmed open, still a live gap'},
        lambda files, modules, method: method == 'unattributed',
    ))
    failures = []
    for label, finding, check in cases:
        files, modules, method = attribute(finding)
        if not check(files, modules, method):
            failures.append('%s -- got files=%r modules=%r method=%r' % (label, files, modules, method))
    return {'fixtures_run': len(cases), 'fixtures_failed': failures, 'FAIL_control': len(failures) > 0}


def compute(entries):
    findings = [e for e in entries if e.get('type') == 'finding']
    platform_findings = [e for e in findings if e.get('target') != 'self']
    self_findings = [e for e in findings if e.get('target') == 'self']

    file_hits = Counter()
    module_hits = Counter()
    method_counts = Counter()
    per_finding = []

    for f in platform_findings:
        files, modules, method = attribute(f)
        method_counts[method] += 1
        per_finding.append({'seq': f['seq'], 'target': f['target'], 'ref': f.get('ref'),
                            'files': files, 'modules': modules, 'method': method})
        for fp in files:
            file_hits[fp] += 1
        for m in modules:
            module_hits[m] += 1

    return {
        'total_findings': len(findings),
        'platform_findings': len(platform_findings),
        'self_findings_excluded': len(self_findings),
        'attribution_method_counts': dict(method_counts),
        'unattributable': method_counts.get('unattributed', 0),
        'file_density': file_hits.most_common(),
        'module_density': module_hits.most_common(),
        'per_finding': per_finding,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', default=DEFAULT_LOG)
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--verbose', action='store_true')
    # --json: structured output for hover_cold_scan_pool.py's --draw, which
    # consumes module_density as the PRIMARY draw-score factor. Added
    # 2026-09-27 so the consumer reads a contract, not this tool's prose --
    # a stdout-prose parse is the string-anchor gyro the disciplines doc
    # warns about (item 8), and it would rot the day a heading reworded.
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    control = _fixture_control()
    if control['FAIL_control']:
        print(json.dumps({'FAIL_control': True, 'fixtures_failed': control['fixtures_failed'],
                          'note': 'COULD NOT RUN -- classifier failed its own fixtures'}, indent=2))
        return 2

    entries = load_entries(args.log)
    result = compute(entries)

    if args.json:
        print(json.dumps({'FAIL_control': False,
                          'module_density': result['module_density'],
                          'platform_findings': result['platform_findings'],
                          'unattributable': result['unattributable']}))
        return 0

    print('DEFECT DENSITY WEIGHTING -- a fourth rotation axis, empirically measured, not declared')
    print('  classifier control: %d/%d fixtures pass' % (control['fixtures_run'], control['fixtures_run']))
    print('  %d total findings in the self-log; %d self-target (excluded from platform weighting), '
          '%d platform-target' % (result['total_findings'], result['self_findings_excluded'],
                                  result['platform_findings']))
    print('  attribution methods: %s' % result['attribution_method_counts'])
    print('  %d of %d platform findings could not be attributed to any file -- named, not dropped'
          % (result['unattributable'], result['platform_findings']))
    print()
    print('  DISCLOSED LIMIT, MEASURED ON THIS OWN RUN, NOT HYPOTHETICAL: sha-based attribution '
          'credits')
    print('  EVERY file the whole commit touched, not only the one the finding was actually about --')
    print('  docs/MASTER-PLAN.md and docs/traceability-matrix.md rank here because they get')
    print('  regenerated alongside real fixes, not because a finding was ever about them directly.')
    print('  Read the per-file ranking as "files that travel with real findings", not "files that')
    print('  were themselves defective" -- --verbose shows which specific findings drove each count.')
    print()
    print('  TOP FILES BY REAL FINDING COUNT (n=1 is most of this list -- read the sample size):')
    for fp, n in result['file_density'][:args.top]:
        print('    %2d  %s' % (n, fp))
    print()
    print('  TOP MODULES/APPS BY REAL FINDING COUNT:')
    for m, n in result['module_density'][:args.top]:
        print('    %2d  %s' % (n, m))

    if args.verbose:
        print()
        print('  PER-FINDING ATTRIBUTION:')
        for pf in result['per_finding']:
            print('    #%d [%s] method=%s ref=%r -> %s'
                 % (pf['seq'], pf['target'], pf['method'], pf['ref'], pf['files']))

    return 0


if __name__ == '__main__':
    sys.exit(main())
