#!/usr/bin/env python
"""hover_threshold_cluster.py -- for every trigger threshold this role can
find in the repo's own source, how many measurable items sit just under it.

H1 batch Q item 7. A threshold is a cliff: at N-1 nothing fires, at N
something does, and nothing about the number N-1 looks different from N-5
unless somebody is specifically looking for the drop-off. Several real
SAIRN incidents are shaped exactly like this (the register's own
Tier-A-count drift examples in CRITICALITY-TIERS.md; a claim-expiry window
one commit away from lapsing; undirected-sweep cadence trackers that sit at
N-1 for a long time and then silently reset). This tool does not find NEW
thresholds' correctness -- it is a census: which numeric gates exist, and
which measurable counts sit close enough to trip one soon.

TWO HONEST LIMITS, NAMED RATHER THAN HIDDEN, both because of the standing
NO BUILDER EXECUTION rule this batch runs under:

  1. STATIC THRESHOLD DISCOVERY ONLY. This greps `.py` source for
     comparison-shaped lines (`name >= NUM`, `name > NUM`, etc.) where the
     compared name looks count-shaped. It does not parse an AST and does
     not understand control flow -- a threshold inside a string or a
     comment can still match if it is shaped like code; the clustering step
     below is what separates real findings from text that merely looks
     like one.
  2. LIVE VALUE RESOLUTION IS MECHANICAL-ONLY, NEVER BY RUNNING THE OWNING
     TOOL. For a handful of simple, directly countable shapes -- the
     length of a JSON array in a named repo file, the line count of a
     JSONL file, the row count of a markdown table matching an anchor --
     this tool reads the data file directly and counts. Every other
     threshold is reported with value=UNRESOLVED and named as exactly
     that: resolving it would mean executing the owning tool, which is out
     of scope for a read-only, cross-session census and is correctly left
     for that tool's own owner to self-report.

CLUSTERING: any RESOLVED item within --margin (default 3) below its
threshold is reported as a near-miss. Already-tripped (value >= threshold)
is reported separately, not folded into "just under".
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


THRESHOLD_RE = re.compile(
    r'\b([a-zA-Z_][a-zA-Z0-9_\.\(\)]{2,40})\s*(>=|<=|>|<)\s*(\d{1,6})\b')

COUNTY_HINTS = ('count', 'len', 'num', 'total', 'n_', 'size', 'cadence',
                'threshold', 'age', 'hours', 'h', 'budget', 'max', 'limit')

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'tools-hover2'}


def iter_py_files(repo):
    # Self-exclusion, found by hand-verifying this tool's OWN first real
    # run: its own _selftest() fixture writes the literal text
    # "bypass_count >= 10" into a temp file as a string, and that same
    # literal text also appears in THIS file's source (inside the fixture
    # f.write(...) call) -- a text-shaped scanner cannot tell a fixture
    # string from real code, so it flagged itself as ALREADY TRIPPED. This
    # is the same class of bug as hover_completeness_probe.py's
    # comment-embedded-quote false positive: the general limitation is
    # disclosed in the module docstring, and this one concrete, confirmed
    # instance (self-reference) is fixed outright rather than left for a
    # reader to notice.
    self_path = os.path.abspath(__file__)
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith('.py'):
                full = os.path.join(root, fn)
                if os.path.abspath(full) == self_path:
                    continue
                yield full


def find_thresholds(repo):
    found = []
    for path in iter_py_files(repo):
        rel = os.path.relpath(path, repo).replace('\\', '/')
        try:
            with open(path, encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            for m in THRESHOLD_RE.finditer(line):
                name, op, num = m.group(1), m.group(2), int(m.group(3))
                if num < 2:
                    continue
                low = name.lower()
                if not any(h in low for h in COUNTY_HINTS):
                    continue
                found.append({
                    'file': rel, 'line': i, 'name': name, 'op': op,
                    'threshold': num, 'source_line': stripped[:160],
                })
    return found


# Mechanical, named, read-only resolvers for the handful of count shapes
# this role already knows how to read directly without running a tool.
def resolve_known_counts(repo):
    counts = {}
    # docs/BYPASS-LOG.jsonl line count
    p = os.path.join(repo, 'docs', 'BYPASS-LOG.jsonl')
    if os.path.isfile(p):
        with open(p, encoding='utf-8') as f:
            counts['bypass_log_entries'] = sum(1 for _ in f)
    # this role's own audit log, for self-referential thresholds
    hover_log = r'C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hover\hover-audit-log\hover-audit-log.jsonl'
    if os.path.isfile(hover_log):
        with open(hover_log, encoding='utf-8') as f:
            counts['hover_log_entries'] = sum(1 for _ in f)
    # CRITICALITY-TIERS.md Tier A row count (anchor-correct, per that doc's
    # own stated bug history: row anchor, not a plain substring count)
    p = os.path.join(repo, 'docs', 'CRITICALITY-TIERS.md')
    if os.path.isfile(p):
        with open(p, encoding='utf-8') as f:
            src = f.read()
        counts['tier_a_rows'] = len(re.findall(r'^\|\s*`[a-z][a-z0-9_]+`\s*\|\s*\*?\*?A\*?\*?\s*\|', src, re.M))
    # open-work index row count
    p = os.path.join(repo, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
    if os.path.isfile(p):
        with open(p, encoding='utf-8') as f:
            counts['open_work_rows'] = sum(1 for line in f if line.startswith('|') and '---' not in line)
    return counts


# Map a threshold's variable-name hint to a resolved count key above, where
# the correspondence is unambiguous enough to state without guessing.
NAME_TO_COUNT = {
    'bypass': 'bypass_log_entries',
}


def cluster(found, counts, margin=3):
    out = []
    for t in found:
        resolved = None
        low = t['name'].lower()
        for hint, key in NAME_TO_COUNT.items():
            if hint in low and key in counts:
                resolved = counts[key]
                break
        t = dict(t)
        t['value'] = resolved if resolved is not None else 'UNRESOLVED'
        if resolved is not None:
            dist = t['threshold'] - resolved
            t['distance_below'] = dist
            t['tripped'] = resolved >= t['threshold'] if t['op'] in ('>=', '>') else resolved <= t['threshold']
            t['near_miss'] = (not t['tripped']) and 0 <= dist <= margin
        else:
            t['distance_below'] = None
            t['tripped'] = None
            t['near_miss'] = False
        out.append(t)
    return out


def run(repo, margin=3):
    found = find_thresholds(repo)
    counts = resolve_known_counts(repo)
    clustered = cluster(found, counts, margin)
    return {
        'total_threshold_sites': len(found),
        'resolved_counts': counts,
        'near_miss': [t for t in clustered if t['near_miss']],
        'tripped': [t for t in clustered if t['tripped']],
        'unresolved_count': sum(1 for t in clustered if t['value'] == 'UNRESOLVED'),
        'all': clustered,
    }


def main(argv):
    repo = discover_repo()
    if not repo:
        print('COULD NOT RUN: no known hover-visible clone found on disk.')
        return 2
    margin = 3
    if '--margin' in argv:
        margin = int(argv[argv.index('--margin') + 1])
    report = run(repo, margin)
    print('STATIC threshold-shaped comparison sites found: %d (count-hinted names only)'
          % report['total_threshold_sites'])
    print('Resolved (mechanically countable, no tool execution): %s'
          % json.dumps(report['resolved_counts']))
    print('Unresolved (would require running the owning tool -- left to its own owner): %d'
          % report['unresolved_count'])
    if report['near_miss']:
        print('NEAR-MISS (resolved value within %d below its threshold):' % margin)
        for t in report['near_miss']:
            print('  %s:%d  %s %s %d  value=%s  distance_below=%d'
                  % (t['file'], t['line'], t['name'], t['op'], t['threshold'],
                     t['value'], t['distance_below']))
    else:
        print('No resolved near-misses at margin=%d (of the small resolvable set -- '
              'most threshold sites remain UNRESOLVED by design, see docstring).' % margin)
    if report['tripped']:
        print('ALREADY AT/OVER THRESHOLD:')
        for t in report['tripped']:
            print('  %s:%d  %s %s %d  value=%s'
                  % (t['file'], t['line'], t['name'], t['op'], t['threshold'], t['value']))
    if '--json' in argv:
        print(json.dumps(report, indent=1))
    return 1 if report['near_miss'] or report['tripped'] else 0


def _selftest():
    import tempfile
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, '.git'))
        os.makedirs(os.path.join(td, 'docs'))
        with open(os.path.join(td, 'fake_tool.py'), 'w') as f:
            f.write("if bypass_count >= 10:\n    pass\nif unrelated_thing >= 999999:\n    pass\n# commented_count >= 1 should be skipped\n")
        with open(os.path.join(td, 'docs', 'BYPASS-LOG.jsonl'), 'w') as f:
            f.write('{}\n' * 8)
        found = find_thresholds(td)
        names = [t['name'] for t in found]
        check('bypass_count threshold found', 'bypass_count' in names)
        check('commented-out threshold NOT found', 'commented_count' not in names)
        counts = resolve_known_counts(td)
        check('bypass_log_entries resolved to 8', counts.get('bypass_log_entries') == 8)
        clustered = cluster(found, counts, margin=3)
        bc = [t for t in clustered if t['name'] == 'bypass_count'][0]
        check('bypass_count resolved value is 8', bc['value'] == 8)
        check('bypass_count is a near-miss at margin 3 (10-8=2)', bc['near_miss'] is True)
        unrelated = [t for t in clustered if t['name'] == 'unrelated_thing'][0]
        check('unrelated_thing stays UNRESOLVED (not guessed)', unrelated['value'] == 'UNRESOLVED')
        check('UNRESOLVED items are never near_miss', unrelated['near_miss'] is False)

    print()
    print('SELFTEST %s (%d/%d)' % ('PASS' if not failures else 'FAIL', 6 - len(failures), 6))
    return 0 if not failures else 1


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--selftest' in argv:
        sys.exit(_selftest())
    sys.exit(main(argv))
