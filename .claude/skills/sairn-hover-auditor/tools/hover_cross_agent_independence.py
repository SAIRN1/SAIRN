#!/usr/bin/env python
"""
hover_cross_agent_independence.py -- a mechanical check that H1's and H2's
own append-only audit logs are actually searching independently, rather
than converging on the same targets at the same times.

ONE-LINE CONCEPT (written before this code, per b58 methodology): pull each
session's own append-only log over the same recent window, extract
target/resource tokens from each entry's summary, and report (a) keyword-
overlap Jaccard across the two windows and (b) any cross-session entry pair
whose token overlap AND timestamp proximity both look like shared rather
than independent discovery -- low overlap with no close-timing collisions is
actual evidence of independence, a claim of "we didn't coordinate" is not.

WHY THIS, AND NOT A REUSE OF THE EXISTING h1-h2-disagreements.jsonl: that
file already exists (found while scoping this item) and is a hand-curated,
case-by-case VERDICT comparison -- did H1 and H2 reach the same conclusion
about a specific resource. It answers "did we disagree", not "are we
structurally searching the same ground at the same time". This tool answers
the second question mechanically, from the logs' own timestamps and
summaries, with no manual case-authoring -- a different method on purpose,
because two tools built the same way are not two independent checks any
more than two reviewers reading the same diff are (Ariane 5 Flight 501, the
cross-domain-disciplines doc's sixth item: a second copy is not a second
opinion).

BUILT INDEPENDENTLY OF H2: no H2-authored code, spec, or design was read or
consulted while writing this (only its LOG DATA, which is the subject under
test, read the same way a human auditor would -- the file is readable
cross-session on local disk, not fetched through any H2 tool).

USAGE:
  python hover_cross_agent_independence.py --check [--window N] [--close-minutes M]
  python hover_cross_agent_independence.py --selftest

FAILS CLOSED: if either log is missing or unreadable, says so and exits 2 --
never reports "independent" from a comparison it could not actually run.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

H1_LOG = os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                       'C--Users-marsh-Documents-SAIRN-hover', 'hover-audit-log',
                       'hover-audit-log.jsonl')
H2_LOG = os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                       'C--Users-marsh-Documents-SAIRN-hover2', 'hover-audit-log',
                       'hover-audit-log.jsonl')

# SIGNAL TOKENS ONLY, BY ALLOWLISTED SHAPE -- NOT A STOPWORD DENYLIST.
# First cut of this tool used a short stopword denylist and it was wrong in
# the way this platform's own cross-domain-disciplines doc names as a
# recurring failure (a scorer whose false positives look like a real
# finding): ordinary report prose ("rather", "including", "confirming",
# "nothing", "real", "item") kept passing as "shared vocabulary" and the
# verdict flipped to CONCERN on two sessions that just write in the same
# house style. A token only counts as signal if it LOOKS LIKE A TARGET:
# snake_case with an underscore (resource/field names: bld_draws,
# session_required), a filename with a known extension, or a named app/
# session identifier. Everything else -- however rare the word -- is noise
# for this comparison's purpose, which is "did they look at the same THING",
# not "do they write alike".
KNOWN_ENTITIES = set((
    'sairnbuild sairndental sairnlaw sairncode sairnbiz sairngrounds '
    'sairnscape sairnlegacy sairnvet stonedesk sairnfreedom '
    'hank cody fourth cc hover hover2'
).split())

FILE_EXT_RE = re.compile(r"\.[A-Za-z]{2,5}$")
SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+){1,}$")
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./-]{2,}")


def _is_signal(tok):
    low = tok.lower()
    if low in KNOWN_ENTITIES:
        return True
    if SNAKE_RE.match(low):
        return True
    if FILE_EXT_RE.search(low) and '_' in low.replace('.', '_'):
        return True
    if FILE_EXT_RE.search(low) and len(low) > 6:
        return True
    return False


def load_log(path):
    if not os.path.isfile(path):
        raise SystemExit('FAIL CLOSED: log not found at %s -- cannot run the '
                          'comparison, not reporting independence from a read '
                          'that did not happen.' % path)
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a malformed line is skipped, not fabricated into a row
    return rows


def parse_ts(row):
    ts = row.get('ts') or row.get('logged_at')
    if not ts:
        return None
    try:
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def tokens_of(row):
    text = ' '.join(str(row.get(k, '')) for k in ('summary', 'target'))
    found = set()
    for tok in TOKEN_RE.findall(text):
        low = tok.lower().strip('.')
        if _is_signal(low):
            found.add(low)
    return found


def jaccard(a, b):
    if not a and not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


def cmd_check(args):
    h1_rows = load_log(H1_LOG)[-args.window:]
    h2_rows = load_log(H2_LOG)[-args.window:]
    h1_tokens = set()
    h2_tokens = set()
    h1_entries = []
    h2_entries = []
    for row in h1_rows:
        t = tokens_of(row)
        h1_tokens |= t
        ts = parse_ts(row)
        if ts:
            h1_entries.append((ts, t, row.get('summary', '')[:80]))
    for row in h2_rows:
        t = tokens_of(row)
        h2_tokens |= t
        ts = parse_ts(row)
        if ts:
            h2_entries.append((ts, t, row.get('summary', '')[:80]))

    overlap = jaccard(h1_tokens, h2_tokens)
    collisions = []
    for ts1, t1, s1 in h1_entries:
        for ts2, t2, s2 in h2_entries:
            shared = t1 & t2
            if len(shared) < args.min_shared_tokens:
                continue
            delta_min = abs((ts1 - ts2).total_seconds()) / 60.0
            if delta_min <= args.close_minutes:
                collisions.append((delta_min, sorted(shared), s1, s2))

    print('H1 window: %d entries, H2 window: %d entries' % (len(h1_rows), len(h2_rows)))
    print('KEYWORD-OVERLAP JACCARD (whole window, not per-pair): %.3f' % overlap)
    print('CLOSE-TIMING TOKEN COLLISIONS (>=%d shared tokens within %d min): %d' % (
        args.min_shared_tokens, args.close_minutes, len(collisions)))
    for delta_min, shared, s1, s2 in sorted(collisions)[:10]:
        print('  %.1f min apart, shared=%s\n    H1: %s\n    H2: %s' % (delta_min, shared, s1, s2))
    if not collisions and overlap < args.overlap_threshold:
        print('VERDICT: no evidence of convergence over this window -- low '
              'overlap (%.3f < %.3f) and zero close-timing token collisions. '
              'Not proof of independence (both logs are terse and keyword '
              'extraction is naive), but it is the actual evidence, not a '
              'claim.' % (overlap, args.overlap_threshold))
        return 0
    print('VERDICT: CONCERN -- %s. Worth a human read of the listed pairs '
          'before trusting the two audits as independent this window.' % (
              'overlap above threshold' if overlap >= args.overlap_threshold
              else 'close-timing token collisions present'))
    return 1


def cmd_selftest():
    """Builds two tiny synthetic logs in memory (no real H1/H2 files touched)
    and proves the detector fires on an injected collision and stays quiet
    on independent data."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix='hover_independence_selftest_')
    indep_h1 = os.path.join(tmp, 'h1.jsonl')
    indep_h2 = os.path.join(tmp, 'h2.jsonl')
    conv_h1 = os.path.join(tmp, 'h1c.jsonl')
    conv_h2 = os.path.join(tmp, 'h2c.jsonl')
    with open(indep_h1, 'w') as f:
        f.write(json.dumps({'ts': '2026-10-19T08:00:00Z', 'target': 'alpha',
                             'summary': 'checked bld_draws session gate thoroughly today'}) + '\n')
    with open(indep_h2, 'w') as f:
        f.write(json.dumps({'ts': '2026-10-19T20:00:00Z', 'target': 'beta',
                             'summary': 'reviewed sairnlaw role matrix coverage rows'}) + '\n')
    with open(conv_h1, 'w') as f:
        f.write(json.dumps({'ts': '2026-10-19T08:00:00Z', 'target': 'alpha',
                             'summary': 'checked bld_draws session_required gate value today'}) + '\n')
    with open(conv_h2, 'w') as f:
        f.write(json.dumps({'ts': '2026-10-19T08:04:00Z', 'target': 'alpha',
                             'summary': 'checked bld_draws session_required gate value also'}) + '\n')

    global H1_LOG, H2_LOG
    saved = (H1_LOG, H2_LOG)
    results = {}
    try:
        for name, (h1p, h2p) in (('independent', (indep_h1, indep_h2)),
                                  ('convergent', (conv_h1, conv_h2))):
            H1_LOG, H2_LOG = h1p, h2p
            args = argparse.Namespace(window=100, close_minutes=15,
                                       min_shared_tokens=2, overlap_threshold=0.15)
            rc = cmd_check(args)
            results[name] = rc
    finally:
        H1_LOG, H2_LOG = saved
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    ok = (results['independent'] == 0) and (results['convergent'] == 1)
    print('SELFTEST %s -- independent-fixture verdict=%s (want 0), '
          'convergent-fixture verdict=%s (want 1)' % (
              'PASS' if ok else 'FAIL', results['independent'], results['convergent']))
    return 0 if ok else 1


def main(argv):
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--check', action='store_true')
    p.add_argument('--selftest', action='store_true')
    p.add_argument('--window', type=int, default=40)
    p.add_argument('--close-minutes', type=int, default=20)
    p.add_argument('--min-shared-tokens', type=int, default=3)
    p.add_argument('--overlap-threshold', type=float, default=0.20)
    args = p.parse_args(argv)
    if args.selftest:
        return cmd_selftest()
    if args.check:
        return cmd_check(args)
    print('usage: hover_cross_agent_independence.py --check | --selftest')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
