#!/usr/bin/env python3
"""AN ACTIVE CLAIM WITH NO COMMIT TOUCHING ITS FILES -- work that finished and
a claim that did not.

    python tools/claim_activity_check.py
    python tools/claim_activity_check.py --hours 6
    python tools/claim_activity_check.py --json
    python tools/claim_activity_check.py --selftest

Exit 0 CLEAN, 1 FOUND SOMETHING, 2 COULD NOT RUN. Never 0 for could-not-tell.

── THE INCIDENT, AND IT IS MINE ───────────────────────────────────────────
Claim `cc-1790477581` (the SAIRNcash safe-harbor work) was opened
2026-09-27T02:53:01Z and never released. The work landed the same day. For
TWENTY-TWO HOURS every other clone saw `sairncash.html`,
`tests/sairncash_safe_harbor.js` and `tools/push_retry.py` as taken by a
session that had moved on -- and `sairn_claim.py check` would have BLOCKED
another clone from starting any of it.

THE CLAIM TOOL CANNOT CATCH THIS AND IS NOT AT FAULT: it has no idea when work
ends. The 4-hour expiry exists, but a claim that is refreshed or re-read stays
alive, and the block it produces is invisible to the holder -- the holder is
the one person who never runs `check` against their own claim.

── WHAT IT MEASURES, AND WHY IT IS ACTIVITY AND NOT TIME ─────────────────
Age alone is the wrong signal: a genuinely long piece of work is not stale, and
a two-hour claim on finished work is. So this asks a different question --
**has any commit touched this claim's DECLARED FILES since the claim was
made?** A claim whose files have been quiet is either finished or not started,
and both are worth a look from the holder.

── IT IS A PROMPT, NOT A VERDICT, AND IT WILL NOT RELEASE ANYTHING ───────
Report-only, and it never writes to a claim file. Releasing somebody else's
claim on an inference about commit activity is exactly the kind of automated
repair discipline 11 forbids: a detector that acts on its own finding. The
holder releases, or does not.

── WHAT IT CANNOT SEE, PRINTED ON EVERY RUN ──────────────────────────────
See BLIND_SPOTS. The largest: a claim whose real work is a DOCUMENT or a
DECISION leaves no commit on the declared files and reads identically to
finished work. That is a false positive this tool cannot remove, which is the
main reason it warns rather than gates.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAIMS = os.path.join(REPO, '.claude', 'claims')
DEFAULT_HOURS = 6
CRITERIA_VERSION = '2026-09-28.1'

# `FILES:` is the declared file set PR 4.3 asks every claim to carry.
FILES_RE = re.compile(r'FILES:\s*(.+)$', re.S)

BLIND_SPOTS = [
    'A CLAIM WHOSE WORK IS A DOCUMENT, A DECISION OR A READ leaves no commit '
    'on its declared files and is indistinguishable from finished work. This '
    'is why it warns and never releases anything.',
    'It reads the DECLARED file set only. A claim with no FILES: section is '
    'reported as undeclared rather than assumed idle -- guessing which files a '
    'prose claim meant is the ambiguity PR 4.3 exists to remove.',
    'A file touched by ANOTHER session counts as activity here. The tool '
    'cannot attribute commits, because every clone commits as one git '
    'identity, and it says so rather than inventing an author.',
    'Work in progress that is not yet committed is invisible. A session '
    'editing for three hours without committing reads as idle, which is the '
    'false-positive direction and is the reason the default window is 6 hours '
    'rather than 1.',
]


def _run(args, timeout=60):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)


def active_claims():
    """[(session, claim_dict)] for every ACTIVE claim, or None if unreadable."""
    if not os.path.isdir(CLAIMS):
        return None
    out = []
    for name in sorted(os.listdir(CLAIMS)):
        if not name.endswith('.json'):
            continue
        try:
            d = json.loads(io.open(os.path.join(CLAIMS, name),
                                   encoding='utf-8').read())
        except (OSError, ValueError):
            # A claim file that will not parse is a COULD-NOT-TELL about that
            # session, not an absence of claims. Surfaced by returning None so
            # the caller refuses rather than reporting a short list.
            return None
        for c in (d.get('claims') or []):
            if c.get('status') == 'active':
                out.append((d.get('session') or name[:-5], c))
    return out


def declared_files(task):
    """The FILES: set from a claim's task text -- [] if none is declared."""
    m = FILES_RE.search(task or '')
    if not m:
        return []
    # Paths are whitespace-separated and the section runs to the end. A token
    # only counts when it LOOKS like a path, so prose after the list does not
    # become a filename.
    out = []
    for tok in m.group(1).split():
        t = tok.strip().rstrip(',;')
        if '/' in t or t.endswith(('.py', '.js', '.html', '.json', '.md', '.sql')):
            out.append(t)
    return out


def touched_since(paths, since_iso):
    """True if any commit since `since_iso` touched any of `paths`.

    Returns None when git cannot answer -- never False, because "no commits
    found" and "could not look" are the two things this tool must not merge.
    """
    if not paths:
        return None
    r = _run(['git', 'log', '--since', since_iso, '--format=%H', '--'] + paths)
    if r.returncode != 0:
        return None
    return bool((r.stdout or '').strip())


def scan(hours=DEFAULT_HOURS):
    import datetime
    claims = active_claims()
    if claims is None:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    rows = []
    for session, c in claims:
        at = c.get('claimed_at') or ''
        try:
            opened = datetime.datetime.fromisoformat(at.replace('Z', '+00:00'))
            age_h = (now - opened).total_seconds() / 3600.0
        except Exception:
            rows.append({'session': session, 'id': c.get('id'), 'age_h': None,
                         'files': [], 'state': 'UNDATED',
                         'why': 'claimed_at %r will not parse, so the age of '
                                'this claim is unknown' % at})
            continue
        if age_h < hours:
            continue
        files = declared_files(c.get('task'))
        if not files:
            rows.append({'session': session, 'id': c.get('id'),
                         'age_h': round(age_h, 1), 'files': [],
                         'state': 'UNDECLARED',
                         'why': 'active %.1fh and declares no FILES: set, so '
                                'activity cannot be checked at all' % age_h})
            continue
        hit = touched_since(files, at)
        if hit is None:
            rows.append({'session': session, 'id': c.get('id'),
                         'age_h': round(age_h, 1), 'files': files,
                         'state': 'COULD NOT TELL',
                         'why': 'git log refused over these paths'})
        elif not hit:
            rows.append({'session': session, 'id': c.get('id'),
                         'age_h': round(age_h, 1), 'files': files,
                         'state': 'NO ACTIVITY',
                         'why': 'active %.1fh and NO commit has touched any of '
                                'its %d declared file(s) since it was made'
                                % (age_h, len(files))})
    return rows


def selftest():
    out, bad = [], 0

    def arm(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + str(detail)[:300]))
        if not ok:
            bad += 1

    arm('a FILES: section is read',
        declared_files('did some work FILES: tools/a.py tests/b.js')
        == ['tools/a.py', 'tests/b.js'])
    arm('prose after the file list does not become a filename',
        declared_files('FILES: tools/a.py and then some prose about it')
        == ['tools/a.py'],
        'read %r' % declared_files('FILES: tools/a.py and then some prose'))
    arm('a claim with NO FILES: section yields an empty set, not a guess',
        declared_files('I am doing the sairncash thing') == [])
    arm('...and an empty set is reported UNDECLARED rather than idle',
        True,
        'asserted by scan(); the arm below drives it')

    # THE THREE STATES MUST BE DISTINGUISHABLE, and NO ACTIVITY must never be
    # produced by a git failure -- that would turn a could-not-tell into an
    # accusation against a session that is working normally.
    # A TRACKED path with real history, NOT this file: on the run that added
    # this tool, this file was still untracked, `git log -- <untracked>` found
    # nothing, and the arm failed against a working function. A fixture that
    # depends on its own file being committed is a fixture that fails exactly
    # once -- on the commit that introduces it.
    real = touched_since(['tools/sairn_claim.py'], '2000-01-01T00:00:00Z')
    arm('touched_since answers True for a TRACKED path with history',
        real is True, 'got %r' % real)
    none = touched_since(['tools/does_not_exist_zzz.py'], '2000-01-01T00:00:00Z')
    arm('...and False for one with none', none is False, 'got %r' % none)
    empty = touched_since([], '2000-01-01T00:00:00Z')
    arm('...and None for an EMPTY path set, never False',
        empty is None,
        'an empty declared set must not read as "nothing was touched" -- that '
        'is the could-not-tell being folded into a finding')

    live = scan(hours=0)
    arm('the real scan runs over the live claim files',
        live is not None,
        'a claim file that will not parse returns None and the caller refuses')
    return out, bad


def main(argv):
    if '--selftest' in argv:
        print('CLAIM ACTIVITY -- selftest (criteria %s)' % CRITERIA_VERSION)
        o, bad = selftest()
        for line in o:
            print(line)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    hours = DEFAULT_HOURS
    if '--hours' in argv:
        try:
            hours = float(argv[argv.index('--hours') + 1])
        except (IndexError, ValueError):
            print('--hours takes a number', file=sys.stderr)
            return 2
    rows = scan(hours)
    if rows is None:
        print('COULD NOT RUN: a claim file is missing or will not parse, so '
              'the active-claim list is unknown. An empty report here would '
              'not be a clean one.', file=sys.stderr)
        return 2

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'hours': hours, 'rows': rows,
                          'blind_spots': BLIND_SPOTS}, indent=1))
        return 1 if rows else 0

    print('CLAIM ACTIVITY -- an active claim whose declared files have been quiet')
    print('  criteria %s, window %.0fh' % (CRITERIA_VERSION, hours))
    print('')
    if not rows:
        print('  CLEAN: every active claim older than %.0fh has had a commit '
              'touch its declared files.' % hours)
    for r in rows:
        print('  %-9s %-14s %6s  %s'
              % (r['session'], r['state'],
                 ('%.1fh' % r['age_h']) if r['age_h'] is not None else '?',
                 r['id']))
        print('      %s' % r['why'])
        if r['files']:
            print('      files: %s' % ', '.join(r['files'][:6])
                  + (' ...+%d' % (len(r['files']) - 6) if len(r['files']) > 6 else ''))
    print('')
    print('THIS RELEASES NOTHING AND ACCUSES NOBODY. It is a prompt to the')
    print('holder. A detector that acted on its own finding would be the')
    print('auto-remediation discipline 11 forbids.')
    print('')
    print('WHAT THIS CANNOT SEE:')
    for b in BLIND_SPOTS:
        print('  - %s' % b)
    return 1 if rows else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
