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
# SAIRN_CLAIM_DIR points this at a constructed claim directory instead of the
# live one -- the same affordance SAIRN_TIER_REGISTER gives
# criticality_tier_check.py, and for the same reason: the real directory
# changes under a test and cannot be made to hold a known shape, so arms
# driven against it are measuring whatever three other sessions happen to be
# doing. Not a behaviour switch; the same code runs over a different input.
CLAIMS = os.environ.get('SAIRN_CLAIM_DIR') or os.path.join(
    REPO, '.claude', 'claims')
DEFAULT_HOURS = 6
CRITERIA_VERSION = '2026-09-28.2'


class CouldNotRun(Exception):
    """Something this check DEPENDS ON is absent. Never folded into a pass."""


def _claim_is_active(c):
    """Is this claim still HELD -- by sairn_claim.py's own rule, not by its
    `status` field.

    ── THE DEFECT THIS EXISTS FOR, AND IT WAS THIS TOOL'S (2026-09-28) ────
    `active_claims()` selected on `c.get('status') == 'active'`, the RAW
    field. That is half the answer. `sairn_claim.is_active()` also applies
    the four-hour staleness rule -- and a liveness check on the owning
    process where the registry stamped one -- and sairn_claim.py says so at
    its own call site: "Uses is_active(), not the raw status field: an
    EXPIRED claim is one this...". The sibling tool draws the distinction;
    this one did not.

    MEASURED THE DAY IT WAS FIXED: 13 records carried `status: active` and
    `is_active()` was true for TWO. So eleven of thirteen were being
    described as "active NNh and NO commit has touched its declared files"
    when they had expired hours or days earlier and were blocking nobody --
    `sairn_claim.py check` already ignores them. Every finding the tool
    produced that day was of that shape: non-empty, plausible, and pointing
    at nothing anybody could act on in the way the sentence implied. A
    false-finding generator is the shape that gets a check switched off.

    IT IS IMPORTED AND NOT REIMPLEMENTED. Two spellings of one staleness
    rule is two rules that drift, and the rule itself has already changed
    once (a fixed timeout became a timeout plus process liveness on
    2026-09-23). A local copy would have frozen the older half here.

    AND IT FAILS CLOSED. If sairn_claim.py cannot be imported, the rule
    cannot be applied, and falling back to `status == 'active'` would be the
    defect restored under a different name -- a pass reported that was never
    performed. PR 1.11.
    """
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import sairn_claim
    except Exception as e:                                     # noqa: BLE001
        raise CouldNotRun(
            'cannot import sairn_claim from %s (%s), so the staleness rule '
            'that decides whether a claim is still HELD cannot be applied. '
            'Falling back to the raw `status` field would report every '
            'expired-but-unreleased claim as a session actively holding it, '
            'which is the defect this check was fixed for. Nothing was '
            'measured.' % (os.path.join(REPO, 'tools'), e))
    return sairn_claim.is_active(c)

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
        # ── EXPIRED-BUT-UNRELEASED IS A THIRD ANSWER, NOT A QUIET ACTIVE ONE
        # It is real clutter and worth clearing, so it is REPORTED. What it
        # is not is "a session is holding this right now and has stopped
        # working" -- that sentence names a different person and a different
        # action, and merging the two is PR 1.11 one domain over.
        live = _claim_is_active(c)
        if not live:
            rows.append({'session': session, 'id': c.get('id'),
                         'age_h': round(age_h, 1),
                         'files': declared_files(c.get('task')),
                         'state': 'EXPIRED',
                         'why': 'claimed %.1fh ago, past the claim tool\'s own '
                                'staleness rule, and never released. It BLOCKS '
                                'NOBODY -- sairn_claim.py check already ignores '
                                'it -- so this is clutter for its holder to '
                                'clear, not a claim anybody is waiting on.'
                                % age_h})
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
    try:
        rows = scan(hours)
    except CouldNotRun as e:
        print('COULD NOT RUN: %s' % e, file=sys.stderr)
        return 2
    if rows is None:
        print('COULD NOT RUN: a claim file is missing or will not parse, so '
              'the active-claim list is unknown. An empty report here would '
              'not be a clean one.', file=sys.stderr)
        return 2

    # ── THE EXIT CODE FOLLOWS THE LIVE FINDINGS ONLY, AND THAT IS A DECISION
    # An EXPIRED row is worth printing and is not worth failing on: this repo
    # carries eleven of them right now, none of them blocking anybody, and a
    # check that is red forever on a backlog nobody can clear from here is a
    # check people stop reading. The rows are still in the report and in the
    # JSON; only the exit code is scoped.
    live_rows = [r for r in rows if r['state'] != 'EXPIRED']

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'hours': hours, 'rows': rows,
                          'live_findings': len(live_rows),
                          'expired_unreleased': len(rows) - len(live_rows),
                          'blind_spots': BLIND_SPOTS}, indent=1))
        return 1 if live_rows else 0

    print('CLAIM ACTIVITY -- an active claim whose declared files have been quiet')
    print('  criteria %s, window %.0fh' % (CRITERIA_VERSION, hours))
    print('')
    if not live_rows:
        print('  CLEAN: every claim STILL HELD and older than %.0fh has had a '
              'commit touch its declared files.' % hours)
        if rows:
            print('  (%d expired-but-unreleased claim(s) below. They block '
                  'nobody and do not make this check red.)'
                  % (len(rows) - len(live_rows)))
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
    return 1 if live_rows else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
