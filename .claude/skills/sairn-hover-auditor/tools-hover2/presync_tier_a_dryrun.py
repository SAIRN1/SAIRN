#!/usr/bin/env python
"""presync_tier_a_dryrun.py -- before an auditor tool is synced into the
platform repo, predict whether it will TRIP the Tier A push gate, so the
obligation can be opened deliberately instead of discovered at push time.

WHY THIS EXISTS. Twice this session (self-log seq 416, 422) an auditor tool
landed at .claude/skills/sairn-hover-auditor/tools-hover2/ and the push gate
refused it because a plain word in the tool -- "leg_insurance", "quotes" --
is also a Tier A resource NAME. The gate cannot tell a mention-token in a
checker's fixture from a handler's serving token (it says so itself). Until
that gate is taught to skip the auditor tree (routed to hank, seq of this
dispatch), the auditor can at least run the gate's OWN logic in dry-run on a
candidate file first and know what to expect.

HOW. It imports the REAL gate module from the repo -- tools/
tier_a_review_gate.py -- so it cannot drift from the gate's actual behaviour:
it reuses tier_a_resources() (the live Tier A list from CRITICALITY-TIERS.md),
touched_tier_a() (the real diff-scan), and skip_reason() (the real path
exclusions). The candidate file's content is framed as an all-added diff at
the intended DESTINATION path, which is exactly what the gate sees at push.

REPORT-ONLY, READ-ONLY. It reads the repo; it writes nothing, syncs nothing,
and opens no obligation -- naming what WOULD trip is the point.

    python presync_tier_a_dryrun.py <candidate.py> [--dest <repo-rel-path>]
    python presync_tier_a_dryrun.py --selftest
"""
import io
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = r'C:\Users\marsh\Documents\SAIRN-hover2'
DEST_PREFIX = '.claude/skills/sairn-hover-auditor/tools-hover2/'


def _load_gate(repo=DEFAULT_REPO):
    path = os.path.join(repo, 'tools', 'tier_a_review_gate.py')
    if not os.path.isfile(path):
        raise RuntimeError('COULD NOT RUN: the gate is not at %s -- cannot '
                           'predict what it cannot be loaded from' % path)
    sys.path.insert(0, os.path.join(repo, 'tools'))
    spec = importlib.util.spec_from_file_location('tier_a_review_gate', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _as_added_diff(dest_path, content):
    """Frame file content as a unified diff of all-added lines at dest_path --
    what the gate sees for a newly-synced file."""
    lines = ['+++ b/%s' % dest_path, '@@ -0,0 +1 @@']
    lines += ['+' + ln for ln in content.splitlines()]
    return '\n'.join(lines) + '\n'


def predict(content, dest_path, gate):
    """Return (would_trip: bool, resources: list, skip: str|None)."""
    skip = gate.skip_reason(dest_path)
    if skip is not None:
        return False, [], skip
    resources = gate.tier_a_resources()
    diff = _as_added_diff(dest_path, content)
    hits = gate.touched_tier_a(diff, resources)
    return (bool(hits), sorted(hits.keys()), None)


def run(candidate, dest, repo=DEFAULT_REPO):
    gate = _load_gate(repo)
    content = io.open(candidate, encoding='utf-8', errors='replace').read()
    return predict(content, dest, gate)


# ── FIXTURE, blind-locked: a stub gate so the selftest needs no repo ────────
class _StubGate:
    """Mimics the three real gate entry points on a tiny fixed Tier A set."""
    _TIER_A = {'leg_insurance', 'quotes', 'sv_soapnotes'}

    def skip_reason(self, dest):
        d = dest.replace('\\', '/')
        if d.startswith('docs/') or d.endswith('.md'):
            return 'prose'
        return None

    def tier_a_resources(self):
        return set(self._TIER_A)

    def touched_tier_a(self, diff, resources):
        import re
        hits = {}
        for line in diff.split('\n'):
            if not line.startswith('+'):
                continue
            for r in resources:
                if re.search(r'(?<![A-Za-z0-9_])' + re.escape(r) + r'(?![A-Za-z0-9_])', line):
                    hits.setdefault(r, []).append('x')
        return hits


def selftest():
    bad = []
    g = _StubGate()

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    trip, res, skip = predict("POOL = ['leg_insurance', 'quotes']\n",
                              DEST_PREFIX + 'hover_x.py', g)
    ck('a tool naming Tier A resources, destined for the auditor tree, is '
       'predicted to TRIP and names which resources',
       trip is True and res == ['leg_insurance', 'quotes'] and skip is None)
    trip2, res2, _ = predict("POOL = ['sd_jobs', 'grd_zones']\n",
                             DEST_PREFIX + 'hover_y.py', g)
    ck('KNOWN-BAD CONTROL: a tool naming only NON-Tier-A resources does NOT '
       'trip', trip2 is False and res2 == [])
    trip3, _, skip3 = predict("names leg_insurance in prose\n",
                             'docs/some-note.md', g)
    ck('KNOWN-BAD CONTROL: a docs/.md destination is predicted SKIPPED (the '
       'gate excludes prose), so it would not trip even naming a resource',
       trip3 is False and skip3 is not None)
    if bad:
        print('%d of 3 selftest arm(s) failed' % len(bad))
        return 1
    print('OK -- 3 arms passed')
    return 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    args = [a for a in argv if not a.startswith('--')]
    if not args:
        print('usage: presync_tier_a_dryrun.py <candidate.py> [--dest <repo-rel-path>]')
        return 2
    candidate = args[0]
    dest = DEST_PREFIX + os.path.basename(candidate)
    if '--dest' in argv:
        dest = argv[argv.index('--dest') + 1]
    try:
        trip, resources, skip = run(candidate, dest)
    except RuntimeError as e:
        print(str(e))
        return 2
    print('PRE-SYNC TIER A DRY-RUN -- report only, nothing synced')
    print('  candidate : %s' % candidate)
    print('  dest      : %s' % dest)
    if skip is not None:
        print('  WOULD NOT TRIP -- the gate skips this path: %s' % skip)
        return 0
    if not trip:
        print('  WOULD NOT TRIP -- no Tier A resource name found in the content')
        return 0
    print('  WOULD TRIP -- these Tier A resource NAME(s) appear as tokens the '
          'gate reads as a touch:')
    for r in resources:
        print('    ! %s' % r)
    print('\n  Open the obligation deliberately BEFORE syncing '
          '(tools/tier_a_review_gate.py --open), or route the gate-skip fix '
          '(this session\'s hank finding) so the auditor tree is excluded.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
