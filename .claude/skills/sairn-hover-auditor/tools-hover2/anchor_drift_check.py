#!/usr/bin/env python
"""anchor_drift_check.py (batch b12) -- report-only check that every
line number this role has cited in a routing doc still points at the
real code it claimed to, by resolving each citation against a STABLE
ANCHOR (an exact text snippet drawn from the citation's own context --
a symbol name, a distinctive substring) rather than trusting the line
number alone.

WHY THIS EXISTS. api/sd-data.js is edited often enough that a line
number cited in a routing doc routinely drifts within a few batches --
bld_draws moved +231 lines between b11 and b12 alone (two unrelated
upstream edits in a row). A stale line number that nobody re-derives
reads as a confident, specific citation while actually pointing at the
wrong code -- the exact "a truncated/stale read is indistinguishable
from a correct one" shape this role's own discipline exists to catch,
now turned on this role's OWN citations rather than only a platform
claim.

WHAT IT DOES, and does not. For each (file, anchor_text, claimed_line)
triple, this greps the CURRENT file for the anchor text (an exact
substring match, not a regex -- a symbol name or a distinctive snippet
is specific enough on its own and a regex adds a failure mode this
checker does not need). Three outcomes:
  MATCH         -- the anchor is found at exactly the claimed line.
  DRIFTED       -- the anchor is found, but at a DIFFERENT line (the
                   real, current line is reported so a routing doc can
                   be corrected from this tool's own output).
  NOT FOUND     -- the anchor does not appear anywhere in the current
                   file at all (the code may have been removed, or the
                   anchor text itself may be wrong -- this tool cannot
                   tell which, and says so rather than guessing).
AMBIGUOUS (not a fourth state, a qualifier on MATCH/DRIFTED): if the
anchor appears on more than one line, every matching line is listed
and the claimed line is checked against the set, because a non-unique
anchor could silently match the wrong occurrence.

REPORT-ONLY, ALWAYS. This never edits a routing doc, never edits
api/sd-data.js, never edits anything. It prints a table and exits 0 on
clean (every claim MATCH) or 1 when at least one DRIFTED/NOT FOUND
entry exists -- the exit code is a SUMMARY signal for scripting, not a
pass/fail judgment on the underlying finding (a DRIFTED citation can
still be a real, open finding; only its LINE NUMBER is stale).

Run:
  python anchor_drift_check.py [--repo PATH]
  python anchor_drift_check.py --selftest
"""
import argparse
import os
import sys

DEFAULT_REPO = 'C:/Users/marsh/Documents/SAIRN-hover2'

# ── THE ROUTED-FINDING ANCHOR TABLE, batch b12 ──────────────────────────
# One entry per citation this role has actually made in a routing doc
# this batch. `anchor` is an exact substring pulled from the real source
# at the time it was last confirmed -- not re-typed from memory, copied
# from the grep output that confirmed it. Extend this table whenever a
# new citation is made; it is not meant to cover every citation ever
# made, only the ones a future drift pass should watch.
ANCHOR_TABLE = [
    {
        'label': 'bld_draws generic write branch (fix point)',
        'file': 'api/sd-data.js',
        'anchor': "if (BLD_RESOURCES[resource] && action === 'write') {",
        'claimed_line': 13239,
    },
    {
        'label': 'bld_draws BLD_BID_MANAGEMENT_ROLES definition',
        'file': 'api/sd-data.js',
        'anchor': "const BLD_BID_MANAGEMENT_ROLES = roleSet({ owner: true, office: true });",
        'claimed_line': 5642,
    },
    {
        'label': 'sairncash subscriptionId-branch ownership check (FIXED b12)',
        'file': 'api/sairncash/verify.js',
        'anchor': 'THE MINT ON THIS BRANCH NOW REQUIRES A SECOND IDENTIFIER',
        'claimed_line': 117,
    },
    {
        'label': 'scp_jobs read dispatch',
        'file': 'api/sd-data.js',
        'anchor': "if (resource === 'scp_jobs' && action === 'read') {",
        'claimed_line': 5130,
    },
    {
        'label': 'scp_water_features write dispatch',
        'file': 'api/sd-data.js',
        'anchor': "if (resource === 'scp_water_features' && action === 'write') {",
        'claimed_line': 5343,
    },
    {
        'label': 'law_clients/matters/deadlines SD_SESSION_GATED entries',
        'file': 'api/sd-data.js',
        'anchor': "'law_clients': ['read', 'write'],",
        'claimed_line': 1214,
    },
    {
        'label': 'sf_officers SD_SESSION_GATED entry (FIXED)',
        'file': 'api/sd-data.js',
        'anchor': "'sf_officers':            ['read', 'write'],",
        'claimed_line': 1089,
    },
    {
        'label': 'SV_RESOURCES dict declaration',
        'file': 'api/sd-data.js',
        'anchor': 'const SV_RESOURCES = {',
        'claimed_line': 13399,
    },
]


def check_one(repo, entry):
    path = os.path.join(repo, entry['file'])
    if not os.path.isfile(path):
        return {'status': 'COULD_NOT_RUN', 'detail': '%s not found' % path,
                'matches': []}
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    matches = [i + 1 for i, l in enumerate(lines) if entry['anchor'] in l]
    if not matches:
        return {'status': 'NOT_FOUND', 'detail': None, 'matches': []}
    if entry['claimed_line'] in matches:
        status = 'MATCH' if len(matches) == 1 else 'MATCH_AMBIGUOUS'
    else:
        status = 'DRIFTED' if len(matches) == 1 else 'DRIFTED_AMBIGUOUS'
    return {'status': status, 'detail': None, 'matches': matches}


def run(repo, table=None, out=print):
    table = ANCHOR_TABLE if table is None else table
    any_bad = False
    for entry in table:
        r = check_one(repo, entry)
        if r['status'] == 'COULD_NOT_RUN':
            out('%-55s COULD_NOT_RUN  %s' % (entry['label'], r['detail']))
            any_bad = True
        elif r['status'] == 'NOT_FOUND':
            out('%-55s NOT_FOUND (claimed :%d, anchor absent from current file)'
                % (entry['label'], entry['claimed_line']))
            any_bad = True
        elif r['status'].startswith('MATCH'):
            tag = 'MATCH' if r['status'] == 'MATCH' else (
                'MATCH (AMBIGUOUS -- also at %s)' %
                [m for m in r['matches'] if m != entry['claimed_line']])
            out('%-55s %s :%d' % (entry['label'], tag, entry['claimed_line']))
        else:
            tag = 'DRIFTED' if r['status'] == 'DRIFTED' else (
                'DRIFTED (AMBIGUOUS, candidates %s)' % r['matches'])
            out('%-55s %s -- claimed :%d, real :%s'
                % (entry['label'], tag, entry['claimed_line'],
                   r['matches'][0] if len(r['matches']) == 1 else r['matches']))
            any_bad = True
    return 1 if any_bad else 0


def _selftest():
    import tempfile
    scratch = tempfile.mkdtemp()
    os.makedirs(os.path.join(scratch, 'api'))
    fixture_path = os.path.join(scratch, 'api', 'sd-data.js')

    # CONTROL PAIR (a): plant a drift -- anchor present but at a line
    # different from what is claimed. Must fire (exit 1, DRIFTED).
    with open(fixture_path, 'w', encoding='utf-8') as f:
        f.write('\n' * 10)
        f.write("if (resource === 'fx_moved' && action === 'write') {\n")
        f.write('}\n')
    drift_table = [{'label': 'fx_moved', 'file': 'api/sd-data.js',
                     'anchor': "if (resource === 'fx_moved' && action === 'write') {",
                     'claimed_line': 1}]
    out1 = []
    rc1 = run(scratch, drift_table, out=out1.append)
    drift_fires = (rc1 == 1 and any('DRIFTED' in l for l in out1))

    # CONTROL PAIR (b): plant clean -- anchor present at exactly the
    # claimed line. Must stay silent (exit 0, MATCH).
    clean_table = [{'label': 'fx_moved', 'file': 'api/sd-data.js',
                     'anchor': "if (resource === 'fx_moved' && action === 'write') {",
                     'claimed_line': 11}]
    out2 = []
    rc2 = run(scratch, clean_table, out=out2.append)
    clean_silent = (rc2 == 0 and all('DRIFTED' not in l and 'NOT_FOUND' not in l
                                      for l in out2))

    # (c) NOT_FOUND: anchor genuinely absent.
    missing_table = [{'label': 'fx_absent', 'file': 'api/sd-data.js',
                       'anchor': 'this text does not exist anywhere',
                       'claimed_line': 1}]
    out3 = []
    rc3 = run(scratch, missing_table, out=out3.append)
    not_found_fires = (rc3 == 1 and any('NOT_FOUND' in l for l in out3))

    # (d) AMBIGUOUS: anchor appears twice, claimed line matches one of
    # them -- must still report MATCH (AMBIGUOUS...), not silently drop
    # the other occurrence.
    with open(fixture_path, 'w', encoding='utf-8') as f:
        f.write("const DUP = 1;\n")
        f.write("const DUP = 1;\n")
    dup_table = [{'label': 'fx_dup', 'file': 'api/sd-data.js',
                  'anchor': 'const DUP = 1;', 'claimed_line': 1}]
    out4 = []
    run(scratch, dup_table, out=out4.append)
    ambiguous_reported = any('AMBIGUOUS' in l for l in out4)

    # (e) COULD_NOT_RUN: file genuinely absent -- fail closed, not silent.
    missing_file_table = [{'label': 'fx_no_file', 'file': 'api/does-not-exist.js',
                            'anchor': 'anything', 'claimed_line': 1}]
    out5 = []
    rc5 = run(scratch, missing_file_table, out=out5.append)
    could_not_run_fires = (rc5 == 1 and
                            any('COULD_NOT_RUN' in l for l in out5))

    ok = (drift_fires and clean_silent and not_found_fires and
          ambiguous_reported and could_not_run_fires)
    print('SELFTEST %s: drift_fires=%r clean_silent=%r not_found_fires=%r '
          'ambiguous_reported=%r could_not_run_fires=%r'
          % ('PASS' if ok else 'FAIL', drift_fires, clean_silent,
             not_found_fires, ambiguous_reported, could_not_run_fires))
    import shutil
    shutil.rmtree(scratch, ignore_errors=True)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=DEFAULT_REPO)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    return run(args.repo)


if __name__ == '__main__':
    sys.exit(main())
