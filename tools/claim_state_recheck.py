# OWNER: fourth
"""claim_state_recheck.py -- every commit that touches the push wiring, docs/ or
an app's .html is re-checked against the CURRENT claim state when it is pushed.

    python tools/claim_state_recheck.py --pre-push   # .githooks/pre-push, ref lines on stdin
    python tools/claim_state_recheck.py --staged     # the index, for a commit-time hook
    python tools/claim_state_recheck.py --fixtures   # the criteria against synthetic cases

Exit: 0 clean - 1 REFUSED - 2 COULD NOT RUN (never folded into a pass)

-- WHY (fourth b62, 2026-10-28) ----------------------------------------------
In b61 the pre-push wiring was only landed after cody's platform claim was SEEN
released (53b22ae49) and every active claim was re-read immediately before the
commit. That was done by hand, once. Nothing re-asks the question for the next
commit, and the claim state that matters is the one at the time of the push,
not the one read at the start of a batch. So this asks it for EVERY commit in
the outgoing range, in every clone, without anyone remembering to.

WHAT IS WATCHED: `.githooks/pre-push` and every `tools/*.py` it invokes (read
from the hook itself, so a newly wired gate is covered without editing this
file), everything under `docs/`, and any root-level `*.html`.

WHAT COUNTS AS ANOTHER SESSION'S CLAIM ON A PATH: an ACTIVE claim (sairn_claim's
own is_active) held by a different session whose `FILES:` list names the path
or a directory above it, or -- for `<app>.html` -- whose subject IS that app.
Shared ledgers declared in docs/sairn-path-manifest.json and `.claude/claims/`
are exempt: every population appends to them by design.

GO-AHEAD: the standing rule on an overlap is flag back and wait. When the
go-ahead is given, name the claim it covers and who gave it:
    SAIRN_CLAIM_GOAHEAD="<claim id>: <who said so>" git push origin main
Only that claim id is waived; any other overlap still refuses.

FAILS CLOSED: if tools/sairn_claim.py cannot be imported, or neither origin/main
nor the working tree yields a readable claim file, this exits 2 and the hook
refuses. "Could not read the claims" is not "nobody holds a claim".

BLIND SPOTS: claims are only as fresh as this clone's last fetch of origin/main
(unioned with the working tree; a claim released in either copy is released);
a claim with no FILES list on a non-app subject cannot be matched to a path;
a commit-time hook is not wired by this file (`--staged` exists for it).
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = '.githooks/pre-push'
ZERO = '0' * 40
EXIT_OK, EXIT_REFUSED, EXIT_COULD_NOT_RUN = 0, 1, 2
FILES_SEG = re.compile(r'FILES:\s*(.*?)(?:\s+--\s|$)', re.I | re.S)
TOOL_REF = re.compile(r'tools/[A-Za-z0-9_./-]+\.py')


def norm(p):
    p = (p or '').replace('\\', '/').strip()
    return p[2:] if p.startswith('./') else p


def files_of(task):
    """The FILES tokens of a claim's task, or [] when it declares none."""
    m = FILES_SEG.search(task or '')
    if not m:
        return []
    return [norm(t.strip('`,;()')) for t in m.group(1).split() if t.strip('`,;()')]


def wiring(hook_text):
    return {HOOK} | set(TOOL_REF.findall(hook_text or ''))


def watched(path, wired):
    return path in wired or path.startswith('docs/') or (
        path.endswith('.html') and '/' not in path)


def covers(claim, path):
    """-> reason string when this claim covers this path, else None."""
    for f in files_of(claim.get('task')):
        if path == f or (f.endswith('/') and path.startswith(f)):
            return 'its FILES list names %s' % f
    if path.endswith('.html') and '/' not in path:
        if (claim.get('subject') or '').strip().lower() == path[:-5].lower():
            return 'it claims the app %s' % path[:-5]
    return None


def findings(commits, claims, me, wired, exempt, goahead=()):
    """commits: [(sha, [paths])]. claims: ACTIVE claims only. Pure."""
    out = []
    for sha, paths in commits:
        for p in paths:
            if not watched(p, wired) or any(p == e or p.startswith(e.rstrip('/') + '/') for e in exempt):
                continue
            for c in claims:
                if c.get('session') == me or c.get('id') in goahead:
                    continue
                why = covers(c, p)
                if why:
                    out.append((sha, p, c, why))
    return out


def merged_claims(sources):
    """sources: [text of a claims json]. Union by id; released anywhere wins."""
    by_id = {}
    for text in sources:
        for c in (json.loads(text).get('claims') or []):
            k = c.get('id') or json.dumps(c, sort_keys=True)
            prev = by_id.get(k)
            if prev is None or c.get('status') == 'released':
                by_id[k] = c
    return list(by_id.values())


def git(*a):
    r = subprocess.run(['git', '-C', REPO] + list(a), capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, r.stdout


def load_sources():
    texts = []
    rc, ls = git('ls-tree', '--name-only', 'origin/main', '.claude/claims/')
    for path in (ls.split() if rc == 0 else []):
        if path.endswith('.json'):
            rc2, t = git('show', 'origin/main:' + path)
            if rc2 == 0:
                texts.append(t)
    d = os.path.join(REPO, '.claude', 'claims')
    for n in (sorted(os.listdir(d)) if os.path.isdir(d) else []):
        if n.endswith('.json'):
            with open(os.path.join(d, n), encoding='utf-8') as f:
                texts.append(f.read())
    return texts


def outgoing(ref_lines):
    commits = []
    for line in ref_lines.splitlines():
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO:
            continue
        rc, out = git('rev-list', parts[1], '--not', '--remotes=origin')
        if rc != 0:
            raise RuntimeError('rev-list failed for %s' % parts[1][:12])
        for sha in out.split():
            rc, names = git('show', '--name-only', '--format=', sha)
            if rc != 0:
                raise RuntimeError('could not list the paths of %s' % sha[:12])
            commits.append((sha, [norm(n) for n in names.splitlines() if n.strip()]))
    return commits


def run(mode):
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import sairn_claim
        import sairn_path_manifest
    except Exception as e:                                     # noqa: BLE001
        print('COULD NOT RUN (claim-state recheck): could not import the claim '
              'tools (%s). Nothing was checked, and that is not a pass.' % e)
        return EXIT_COULD_NOT_RUN
    try:
        texts = load_sources()
        if not texts:
            print('COULD NOT RUN (claim-state recheck): no claim file was readable '
                  'from origin/main or the working tree. "Could not read the '
                  'claims" is not "nobody holds one".')
            return EXIT_COULD_NOT_RUN
        claims = [c for c in merged_claims(texts) if sairn_claim.is_active(c)]
        me = sairn_claim.session_name()
        manifest, why = sairn_path_manifest.load_manifest(REPO)
        if manifest is None:
            raise RuntimeError('the path manifest could not be read: %s' % why)
        exempt = list(manifest['shared_ledgers'])
        exempt.append('.claude/claims/')
        with open(os.path.join(REPO, HOOK), encoding='utf-8') as f:
            wired = wiring(f.read())
        if mode == '--pre-push':
            commits = outgoing(sys.stdin.read())
        else:
            rc, out = git('diff', '--cached', '--name-only')
            if rc != 0:
                raise RuntimeError('could not read the index')
            commits = [('<staged>', [norm(n) for n in out.splitlines() if n.strip()])]
    except Exception as e:                                     # noqa: BLE001
        print('COULD NOT RUN (claim-state recheck): %s. Nothing was checked, '
              'and that is not a pass.' % e)
        return EXIT_COULD_NOT_RUN

    raw = os.environ.get('SAIRN_CLAIM_GOAHEAD', '')
    goahead = ()
    if raw.strip():
        cid, _, who = raw.partition(':')
        if not who.strip():
            print('REFUSED (claim-state recheck): SAIRN_CLAIM_GOAHEAD must be '
                  '"<claim id>: <who gave the go-ahead>". A waiver with no name '
                  'on it is a mechanism, not a decision.')
            return EXIT_REFUSED
        goahead = (cid.strip(),)
        print('claim-state recheck: go-ahead for claim %s, given by %s'
              % (cid.strip(), who.strip()))

    hits = findings(commits, claims, me, wired, exempt, goahead)
    n_watched = sum(1 for _s, ps in commits for p in ps if watched(p, wired))
    if not hits:
        print('claim-state recheck: %d commit(s), %d watched path(s), %d active '
              'claim(s) held by other sessions -- no overlap.'
              % (len(commits), n_watched,
                 sum(1 for c in claims if c.get('session') != me)))
        return EXIT_OK
    print('REFUSED (claim-state recheck): %d path(s) in this push are under '
          'another session\'s ACTIVE claim:' % len(hits))
    for sha, p, c, why in hits:
        print('  %s  %-44s %s holds %r (%s) -- %s'
              % (sha[:12], p, c.get('session'), c.get('subject'), c.get('id'), why))
    print('The standing rule is flag back and wait. When the go-ahead is given:')
    print('  SAIRN_CLAIM_GOAHEAD="<claim id>: <who said so>" git push origin main')
    return EXIT_REFUSED


def fixtures():
    wired = wiring('"$PY" "$ROOT/tools/push_timeout_guard.py" --pre-push\n'
                   'for g in tools/copy_exactly_gate.py; do')
    ex = ['docs/defect-density-register.json', '.claude/claims/']
    cc = {'id': 'cc-1', 'session': 'cc', 'subject': 'platform',
          'task': 'hook work FILES: .githooks/pre-push tools/x.py'}
    sd = {'id': 'hank-1', 'session': 'hank', 'subject': 'stonedesk', 'task': 'kpi'}
    dd = {'id': 'cody-1', 'session': 'cody', 'subject': 'platform',
          'task': 'notes FILES: docs/open-work/ docs/defect-density-register.json'}
    mine = {'id': 'fourth-1', 'session': 'fourth', 'subject': 'platform',
            'task': 'FILES: .githooks/pre-push'}
    F = lambda paths, cl, ga=(): findings([('abc', paths)], cl, 'fourth', wired, ex, ga)
    arms = [
        ('the hook itself, under another session\'s FILES list, REFUSES',
         len(F(['.githooks/pre-push'], [cc])) == 1),
        ('a gate the hook invokes is wiring, derived from the hook text',
         'tools/push_timeout_guard.py' in wired and 'tools/copy_exactly_gate.py' in wired),
        ('<app>.html under a claim on that app REFUSES',
         len(F(['stonedesk.html'], [sd])) == 1),
        ('...but another app\'s html does not',
         F(['sairnbiz.html'], [sd]) == []),
        ('a docs/ path under a claimed directory REFUSES',
         len(F(['docs/open-work/platform.md'], [dd])) == 1),
        ('a shared ledger is exempt even when a FILES list names it',
         F(['docs/defect-density-register.json'], [dd]) == []),
        ('my OWN claim never refuses me',
         F(['.githooks/pre-push'], [mine]) == []),
        ('an unwatched path is not checked (tools/ not wired, api/)',
         F(['tools/x.py', 'api/sd-data.js'], [cc]) == []),
        ('a subject match alone does not cover a non-app path',
         F(['docs/x.md'], [{'id': 'h', 'session': 'hank', 'subject': 'docs', 'task': ''}]) == []),
        ('the go-ahead waives ONLY the named claim',
         len(F(['.githooks/pre-push', 'stonedesk.html'], [cc, sd], ('cc-1',))) == 1),
        ('union of copies: released in either copy is released',
         merged_claims(['{"claims":[{"id":"a","status":"active"}]}',
                        '{"claims":[{"id":"a","status":"released"}]}'])[0]['status'] == 'released'),
        ('...regardless of which copy is read first',
         merged_claims(['{"claims":[{"id":"a","status":"released"}]}',
                        '{"claims":[{"id":"a","status":"active"}]}'])[0]['status'] == 'released'),
        ('a directory token in FILES is kept, backslashes normalised',
         files_of('x FILES: docs\\open-work\\ a.py') == ['docs/open-work/', 'a.py']),
    ]
    bad = [n for n, ok in arms if not ok]
    for n, ok in arms:
        print('  %s %s' % ('ok  ' if ok else 'FAIL', n))
    print('%d/%d fixtures classify correctly' % (len(arms) - len(bad), len(arms)))
    return EXIT_COULD_NOT_RUN if bad else EXIT_OK


if __name__ == '__main__':
    a = sys.argv[1:]
    if a == ['--fixtures']:
        sys.exit(fixtures())
    if a in (['--pre-push'], ['--staged']):
        sys.exit(run(a[0]))
    print(__doc__)
    sys.exit(EXIT_COULD_NOT_RUN)
