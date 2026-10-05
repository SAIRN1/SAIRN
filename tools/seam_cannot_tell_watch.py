# OWNER: cc
"""tools/seam_cannot_tell_watch.py -- watch the COULD-NOT-TELL count that moved
with nothing watching it.

WHY THIS EXISTS, and it is a measurement rather than a worry.
`tools/sairn_seam_check.py` classifies every forwarding seam into
`api/_lib/auth.js` and friends as CLEAN, NOT-FORWARDED, or COULD-NOT-TELL. Its
own last two lines say, correctly:

    COULD NOT TELL IS NOT A PASS. Each line above names why, and a seam this
    tool cannot read still needs a hand-written test [...]

On 2026-09-28 that count was recorded as 18. On 2026-10-05 it read 19. NOBODY
NOTICED AND NOTHING COULD HAVE. The tool prints a number and exits; no baseline
existed, so a rise was indistinguishable from the same number, and the only
reason the move was seen at all is that two different sessions happened to write
the figure down eight days apart.

THE NUMBER IS NOT THE POINT -- THE NAMES ARE. A watch that compared only counts
would be silent on the case that actually matters: one seam becoming readable
while another becomes unreadable, which holds the total still while moving the
risk. So the baseline stores the SET of (caller -> dependency, reason) and this
reports ADDED and REMOVED separately. A net-zero churn is reported, not hidden.

── IT FAILS CLOSED, AND THAT IS NOT DECORATION (PR 1.11) ───────────────────────
This tool depends on another tool. Every way that dependency can fail is exit 2
COULD NOT RUN, never exit 0:

  * tools/sairn_seam_check.py missing          -> 2, naming it
  * it crashes or times out                    -> 2, with its stderr
  * its summary line cannot be parsed          -> 2, with the line it got
  * the baseline file is missing or unparseable -> 2, with the write command

A wrapper that treated any of those as "no drift" would report a pass it never
performed, and this file would then be the fifth instance of the defect it was
written to watch for.

── IT DOES NOT UPDATE ITS OWN BASELINE ─────────────────────────────────────────
`--propose` PRINTS the new baseline and the command to write it. There is no
flag that writes it. A detector that re-baselines itself on every rise cannot
ever report one -- it is standing discipline 11 (human-gated auto-remediation)
and it is also how a ratchet silently becomes a rubber stamp.

── WHAT IT CANNOT DO, stated here rather than discovered ───────────────────────
  * It cannot tell whether a COULD-NOT-TELL seam is actually broken. The whole
    category means "unreadable by that tool", and unreadable is not unsafe. A
    rise means a new seam needs a HAND-WRITTEN test, not that a bug landed.
  * It inherits sairn_seam_check.py's own blind spots whole. Its denominator is
    that tool's universe, not the set of real seams, and it publishes the
    clean/not-forwarded/could-not-tell triple so the denominator is visible
    rather than implied.
  * A seam that changes REASON while keeping its caller and dependency is
    reported as one removal plus one addition, which is correct but reads as
    churn. The reason text is part of the identity on purpose: "this tool cannot
    read it because roleSet() destructures" and "...because it is behind a
    helper" are different pieces of work.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEAM = os.path.join(REPO, 'tools', 'sairn_seam_check.py')
BASELINE = os.path.join(REPO, 'docs', 'seam-cannot-tell-baseline.json')

# `96 clean, 0 not-forwarded, 19 could-not-tell`
SUMMARY = re.compile(
    r'^\s*(\d+)\s+clean,\s*(\d+)\s+not-forwarded,\s*(\d+)\s+could-not-tell\s*$')
# `  CANNOT TELL api/sd-data.js   -> api/_lib/auth.js   roleSet() makes no ...`
ROW = re.compile(r'^\s*CANNOT TELL\s+(\S+)\s+->\s+(\S+)\s+(.*?)\s*$')

COULD_NOT_RUN = 2


def die_could_not_run(why, detail=''):
    print('COULD NOT RUN -- this is not a pass.')
    print('  ' + why)
    if detail:
        for line in str(detail).rstrip().split('\n')[-12:]:
            print('    ' + line[:200])
    sys.exit(COULD_NOT_RUN)


def run_seam_check():
    if not os.path.isfile(SEAM):
        die_could_not_run(
            'tools/sairn_seam_check.py is not on disk, so no seam was '
            'classified and this watch has nothing to compare. It is named '
            'here rather than skipped: a missing dependency is a third state.')
    try:
        p = subprocess.run([sys.executable, SEAM], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=600)
    except subprocess.TimeoutExpired:
        die_could_not_run('tools/sairn_seam_check.py did not finish in 600s.')
    except OSError as e:
        die_could_not_run('tools/sairn_seam_check.py could not be executed.', e)
    out = (p.stdout or '') + '\n' + (p.stderr or '')
    counts = None
    for line in out.split('\n'):
        m = SUMMARY.match(line)
        if m:
            counts = tuple(int(x) for x in m.groups())
    if counts is None:
        die_could_not_run(
            'tools/sairn_seam_check.py produced no parseable summary line. '
            'Expected "<n> clean, <n> not-forwarded, <n> could-not-tell". '
            'Its format may have changed, and a watch that guessed would be '
            'reporting about nothing.', out)
    rows = []
    for line in out.split('\n'):
        m = ROW.match(line)
        if m:
            rows.append({'caller': m.group(1), 'dependency': m.group(2),
                         'reason': m.group(3)})
    if len(rows) != counts[2]:
        die_could_not_run(
            'the summary says %d could-not-tell and %d CANNOT TELL rows were '
            'parsed. A disagreement between the count and the names means one '
            'of the two is being read wrongly, and reporting either would be '
            'worse than refusing.' % (counts[2], len(rows)), out)
    return counts, rows


def key(r):
    return '%s -> %s :: %s' % (r['caller'], r['dependency'], r['reason'])


def load_baseline():
    if not os.path.isfile(BASELINE):
        die_could_not_run(
            'docs/seam-cannot-tell-baseline.json does not exist, so there is '
            'nothing to compare against. Create it deliberately:\n'
            '      python tools/seam_cannot_tell_watch.py --propose > '
            'docs/seam-cannot-tell-baseline.json')
    try:
        with open(BASELINE, encoding='utf-8') as f:
            b = json.load(f)
    except (ValueError, OSError) as e:
        die_could_not_run('docs/seam-cannot-tell-baseline.json could not be '
                          'read as JSON.', e)
    if 'seams' not in b or 'counts' not in b:
        die_could_not_run('the baseline is missing "seams" or "counts".')
    return b


def propose(counts, rows):
    print(json.dumps({
        '_what': 'The COULD-NOT-TELL seams tools/sairn_seam_check.py reports, '
                 'recorded so a RISE is visible. Written by hand from '
                 '`--propose`; this file is never updated by the watch itself, '
                 'because a detector that re-baselines its own rise can never '
                 'report one.',
        '_how_to_update': 'python tools/seam_cannot_tell_watch.py --propose > '
                          'docs/seam-cannot-tell-baseline.json  -- and say in '
                          'the commit WHY each added seam is accepted.',
        '_not_a_claim': 'COULD-NOT-TELL means unreadable by that tool, not '
                        'unsafe. A rise means a new seam needs a hand-written '
                        'test; it does not mean a defect landed.',
        'counts': {'clean': counts[0], 'not_forwarded': counts[1],
                   'could_not_tell': counts[2],
                   'total_seams': counts[0] + counts[1] + counts[2]},
        'seams': sorted(key(r) for r in rows),
    }, indent=2))


def main(argv):
    counts, rows = run_seam_check()
    if '--propose' in argv:
        propose(counts, rows)
        return 0

    b = load_baseline()
    was = set(b['seams'])
    now = set(key(r) for r in rows)
    added = sorted(now - was)
    removed = sorted(was - now)

    print('SEAM COULD-NOT-TELL WATCH')
    print('  denominator, published rather than implied:')
    print('    %d clean, %d not-forwarded, %d could-not-tell  (%d seams total)'
          % (counts[0], counts[1], counts[2], sum(counts)))
    print('    baseline was %d could-not-tell of %d'
          % (b['counts']['could_not_tell'], b['counts'].get('total_seams', 0)))
    print()

    if removed:
        print('  %d seam(s) BECAME READABLE -- reported, not celebrated. A '
              'removal is work somebody did, and it should be in a commit '
              'message somewhere:' % len(removed))
        for k in removed:
            print('    - ' + k[:160])
        print()
    if added:
        print('  %d NEW UNREADABLE SEAM(S). Each needs a hand-written test; '
              'this tool cannot say whether any is broken:' % len(added))
        for k in added:
            print('    + ' + k[:160])
        print()
        print('  If these are accepted, re-baseline DELIBERATELY and say why '
              'per seam:')
        print('    python tools/seam_cannot_tell_watch.py --propose > '
              'docs/seam-cannot-tell-baseline.json')
        return 1

    if removed:
        # Net-DOWN or churn with no additions is not a failure, and is not
        # silence either: the baseline now overstates the gap.
        print('  No new unreadable seam. The baseline is now STALE IN THE SAFE '
              'DIRECTION -- it lists seams that no longer exist, so re-baseline '
              'when convenient.')
        return 0

    print('  No change. %d could-not-tell, same set, name for name.'
          % counts[2])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
