#!/usr/bin/env python
"""Reads docs/BYPASS-LOG.jsonl and reports, per LIVE bypass entry, two
mechanically-checkable facts -- never a judgement on whether bypassing was
wise at decision time.

Own tool, own location. Built 2026-10-06 (H1, batch H, item 5). Design
(goals/non-goals/alternatives) logged to hover-audit-log.jsonl before this
file was written.

PER ENTRY:
  1. TIP INTEGRITY. If the entry recorded a `tip` sha, does that commit
     still exist in the current git object store? A bypass whose own
     record points at a commit later rebased/amended away cannot be
     checked against what it actually shipped.
  2. FOLLOW-THROUGH. For a SCOPED bypass (not blanket) whose `command`
     text names a file (a `git add <path>` or similar), does any LATER
     commit (by timestamp) touch that same file? A crude, named-as-crude
     proxy for "was the thing this check guards addressed afterward" --
     true follow-through verification would mean reading every later
     commit's actual content, which this tool does not do.

THIRD STATE, NOT TWO: COULD_NOT_TELL is distinct from both "integrity
holds" and "integrity broken" -- an entry with no `tip` recorded has
nothing to check (COULD_NOT_TELL, not PASS), and a BLANKET bypass has no
single check to look for follow-through on (NOT_APPLICABLE, not FAIL).

CANNOT SEE, NAMED RATHER THAN SILENTLY ASSUMED COMPLETE:
  - --no-verify or any override NOT written to this log. Trusts the log is
    the complete record of every bypass, which is only true if every push
    path actually writes to it.
  - Whether the STATED REASON was true at decision time -- only whether a
    recorded tip still resolves and whether a named file was touched later.
  - A RETRACTION (check: "(RETRACTION)") is read but not scored as a live
    bypass -- it is itself the record of a correction, not a new one.
"""
import json
import os
import re
import subprocess
import sys

REPO = r'C:\Users\marsh\Documents\SAIRN-hover'
LOG_PATH = os.path.join(REPO, 'docs', 'BYPASS-LOG.jsonl')

FILE_IN_COMMAND_RE = re.compile(r'\b(?:tools|api|tests|docs|sql)/[\w./-]+\.\w+')


def _git(args, cwd=REPO):
    p = subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def load_log(path=LOG_PATH):
    if not os.path.isfile(path):
        return None, 'BYPASS-LOG.jsonl not found at %s' % path
    entries = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                return None, 'line %d unparseable: %s' % (i, e)
    return entries, None


def check_tip_integrity(entry):
    tip = entry.get('tip')
    if not tip:
        return 'COULD_NOT_TELL', 'no tip sha recorded'
    rc, _out, _err = _git(['cat-file', '-e', tip])
    if rc == 0:
        return 'HOLDS', 'tip %s exists' % tip[:12]
    return 'BROKEN', 'tip %s does not resolve in the current object store' % tip[:12]


def check_follow_through(entry, all_commits_after):
    if entry.get('blanket'):
        return 'NOT_APPLICABLE', 'blanket bypass names no single check to follow up on'
    cmd = entry.get('command') or ''
    files = FILE_IN_COMMAND_RE.findall(cmd)
    if not files:
        return 'COULD_NOT_TELL', 'no file path found in the recorded command text'
    for sha, files_touched in all_commits_after:
        for f in files:
            if f in files_touched:
                return 'FOLLOWED_UP', 'later commit %s touches %s' % (sha[:12], f)
    return 'NO_LATER_TOUCH_FOUND', 'named file(s) %s: no later commit found touching any of them' % files


_COMMITS_AFTER_CACHE = {}
MAX_COMMITS_AFTER = 500


def _commits_after(ts_iso):
    """All commits after ts_iso, each as (sha, set-of-files-touched).
    ONE git call, not one per commit -- the first version shelled out
    `git show` per commit and a fixture dated 2020 (this tool's own
    selftest) walked the ENTIRE repo history one subprocess at a time and
    timed out past 120s. `git log --name-only` in a SINGLE call returns the
    same information; parsed by blank-line-separated groups, each starting
    with a commit sha line. Capped at MAX_COMMITS_AFTER (oldest truncated,
    named in the result) so a bypass from early in a long repo's life does
    not repeat the same cost."""
    if ts_iso in _COMMITS_AFTER_CACHE:
        return _COMMITS_AFTER_CACHE[ts_iso]
    rc, out, _err = _git(['log', '--since=' + ts_iso, '--name-only',
                           '--pretty=format:@@%H', '-n', str(MAX_COMMITS_AFTER), 'main'])
    result = []
    if rc == 0 and out:
        for block in out.split('@@')[1:]:
            lines = block.strip().splitlines()
            if not lines:
                continue
            sha = lines[0].strip()
            files = set(l.strip() for l in lines[1:] if l.strip())
            result.append((sha, files))
    _COMMITS_AFTER_CACHE[ts_iso] = result
    return result


def review(path=LOG_PATH):
    entries, err = load_log(path)
    if entries is None:
        return {'error': err}
    live = [e for e in entries if e.get('check') != '(RETRACTION)']
    results = []
    for e in live:
        tip_state, tip_reason = check_tip_integrity(e)
        after = _commits_after(e['at']) if e.get('at') else []
        ft_state, ft_reason = check_follow_through(e, after)
        results.append({
            'at': e.get('at'), 'session': e.get('session'), 'check': e.get('check'),
            'blanket': e.get('blanket'), 'reason': e.get('reason'),
            'tip_integrity': tip_state, 'tip_detail': tip_reason,
            'follow_through': ft_state, 'follow_through_detail': ft_reason,
        })
    return {'total_entries': len(entries), 'live_reviewed': len(live), 'results': results}


# ---------------------------------------------------------------------------
# Selftest: a planted fixture with a known-broken tip and a known-missing
# follow-through, so both real checks are proven to fire, not just read.
# ---------------------------------------------------------------------------

def _selftest():
    import tempfile
    fixture = [
        {'at': '2020-01-01T00:00:00Z', 'session': 'fixture', 'check': 'planted',
         'blanket': False, 'command': 'git add tools/does_not_exist_fixture.py && git push',
         'tip': '0000000000000000000000000000000000ffff', 'reason': 'planted fixture'},
        {'at': '2020-01-01T00:00:00Z', 'session': 'fixture', 'check': '(RETRACTION)',
         'blanket': False, 'command': None, 'tip': None, 'reason': 'planted retraction, must not be scored'},
    ]
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        for e in fixture:
            f.write(json.dumps(e) + '\n')
    try:
        report = review(path)
        ok = 0
        total = 3
        if report['total_entries'] == 2:
            ok += 1
            print('  ok   total_entries counts the retraction too (2)')
        else:
            print('  FAIL total_entries expected 2, got %r' % report['total_entries'])
        if report['live_reviewed'] == 1:
            ok += 1
            print('  ok   live_reviewed excludes the retraction (1)')
        else:
            print('  FAIL live_reviewed expected 1, got %r' % report['live_reviewed'])
        r = report['results'][0]
        if r['tip_integrity'] == 'BROKEN':
            ok += 1
            print('  ok   planted fake tip correctly reported BROKEN')
        else:
            print('  FAIL planted fake tip expected BROKEN, got %r' % r['tip_integrity'])
        print('%d/%d fixture checks correct' % (ok, total))
        return ok == total
    finally:
        os.remove(path)


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    report = review()
    if 'error' in report:
        print('COULD NOT RUN: %s' % report['error'])
        return 2
    print('AUDIT-TRAIL REVIEW -- %d total entries, %d live (excludes retractions)'
          % (report['total_entries'], report['live_reviewed']))
    broken = [r for r in report['results'] if r['tip_integrity'] == 'BROKEN']
    unfollowed = [r for r in report['results'] if r['follow_through'] == 'NO_LATER_TOUCH_FOUND']
    for r in report['results']:
        print('  %s  %-8s %-10s tip=%-16s follow=%s'
              % (r['at'], r['session'], r['check'] or '-', r['tip_integrity'], r['follow_through']))
        if r['tip_integrity'] == 'BROKEN':
            print('      ! %s' % r['tip_detail'])
        if r['follow_through'] == 'NO_LATER_TOUCH_FOUND':
            print('      ! %s' % r['follow_through_detail'])
    print('%d broken tip(s), %d with no later touch found' % (len(broken), len(unfollowed)))
    return 1 if (broken or unfollowed) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
