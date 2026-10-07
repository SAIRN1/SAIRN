#!/usr/bin/env python
"""hover2_routing_gap_check.py -- deterministic, read-only replacement for
this role's past reliance on tools/hover_routing_gap_check.py (a
build-agent tool, run one-off at seq568/586 before the no-execution rule).
Computes the SAME question -- how many of this role's own findings are
unrouted -- by reading two static sources only, never executing anything:

  1. this role's own hover-audit-log.jsonl: every entry with type=="finding".
  2. docs/SAIRN-OPEN-WORK-INDEX.md: every HTML comment matching
     HOVER-H2-<seq>[-...]-ROUTED, naming which of this role's findings a
     build agent has already routed into the index.

UNROUTED = findings whose seq never appears in a ROUTED marker. This is a
NARROWER question than hank's own tool (which also covers H1's findings
and this role's own routing docs under docs/2026-*-hover2-*-routing.md,
which this tool also checks as a second, OR'd source of "routed").

NON-GOALS: does not replicate hank's exact matching logic or his
scope (H1's findings, non-finding entry types). Does not decide whether
an unrouted finding is urgent. Read-only on both sources.

Usage:
  python hover2_routing_gap_check.py --log PATH --index PATH [--repo PATH]
  python hover2_routing_gap_check.py --selftest
"""
import argparse
import glob
import json
import os
import re
import sys

ROUTED_MARKER = re.compile(r'HOVER-H2-([\d-]+?)-ROUTED')
# Was `HOVER-H2-(\d+)`, which only captured the FIRST number in a marker
# naming several at once -- found on this tool's own first real run,
# which reported 150 of 168 unrouted. Markers like
# "HOVER-H2-551-556-564-ROUTED" name THREE seqs in one comment (one row
# routing several findings together); the single-number pattern silently
# dropped the other two. Widened to capture the whole hyphen-run before
# "-ROUTED" and split it into individual numbers.


def load_findings(log_path):
    seqs = []
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get('type') == 'finding':
                seqs.append(d['seq'])
    return seqs


def load_routed_from_index(index_path):
    if not os.path.isfile(index_path):
        return set()
    text = open(index_path, encoding='utf-8').read()
    routed = set()
    for run in ROUTED_MARKER.findall(text):
        for part in run.split('-'):
            if part.isdigit():
                routed.add(int(part))
    return routed


def load_routed_from_own_docs(repo):
    """This role's own docs/2026-*-hover2-*-routing.md files are a second,
    valid form of 'routed' -- a finding written into its own routing doc,
    even before a build agent copies it into the shared index, is not
    unrouted in the sense this check cares about (the routing STEP this
    role owns is done; what happens after is out of this role's hands)."""
    routed = set()
    pattern = os.path.join(repo, 'docs', '2026-*-hover2-*-routing.md')
    for path in glob.glob(pattern):
        text = open(path, encoding='utf-8').read()
        for m in re.findall(r'seq\s*(\d+)', text, re.IGNORECASE):
            routed.add(int(m))
    return routed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log')
    ap.add_argument('--index')
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if not args.log or not os.path.isfile(args.log):
        print('COULD NOT RUN: --log %r not found' % args.log)
        sys.exit(2)

    findings = load_findings(args.log)
    routed = load_routed_from_index(args.index) if args.index else set()
    routed |= load_routed_from_own_docs(args.repo)

    unrouted = [s for s in findings if s not in routed]
    print('FINDINGS: %d   ROUTED (seen): %d   UNROUTED: %d' %
          (len(findings), len(routed), len(unrouted)))
    if unrouted:
        print('unrouted seqs: %s' % ', '.join(str(s) for s in unrouted))
    sys.exit(1 if unrouted else 0)


def selftest():
    import tempfile
    d = tempfile.mkdtemp()
    log_path = os.path.join(d, 'log.jsonl')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(json.dumps({'seq': 1, 'type': 'finding'}) + '\n')
        f.write(json.dumps({'seq': 2, 'type': 'finding'}) + '\n')
        f.write(json.dumps({'seq': 3, 'type': 'check'}) + '\n')
        f.write(json.dumps({'seq': 4, 'type': 'finding'}) + '\n')

    index_path = os.path.join(d, 'index.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write('<!-- HOVER-H2-1-ROUTED-HANK-2026-01-01 -->\n')
        f.write('<!-- HOVER-H2-5-6-7-ROUTED-HANK-2026-01-02 -->\n')

    os.makedirs(os.path.join(d, 'docs'))
    with open(os.path.join(d, 'docs', '2026-01-01-hover2-fx-routing.md'), 'w', encoding='utf-8') as f:
        f.write('Routed 2026-01-01 by hover2 (H2), hover-audit-log seq 2.\n')

    findings = load_findings(log_path)
    routed_idx = load_routed_from_index(index_path)
    routed_own = load_routed_from_own_docs(d)
    routed = routed_idx | routed_own
    unrouted = [s for s in findings if s not in routed]

    ok = (findings == [1, 2, 4] and routed_idx == {1, 5, 6, 7} and
          routed_own == {2} and unrouted == [4])
    print('SELFTEST %s: findings=%r routed_idx=%r routed_own=%r unrouted=%r' %
          ('PASS' if ok else 'FAIL', findings, routed_idx, routed_own, unrouted))
    return 0 if ok else 1


if __name__ == '__main__':
    main()
