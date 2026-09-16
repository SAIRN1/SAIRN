"""Did the work LAND -- in production, in every clone, and against current versions.

    python tools/landing_verification.py              # all three sections
    python tools/landing_verification.py --landing    # (a) pushed vs actually live
    python tools/landing_verification.py --skills     # (b) each clone's skills
    python tools/landing_verification.py --upgrades   # (c) real available upgrades
    python tools/landing_verification.py --offline    # no network, and it SAYS so
    python tools/landing_verification.py --json

Exit 0 clean, 1 a finding, 2 COULD NOT TELL -- never folded into either of the
other two (PR 1.11). Report-only: it never edits, pushes, fetches into another
clone, or installs anything.

── WHY THIS EXISTS ─────────────────────────────────────────────────────────────
Three questions get ASSUMED on this platform, each with its own real incident:

  (a) "it's pushed" is taken as "it's live". A clean `git push` is not proof --
      the push protocol says so in one sentence and nothing checked it beyond
      StoneDesk. `tools/deploy_verify_notify.py` watches ONE url on ONE clone
      as a post-push hook. The other 21 routes in vercel.json have never been
      compared to anything.
  (b) "the clones are the same" is taken on faith. They are separate clones and
      drift silently; the skills directory is the half nobody looks at, because
      a stale skill still LOADS and still reads as authoritative.
  (c) "we're current" is a memory, not a measurement.

── THE THINGS THIS GETS WRONG IF IT IS WRITTEN CARELESSLY, EACH ALREADY PAID FOR

THE CLONE LIST IS DISCOVERED, NOT WRITTEN DOWN. CLAUDE.md names FOUR clones.
There are FIVE on disk -- `SAIRN-hover`, the hover auditor's, which post-dates
that sentence. A hardcoded list of four would have reported full coverage while
silently omitting the one clone whose job is checking the other four. So the
list comes from the filesystem, every directory found is reported, and the
count is never stated anywhere in this file.

THE URL MAP COMES FROM `vercel.json`, the file Vercel itself dispatches on, and
never from `<name>.html -> /<name>`. That pattern is true for most routes and
guessing it would produce a confident wrong answer on any route that is not --
the same defect shape as deriving a table name from a resource name, which
`removal_path_check.py`'s header records costing 73 false UNKNOWNs.

A CHALLENGE IS A THIRD STATE. Vercel answers bot-shaped traffic with a 403
mitigation challenge. `sairn_http.Challenged` exists precisely so that cannot
be read as an answer: UNVERIFIED is reported as UNVERIFIED, is counted
separately, and NEVER lands in the MATCHES column. A 403 means the check did
not run (PR 3.2).

THE BASELINE IS `origin/main`, NEVER LOCAL HEAD. In a five-clone setup a local
HEAD is stale by default, and `deploy_verify_notify.py` false-alarmed twice on
2026-09-01 for exactly this reason before it was changed. This fetches ONCE, in
the clone it is run from, and compares everything to that tip.

IT NEVER RUNS `git fetch` IN ANOTHER CLONE. A tool that mutates the repos it is
auditing cannot be report-only, however harmless the mutation looks. Every
other clone is read: HEAD, its worktree status, its files. Whether that clone's
HEAD is PUSHED is answered from THIS clone's object store (`git cat-file -e`),
which is a fact about the shared remote rather than about that clone's refs.

CRLF IS NOT DRIFT. `.gitattributes` stores LF and the working-tree half is not
retroactive, so a byte comparison across a clone boundary reports phantom
differences -- three false alarms in one session on 2026-09-03. Every content
comparison here strips `\r` from BOTH sides first, and says that it did.

── WHAT IT CANNOT DO, said plainly rather than left to be discovered ───────────
It cannot tell a stuck deploy from a route that was never deployed; both read
as DRIFT and the message says so. It cannot see a Vercel preview deployment. It
does not judge whether an available upgrade SHOULD be taken -- `npm audit`
already answers the security half and is a different question from currency.
And section (b) compares a clone's skills against the REPO, so two clones that
are both wrong in the same way agree and pass; the user-store mirror check is
the structurally different second opinion that catches that (convention 6).
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLONE_PARENT = os.path.dirname(REPO)
CLONE_GLOB_PREFIX = 'SAIRN-'
USER_SKILL_STORE = os.path.join(os.path.expanduser('~'), '.claude', 'skills')
SKILL_DIR_REL = os.path.join('.claude', 'skills')
LIVE_HOST = 'https://sairn.vercel.app'
FETCH_TIMEOUT = 25

sys.path.insert(0, os.path.join(REPO, 'tools'))


MISSING = -32767   # the executable is not on PATH: a third state, not exit 1


def run(args, cwd=None):
    """(returncode, stdout, stderr) with an EXPLICIT encoding.

    `cwd=None` MEANS REPO, RESOLVED AT CALL TIME, and that is not a style
    preference. It was `cwd=REPO`, and a Python default argument is evaluated
    once at def time -- so a control that repointed `lv.REPO` at a fixture
    repository went on running git in the REAL one, and its assertions were
    about this clone rather than about the fixture. Found 2026-09-16 while
    writing the arm a First Article Inspection said was missing for
    baseline_tip(): the arm failed, and the cause was the harness silently
    testing the wrong repository, which is the vacuous-control shape this
    platform polices hardest. Late binding makes the seam real.

    Not `text=True` alone: a bare text-mode subprocess decodes with the locale
    default, which is cp1252 here, and `subprocess_decode_check.py` exists
    because that silently returned 0 characters for a file containing 0x81.

    AN ABSENT EXECUTABLE RETURNS `MISSING`, NOT AN EXCEPTION AND NOT EXIT 1,
    and this file's own upgrade section is why. `npm` on Windows is `npm.cmd`,
    which `CreateProcess` will not resolve from the bare name -- so the first
    version of npm_row() raised FileNotFoundError and took the whole run with
    it. That is the failure this tool's header promises to handle: a check that
    depends on another tool must say WHICH tool, say the check did not run, and
    fail -- not crash, and not quietly report a pass. Resolved through
    shutil.which so the real `.cmd` is found when it exists, and reported as
    MISSING when it genuinely is not installed.
    """
    exe = shutil.which(args[0])
    if exe is None:
        return MISSING, '', '%s is not on PATH' % args[0]
    p = subprocess.run([exe] + list(args[1:]), cwd=cwd or REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, (p.stdout or ''), (p.stderr or '')


def strip_cr(b):
    """Both sides of every content comparison pass through here. See header."""
    return b.replace(b'\r', b'') if isinstance(b, bytes) else b.replace('\r', '')


def sha(b):
    return hashlib.sha256(strip_cr(b)).hexdigest()


def clones():
    """Every SAIRN clone on disk, discovered. The count is never written down."""
    out = []
    if not os.path.isdir(CLONE_PARENT):
        return out
    for name in sorted(os.listdir(CLONE_PARENT)):
        if not name.startswith(CLONE_GLOB_PREFIX):
            continue
        path = os.path.join(CLONE_PARENT, name)
        if os.path.isdir(os.path.join(path, '.git')):
            out.append(path)
    return out


def routes():
    """app route -> file, from vercel.json. The file Vercel dispatches on.

    A route whose `dest` is not a tracked file in this repo is reported rather
    than dropped: a route pointing at nothing is a finding, and silently
    skipping it would make this tool agree with a broken config.
    """
    path = os.path.join(REPO, 'vercel.json')
    if not os.path.exists(path):
        return None, 'vercel.json is missing -- the URL map has no source'
    try:
        cfg = json.load(io.open(path, encoding='utf-8'))
    except ValueError as e:
        return None, 'vercel.json does not parse: %s' % e
    out = []
    for r in cfg.get('routes') or []:
        src, dest = r.get('src') or '', r.get('dest') or ''
        m = re.match(r'^/([A-Za-z0-9._-]+)\$?$', src)
        if not m or not dest.endswith('.html'):
            continue
        out.append((m.group(1), dest.lstrip('/')))
    if not out:
        return None, ('vercel.json parsed but yielded ZERO routes -- a '
                      'derivation source that returns nothing is a refusal, '
                      'not a clean run')
    return out, None


# ── (a) LANDING ────────────────────────────────────────────────────────────────

def baseline_tip(offline):
    """The origin/main sha every comparison is made against, and its freshness.

    Fetches ONCE, here, and never in another clone.
    """
    if not offline:
        run(['git', 'fetch', '--quiet', 'origin', 'main'])
    rc, out, err = run(['git', 'rev-parse', 'origin/main'])
    if rc != 0:
        return None, 'could not read origin/main: %s' % err.strip()[:200]
    return out.strip(), None


def clone_state(path, tip):
    """One clone's HEAD, whether it is PUSHED, and whether its tree is dirty."""
    st = {'clone': os.path.basename(path), 'path': path}
    rc, head, err = run(['git', 'rev-parse', 'HEAD'], cwd=path)
    if rc != 0:
        st['error'] = 'could not read HEAD: %s' % err.strip()[:160]
        return st
    st['head'] = head.strip()
    rc, branch, _ = run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=path)
    st['branch'] = branch.strip() if rc == 0 else '?'
    rc, dirty, _ = run(['git', 'status', '--porcelain'], cwd=path)
    st['dirty'] = [l for l in dirty.split('\n') if l.strip()] if rc == 0 else None
    # PUSHED is answered from THIS clone's objects against the fetched tip --
    # a fact about the shared remote, not about that clone's own stale refs.
    if tip:
        rc, _, _ = run(['git', 'merge-base', '--is-ancestor', st['head'], tip])
        st['pushed'] = (rc == 0)
        rc, cnt, _ = run(['git', 'rev-list', '--count', '%s..%s' % (st['head'], tip)])
        st['behind'] = int(cnt.strip()) if rc == 0 and cnt.strip().isdigit() else None
    return st


def live_checks(route_list, tip, offline):
    """Each route's live bytes against the same file at origin/main."""
    rows = []
    if offline:
        for name, dest in route_list:
            rows.append({'route': name, 'file': dest, 'verdict': 'NOT RUN',
                         'detail': '--offline: no request was made'})
        return rows
    try:
        import sairn_http
    except Exception as e:                                  # noqa: BLE001
        for name, dest in route_list:
            rows.append({'route': name, 'file': dest, 'verdict': 'COULD NOT TELL',
                         'detail': 'tools/sairn_http.py did not import: %s' % e})
        return rows
    for name, dest in route_list:
        row = {'route': name, 'file': dest}
        rc, blob, err = run(['git', 'show', '%s:%s' % (tip, dest)])
        if rc != 0:
            row.update(verdict='FINDING',
                       detail='vercel.json routes /%s at %s, which does not '
                              'exist at origin/main' % (name, dest))
            rows.append(row)
            continue
        want = sha(blob.encode('utf-8', 'replace'))
        url = '%s/%s' % (LIVE_HOST, name)
        try:
            status, body = sairn_http.fetch(url, timeout=FETCH_TIMEOUT,
                                            no_cache=True)
        except sairn_http.Challenged as c:
            row.update(verdict='UNVERIFIED',
                       detail='Vercel bot-mitigation challenge (HTTP %s). This '
                              'is NOT a failed deploy and NOT verified-good -- '
                              'the check did not run. Re-check from a Claude '
                              'turn with mcp__claude_ai_Vercel__web_fetch_'
                              'vercel_url, which authenticates past it'
                              % c.status)
            rows.append(row)
            continue
        except Exception as e:                              # noqa: BLE001
            row.update(verdict='COULD NOT TELL',
                       detail='%s: %s' % (type(e).__name__, str(e)[:160]))
            rows.append(row)
            continue
        if status != 200:
            row.update(verdict='COULD NOT TELL', detail='HTTP %s' % status)
        elif sha(body) == want:
            row.update(verdict='MATCHES',
                       detail='live bytes equal origin/main (CR-stripped)')
        else:
            row.update(verdict='DRIFT',
                       detail='live does not match origin/main. This cannot '
                              'distinguish a stuck deploy from a route that '
                              'was never deployed')
        rows.append(row)
    return rows


# ── (b) SKILLS ─────────────────────────────────────────────────────────────────

def skill_rows(tip):
    """Each clone's on-disk skills against the repo, then the repo against the store.

    TWO comparisons on purpose, and they are structurally different. The first
    asks whether a clone's working tree matches what git says it should hold.
    That one is blind in exactly one way -- if every clone is wrong the SAME
    way they all agree and it reports clean -- so the second compares the
    repo's mirror against the user store it is a mirror OF, which is a source
    outside git entirely (convention 6, independent replication).
    """
    rows = []
    for path in clones():
        name = os.path.basename(path)
        d = os.path.join(path, SKILL_DIR_REL)
        if not os.path.isdir(d):
            rows.append({'scope': name, 'verdict': 'FINDING',
                         'detail': '%s does not exist in this clone'
                                   % SKILL_DIR_REL})
            continue
        # (i) the clone's working tree against ITS OWN checkout. Always
        #     answerable, no network, no shared objects.
        rc, out, err = run(['git', 'status', '--porcelain', '--', SKILL_DIR_REL],
                           cwd=path)
        if rc != 0:
            rows.append({'scope': name, 'verdict': 'COULD NOT TELL',
                         'detail': 'git status failed: %s' % err.strip()[:160]})
            continue
        uncommitted = [l for l in out.split('\n') if l.strip()]
        # (ii) that checkout against the current tip -- RUN IN THIS CLONE, not
        #      in theirs. The first version asked the other clone, and a clone
        #      that simply had not fetched recently came back COULD NOT TELL --
        #      which is the common case, so the tool would have spent most of
        #      its life reporting a non-answer about a question it can answer
        #      perfectly well from here. A clone's checked-out sha is a fact
        #      about the shared history; only an UNPUSHED local commit is
        #      genuinely unknown here, and that is reported as its own state
        #      rather than as drift.
        rc_h, head, _ = run(['git', 'rev-parse', 'HEAD'], cwd=path)
        head = head.strip()
        rc_e, _, _ = run(['git', 'cat-file', '-e', head + '^{commit}'])
        if rc_h != 0 or rc_e != 0:
            behind, unknown = [], True
        else:
            rc2, out2, _ = run(['git', 'diff', '--name-only', head, tip, '--',
                                SKILL_DIR_REL])
            behind = [l for l in out2.split('\n') if l.strip()] if rc2 == 0 else []
            unknown = (rc2 != 0)
        if unknown:
            rows.append({'scope': name, 'verdict': 'COULD NOT TELL',
                         'detail': 'this clone is on %s, a commit this clone '
                                   'has never seen -- it holds unpushed work, '
                                   'so its skills cannot be compared to the '
                                   'tip' % (head[:12] or '?')})
            continue
        if uncommitted or behind:
            rows.append({'scope': name, 'verdict': 'FINDING',
                         'detail': '%d file(s) uncommitted, %d file(s) behind '
                                   'origin/main' % (len(uncommitted),
                                                    len(behind)),
                         'files': sorted(set(
                             [l[3:] for l in uncommitted] + behind))[:20]})
        else:
            rows.append({'scope': name, 'verdict': 'MATCHES',
                         'detail': 'skills match origin/main, nothing '
                                   'uncommitted'})
    rows.append(mirror_row())
    return rows


def mirror_row():
    """The repo's mirrored skills against the user store, CR-stripped.

    The store is CRLF and the repo is LF, so a byte diff reports every
    content-identical file as changed -- the mistake CLAUDE.md names by date.
    """
    repo_d = os.path.join(REPO, SKILL_DIR_REL)
    if not os.path.isdir(USER_SKILL_STORE):
        return {'scope': 'repo <-> user skill store', 'verdict': 'COULD NOT TELL',
                'detail': '%s does not exist -- the mirror has no reference to '
                          'compare against, so this did NOT run' % USER_SKILL_STORE}
    if not os.path.isdir(repo_d):
        return {'scope': 'repo <-> user skill store', 'verdict': 'FINDING',
                'detail': '%s does not exist in this repo' % SKILL_DIR_REL}
    mirrored = sorted(n for n in os.listdir(repo_d)
                      if os.path.isdir(os.path.join(repo_d, n)))
    if not mirrored:
        return {'scope': 'repo <-> user skill store', 'verdict': 'COULD NOT TELL',
                'detail': 'the repo mirror holds zero skill directories -- a '
                          'derivation source yielding zero is a refusal'}
    missing, diverged = [], []
    for skill in mirrored:
        a, b = os.path.join(repo_d, skill), os.path.join(USER_SKILL_STORE, skill)
        if not os.path.isdir(b):
            missing.append(skill)
            continue
        for rel in walk_rel(a):
            pa, pb = os.path.join(a, rel), os.path.join(b, rel)
            if not os.path.exists(pb):
                diverged.append('%s/%s (absent from the store)' % (skill, rel))
            elif strip_cr(readb(pa)) != strip_cr(readb(pb)):
                diverged.append('%s/%s' % (skill, rel))
    # The store legitimately holds third-party skills the repo does not mirror,
    # so store-only directories are NOT a finding. Counted and named anyway --
    # an exclusion the reader cannot see is indistinguishable from a checker
    # that stopped looking.
    extra = sorted(set(os.listdir(USER_SKILL_STORE))
                   - set(mirrored)) if os.path.isdir(USER_SKILL_STORE) else []
    detail = ('%d mirrored skill(s) compared after stripping CR from both '
              'sides; %d in the store only and NOT a finding (third-party '
              'skills the repo does not mirror)' % (len(mirrored), len(extra)))
    if missing or diverged:
        return {'scope': 'repo <-> user skill store', 'verdict': 'FINDING',
                'detail': detail, 'files': (['MISSING FROM STORE: ' + m
                                             for m in missing]
                                            + diverged)[:20]}
    return {'scope': 'repo <-> user skill store', 'verdict': 'MATCHES',
            'detail': detail}


def walk_rel(root):
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            yield os.path.relpath(os.path.join(dirpath, f), root)


def readb(path):
    with io.open(path, 'rb') as fh:
        return fh.read()


# ── (c) UPGRADES ───────────────────────────────────────────────────────────────

def upgrade_rows(offline):
    """Real available upgrades for npm and pip.

    FAILS CLOSED WHEN THE TOOL IS ABSENT. `npm` missing does not skip one
    check, it means this check did not run -- and "could not run" is a third
    state that is never folded into "passed" (PR 1.11). That is the single
    commonest defect shape on this platform and it is cheapest to get right
    here, before anything reads the output.
    """
    rows = []
    if offline:
        return [{'ecosystem': e, 'verdict': 'NOT RUN',
                 'detail': '--offline: an upgrade check needs the registry'}
                for e in ('npm', 'pip')]
    rows.append(npm_row())
    rows.append(pip_row())
    return rows


def npm_row():
    if not os.path.exists(os.path.join(REPO, 'package.json')):
        return {'ecosystem': 'npm', 'verdict': 'NOT RUN',
                'detail': 'no package.json in this repo'}
    # `npm outdated` exits 1 when anything IS outdated. That is its documented
    # success path, so the exit code carries no verdict and is not read as one.
    rc, out, err = run(['npm', 'outdated', '--json', '--long'])
    if rc == MISSING:
        return {'ecosystem': 'npm', 'verdict': 'COULD NOT TELL',
                'detail': 'npm is not on PATH, so the npm currency check DID '
                          'NOT RUN. This is not "no upgrades available"'}
    if not out.strip():
        if rc == 0:
            return {'ecosystem': 'npm', 'verdict': 'CURRENT',
                    'detail': 'npm outdated reported nothing'}
        return {'ecosystem': 'npm', 'verdict': 'COULD NOT TELL',
                'detail': 'npm produced no JSON (exit %s): %s'
                          % (rc, (err or '').strip()[:200])}
    try:
        data = json.loads(out)
    except ValueError:
        return {'ecosystem': 'npm', 'verdict': 'COULD NOT TELL',
                'detail': 'npm outdated did not return parseable JSON'}
    items = []
    for pkg, info in sorted(data.items()):
        cur, latest = info.get('current'), info.get('latest')
        if not latest or cur == latest:
            continue
        items.append('%s %s -> %s%s' % (pkg, cur or '(absent)', latest,
                                        '  [MAJOR]' if major_jump(cur, latest)
                                        else ''))
    if not items:
        return {'ecosystem': 'npm', 'verdict': 'CURRENT',
                'detail': 'every dependency is at latest'}
    return {'ecosystem': 'npm', 'verdict': 'UPGRADE AVAILABLE',
            'detail': '%d package(s) behind' % len(items), 'items': items}


def pip_row():
    rc, out, err = run([sys.executable, '-m', 'pip', 'list', '--outdated',
                        '--format=json', '--disable-pip-version-check'])
    if rc == MISSING:
        return {'ecosystem': 'pip', 'verdict': 'COULD NOT TELL',
                'detail': 'this interpreter (%s) could not be re-invoked, so '
                          'the pip currency check DID NOT RUN'
                          % sys.executable}
    if rc != 0 or not out.strip():
        return {'ecosystem': 'pip', 'verdict': 'COULD NOT TELL',
                'detail': 'pip list --outdated failed (exit %s): %s'
                          % (rc, (err or out or '').strip()[:200])}
    try:
        data = json.loads(out)
    except ValueError:
        return {'ecosystem': 'pip', 'verdict': 'COULD NOT TELL',
                'detail': 'pip did not return parseable JSON'}
    if not data:
        return {'ecosystem': 'pip', 'verdict': 'CURRENT',
                'detail': 'pip reports nothing outdated'}
    items = ['%s %s -> %s%s' % (d.get('name'), d.get('version'),
                                d.get('latest_version'),
                                '  [MAJOR]' if major_jump(d.get('version'),
                                                          d.get('latest_version'))
                                else '')
             for d in sorted(data, key=lambda x: x.get('name') or '')]
    return {'ecosystem': 'pip', 'verdict': 'UPGRADE AVAILABLE',
            'detail': '%d package(s) behind' % len(items), 'items': items}


def major_jump(cur, latest):
    """True when the leading version component moved. Labelled, never acted on."""
    def lead(v):
        m = re.match(r'^\D*(\d+)', str(v or ''))
        return int(m.group(1)) if m else None
    a, b = lead(cur), lead(latest)
    return a is not None and b is not None and b > a


# ── report ─────────────────────────────────────────────────────────────────────

FINDING = ('FINDING', 'DRIFT')
UNKNOWN = ('COULD NOT TELL', 'UNVERIFIED', 'NOT RUN')


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--landing', action='store_true')
    ap.add_argument('--skills', action='store_true')
    ap.add_argument('--upgrades', action='store_true')
    ap.add_argument('--offline', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    want = {'landing': a.landing, 'skills': a.skills, 'upgrades': a.upgrades}
    if not any(want.values()):
        want = {k: True for k in want}

    report = {'sections': {}, 'baseline': None, 'offline': a.offline}
    tip, terr = baseline_tip(a.offline)
    report['baseline'] = tip
    report['baseline_error'] = terr

    if terr:
        # Everything downstream is measured against this tip. Without it the
        # tool has not checked anything, and says so rather than reporting the
        # sections it could still technically run.
        emit(report, a.json, note=terr)
        return 2

    if want['landing']:
        route_list, rerr = routes()
        if rerr:
            report['sections']['landing'] = {'error': rerr}
        else:
            report['sections']['landing'] = {
                'clones': [clone_state(p, tip) for p in clones()],
                'live': live_checks(route_list, tip, a.offline)}
    if want['skills']:
        report['sections']['skills'] = {'rows': skill_rows(tip)}
    if want['upgrades']:
        report['sections']['upgrades'] = {'rows': upgrade_rows(a.offline)}

    return emit(report, a.json)


def emit(report, as_json, note=None):
    if as_json:
        print(json.dumps(report, indent=2))
        return verdict(report)
    print('landing verification -- report only, nothing is changed')
    print('  baseline origin/main            : %s'
          % (report['baseline'][:12] if report['baseline'] else 'UNREADABLE'))
    if report.get('offline'):
        print('  --offline: no request was made. Every network answer below '
              'reads NOT RUN,\n  which is not a pass.')
    if note:
        print('\nCOULD NOT TELL -- %s' % note)
        return 2

    land = report['sections'].get('landing')
    if land is not None:
        print('\n--- (a) IS WHAT IS PUSHED ACTUALLY LIVE ---')
        if land.get('error'):
            print('  COULD NOT TELL -- %s' % land['error'])
        else:
            for c in land['clones']:
                if c.get('error'):
                    print('  %-16s COULD NOT TELL -- %s'
                          % (c['clone'], c['error']))
                    continue
                dirty = c.get('dirty')
                print('  %-16s %s %s  %s%s'
                      % (c['clone'], c['head'][:12], c.get('branch', '?'),
                         'PUSHED' if c.get('pushed') else 'NOT ON origin/main',
                         ('' if c.get('behind') in (0, None)
                          else ', %d behind' % c['behind'])))
                if dirty:
                    print('      %d uncommitted path(s), first: %s'
                          % (len(dirty), dirty[0][3:]))
                elif dirty is None:
                    print('      COULD NOT TELL whether the tree is clean')
            print()
            for r in land['live']:
                print('  %-10s %-24s %-15s %s'
                      % (r['verdict'], '/' + r['route'], r['file'],
                         '' if r['verdict'] == 'MATCHES' else r['detail'][:90]))
            counted(land['live'], 'verdict')

    sk = report['sections'].get('skills')
    if sk is not None:
        print('\n--- (b) EACH CLONE\'S SKILLS AGAINST WHAT IT SHOULD HAVE ---')
        for r in sk['rows']:
            print('  %-14s %-32s %s' % (r['verdict'], r['scope'], r['detail']))
            for f in r.get('files', []):
                print('        %s' % f)
        counted(sk['rows'], 'verdict')

    up = report['sections'].get('upgrades')
    if up is not None:
        print('\n--- (c) REAL AVAILABLE UPGRADES ---')
        print('  Currency, not security. `npm audit` answers a different '
              'question and\n  an available upgrade is not by itself a reason '
              'to take one.')
        for r in up['rows']:
            print('  %-18s %-18s %s' % (r['verdict'], r['ecosystem'],
                                        r['detail']))
            for i in r.get('items', []):
                print('        %s' % i)

    v = verdict(report)
    print('\n%s' % {0: 'CLEAN -- nothing here is a finding.',
                    1: 'FINDING(S) above.',
                    2: 'COULD NOT TELL on at least one check. That is NOT a '
                       'pass -- see the rows above that say so.'}[v])
    return v


def counted(rows, key):
    from collections import Counter
    c = Counter(r[key] for r in rows)
    print('    %s' % ', '.join('%s=%d' % (k, c[k]) for k in sorted(c)))


def verdict(report):
    """A FINDING outranks an UNKNOWN; an UNKNOWN never reads as clean."""
    seen = []
    land = report['sections'].get('landing') or {}
    if land.get('error'):
        seen.append('COULD NOT TELL')
    for r in land.get('live', []):
        seen.append(r['verdict'])
    for c in land.get('clones', []):
        if c.get('error') or c.get('dirty') is None:
            seen.append('COULD NOT TELL')
    for r in (report['sections'].get('skills') or {}).get('rows', []):
        seen.append(r['verdict'])
    for r in (report['sections'].get('upgrades') or {}).get('rows', []):
        if r['verdict'] in UNKNOWN:
            seen.append(r['verdict'])
    if any(s in FINDING for s in seen):
        return 1
    if any(s in UNKNOWN for s in seen):
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
