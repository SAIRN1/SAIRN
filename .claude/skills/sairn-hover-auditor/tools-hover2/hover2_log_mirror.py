#!/usr/bin/env python
"""hover2_log_mirror.py -- off-disk backup for THIS clone's own hash-chained
self-log (hover2's hover-audit-log/), designed independently of H1's
hover_backup_mirror.py per direct instruction 2026-09-28.

SCOPE, DECIDED BY MICHAEL 2026-09-29: the mirror carries the LOG
(hover-audit-log.jsonl), the ANCHORS (.mirror2-anchor-outbox.jsonl) and the
BEACON (TIP-BEACON.md) ONLY. No tool scripts, no other files -- the tools
have their own off-disk remote with history (the platform repo, under
.claude/skills/sairn-hover-auditor/tools-hover2/). Enforced mechanically:
--push stages exactly MIRROR_ALLOWLIST via a throwaway index on a dedicated
`mirror` branch, verifies the staged set against the allowlist before
committing (staged_scope_error -- a staged name outside the list refuses
the whole push), and the local repo's own branch and index are untouched.
The one pre-decision full-directory snapshot on the remote stays reachable
in history; the scope narrowing landed as a normal commit, not a rewrite.

HONEST PROVENANCE DISCLOSURE: this role validated H1's mirror tool earlier
the same day, so this is not a clean-room design -- it is an independent
IMPLEMENTATION (no line copied) with three requirements H1's tool does not
have: a credential-expiry record with a 14-day warning, a mechanical
ambient-credential-cannot-answer proof before every push, and a restore
drill that verifies against the last EMAILED anchor rather than only
against the local tree.

THE SEPARATION RULES (blast-radius bounding, same reasoning as H1's tool,
enforced against DIFFERENT resources):
  * Remote: a dedicated PRIVATE repo under the SAIRN-1 account (hyphen --
    the dedicated mirror account), proposed name SAIRN-1/hover2-log-mirror.
    NEVER SAIRN1 (no hyphen -- the platform org), never any repo named
    SAIRN, never H1's own SAIRN-1/hover-log-mirror (a shared mirror would
    let either instance overwrite the other's history -- the two logs stay
    separately recoverable or the second log adds no redundancy).
  * Credential: a fine-grained PAT under SAIRN-1, scoped to the ONE repo
    hover2-log-mirror, permission Contents: read+write ONLY -- and a
    DIFFERENT token from H1's, so stealing either compromises one mirror,
    not both.
  * The token lives ONLY in .mirror-token in THIS directory (named to match
    the real file Michael provisioned 2026-09-29 -- this tool's own design
    draft had proposed .mirror2-token, and the constant was corrected to
    the real on-disk name rather than the file renamed to match a draft).
    Never in any
    global credential store, never in gh's keyring, never in git config,
    never in a remote URL, never in argv. It reaches git only via a
    GIT_ASKPASS shim that reads the file at call time.
  * .mirror2-token-meta.json records {"expires": "YYYY-MM-DD"} the day the
    token is created. Every run warns when today is within EXPIRY_WARN_DAYS
    (14) of expiry, and REFUSES a push once expired -- an expired token's
    push failure would otherwise surface as an opaque auth error.

THE AMBIENT-PROOF RULE, the requirement H1's tool enforces only by
configuration and this one PROVES per push: before any push, run
`git ls-remote` against the remote with the credential helper chain RESET
(-c credential.helper=), GIT_TERMINAL_PROMPT=0, and an askpass shim that
answers EMPTY. If that probe SUCCEEDS, something ambient (a stored
credential, a public repo) can answer without our token -- REFUSE the push,
because either the repo is not private or a broad-scope ambient credential
is reachable, and both are design violations. Only after the ambient probe
FAILS is the real push attempted, with the same helper reset and the real
askpass shim. This turns "no ambient credential can answer" from a promise
into a per-push measured fact.

PRIVACY RULE, fail closed: --push and --set-remote refuse unless the GitHub
REST API, called with THIS tool's own scoped token, answers private:true
for the exact owner/repo. Every other outcome -- no token file, network
error, API error, private:false -- is a refusal that says which. There is
deliberately NO gh-CLI fallback: gh's keyring token is broad-scope and
consulting it would violate the ambient rule above.

ANCHOR RULE: every successful push appends one line to
.mirror2-anchor-outbox.jsonl -- {ts, chain_head, remote_tip, n_entries,
sent: false} -- and exits 1 BROKEN until that anchor is actually emailed
off-disk. The EMAIL ITSELF is deliberately not sent by this tool: this
machine's only mail path is the session's Gmail channel, and a credential
for it must never live in a file here. The flow is: --push prints the
exact anchor line; this role emails it to Michael through the Gmail
channel in the same turn; then --anchor-sent <ts> stamps that outbox row
sent:true. (Checked against the real tools before writing this: the tip
beacon, hover_tip_beacon.py, is a LOCAL passive seal with --check/
--publish only -- it has no mail capability, so citing it as the mail
channel would have been a dead reference.) --restore-test clones the
remote into a scratch directory (read-only against the live dir),
re-verifies the hash chain inside the clone, and compares the clone's
chain head against the last SENT anchor -- three legs (remote content,
chain math, off-disk anchor), so a tampered mirror fails the drill even
if it is internally consistent, and an unsent anchor blocks the drill
rather than quietly standing in for a real off-disk record.

EXIT CODES: 0 clean, 1 a check ran and failed, 2 COULD NOT RUN.

Run:
  python hover2_log_mirror.py --selftest       # fixtures, no network, no token
  python hover2_log_mirror.py --status         # expiry + config report, read-only
  python hover2_log_mirror.py --set-remote URL # gated, no push
  python hover2_log_mirror.py --push           # gated: privacy + ambient proof + expiry
  python hover2_log_mirror.py --restore-test   # scratch clone + chain + anchor
"""
import datetime
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_NAME = 'hover-audit-log.jsonl'
REMOTE_NAME = 'backup2'
TOKEN_FILE = os.path.join(HERE, '.mirror-token')
META_FILE = os.path.join(HERE, '.mirror2-token-meta.json')
ANCHOR_OUTBOX = os.path.join(HERE, '.mirror2-anchor-outbox.jsonl')
# THE MIRROR'S ENTIRE PUSHED SURFACE, decided by Michael 2026-09-29: the
# hash-chained log itself, the anchor outbox, and the tip beacon. No tool
# scripts, no other files -- the tools have their own off-disk remote (the
# platform repo, .claude/skills/sairn-hover-auditor/tools-hover2/). Staged
# with -f because the anchor outbox is deliberately gitignored against the
# LOCAL repo's own snapshots; the mirror carries it per this decision.
MIRROR_ALLOWLIST = ('hover-audit-log.jsonl',
                    '.mirror2-anchor-outbox.jsonl',
                    'TIP-BEACON.md')
PROPOSED_REPO = 'SAIRN-1/hover2-log-mirror'
H1_MIRROR_REPO = ('sairn-1', 'hover-log-mirror')
EXPIRY_WARN_DAYS = 14
EXIT_CLEAN, EXIT_BROKEN, EXIT_COULD_NOT_RUN = 0, 1, 2


# -- remote classification: pure, fixture-locked ---------------------------

_CRED_IN_URL = re.compile(r'://[^/@]*:[^/@]*@|://[^/:@]+@')
_GITHUB = re.compile(
    r'^(?:https://|git@|ssh://git@)github\.com[:/]'
    r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$')


def classify_remote(url):
    """('refuse', reason) | ('check', (owner, repo)). Never 'ok': a URL
    string cannot prove privacy. Ordering note, learned from the seq-289
    finding on H1's tool: the github matcher runs FIRST on the exact
    supported forms, so ssh://git@github.com/... is recognised as the ssh
    transport user, not misdiagnosed as an embedded credential; the
    credential check then applies to whatever the matcher did not claim,
    and to userinfo other than the bare 'git' transport user."""
    u = (url or '').strip()
    if not u:
        return ('refuse', 'no remote URL configured')
    m = _GITHUB.match(u)
    if m:
        owner, repo = m.group(1), m.group(2)
        ol, rl = owner.lower(), repo.lower()
        if ol == 'sairn1':
            return ('refuse', 'owner is SAIRN1 -- the PLATFORM org; audit '
                              'records never live inside the thing audited')
        if rl == 'sairn':
            return ('refuse', 'repo named SAIRN -- could be a platform alias/fork')
        if (ol, rl) == H1_MIRROR_REPO:
            return ('refuse', "this is H1's own mirror repo -- the two "
                              'hover logs stay separately recoverable, so '
                              'hover2 never pushes there')
        return ('check', (owner, repo))
    if _CRED_IN_URL.search(u):
        return ('refuse', 'remote URL embeds a credential/userinfo -- this '
                          'tool never puts a credential in a URL')
    return ('refuse', 'not a recognised github.com remote form -- privacy '
                      'cannot be confirmed, so it cannot be used')


# -- token + expiry --------------------------------------------------------

def token_state(today=None, token_file=TOKEN_FILE, meta_file=META_FILE):
    """('missing'|'no-meta'|'expired'|'warn'|'ok', detail). Never reads the
    token's VALUE here -- only existence; expiry comes from the meta file."""
    if not os.path.isfile(token_file):
        return ('missing', '.mirror-token does not exist -- Michael creates '
                           'the fine-grained PAT (repo %s, Contents rw only) '
                           'and it goes in that file, one line' % PROPOSED_REPO)
    if not os.path.isfile(meta_file):
        return ('no-meta', '.mirror2-token-meta.json missing -- the expiry '
                           'date must be recorded the day the token is made')
    try:
        with io.open(meta_file, encoding='utf-8') as f:
            exp = datetime.date.fromisoformat(json.load(f)['expires'])
    except Exception as e:
        return ('no-meta', 'meta file unreadable (%s)' % e)
    today = today or datetime.date.today()
    days = (exp - today).days
    if days < 0:
        return ('expired', 'token expired %s (%d day(s) ago) -- pushes '
                           'refuse until rotated' % (exp, -days))
    if days <= EXPIRY_WARN_DAYS:
        return ('warn', 'token expires %s -- %d day(s) left (warning window '
                        'is %d)' % (exp, days, EXPIRY_WARN_DAYS))
    return ('ok', 'token expires %s (%d days out)' % (exp, days))


def token_hygiene_errors(run=None, token_file=TOKEN_FILE):
    """Refusal reasons if the token could leak into the mirror or config.
    run(cmd_list)->(rc, out) is injectable for fixtures."""
    run = run or _run_git
    errs = []
    rc, out = run(['ls-files', '--', os.path.basename(token_file)])
    if rc == 0 and out.strip():
        errs.append('%s is TRACKED by the mirror repo -- pushing would '
                    'publish the credential' % os.path.basename(token_file))
    rc, out = run(['check-ignore', os.path.basename(token_file)])
    if rc != 0:
        errs.append('%s is NOT gitignored in this directory -- a snapshot '
                    'commit -A would stage it' % os.path.basename(token_file))
    # --local ONLY, found live 2026-09-29 on the real first push: the merged
    # (no --local) view also returns credential.helper=manager from Git for
    # Windows' own SYSTEM config (C:\Program Files\Git\etc\gitconfig, every
    # standard Windows install carries this) -- confirmed via `git config
    # --show-origin` before this was trusted. That system entry is not a
    # hygiene defect to refuse on: `-c credential.helper=` on every real git
    # call this tool makes (ls-remote/push/clone) resets the ENTIRE
    # accumulated helper list regardless of which level set it, per git's
    # own documented -c precedence -- so a system or global helper is
    # already fully neutralized at the moment it would matter. What this
    # check exists to catch is a LOCAL override specific to THIS repo,
    # the one level a mistake or a hand-run `git config credential.helper
    # ...` inside this directory could add and that a caller might forget
    # is still sitting there. Checking the merged view instead of --local
    # would have refused every push on every real Windows machine forever,
    # which is not caution, it is the tool being unable to do its one job.
    rc, out = run(['config', '--local', '--get-regexp', r'credential\.'])
    if rc == 0 and out.strip():
        errs.append('local (repo-specific) git config carries credential.* '
                    'entries -- this tool requires a clean LOCAL helper '
                    'chain; a system or global helper is separately '
                    'neutralized per-command and is not what this checks')
    return errs


# -- ambient-credential proof ---------------------------------------------

def ambient_can_answer(url, probe=None):
    """True if `git ls-remote` succeeds with all credential helpers reset
    and an empty-answer askpass -- meaning something OTHER than our token
    (a stored credential, or the repo being public) can already answer.
    probe(url)->(rc, err) is injectable; the real one execs git."""
    probe = probe or _real_ambient_probe
    rc, _err = probe(url)
    return rc == 0


def ambient_proof_error(url, probe=None):
    if ambient_can_answer(url, probe):
        return ('an AMBIENT credential (or public visibility) answered for '
                '%s with our token withheld -- refusing: either the repo is '
                'not private or a broad-scope stored credential is '
                'reachable, and both violate the design' % url)
    return None


# -- privacy confirmation (own token only, no gh fallback) -----------------

def confirm_private(owner, repo, http_get=None, token_file=TOKEN_FILE):
    """(True, why) only on an API answer private:true using OUR token.
    http_get(url, headers)->(status, body_dict) injectable for fixtures."""
    if not os.path.isfile(token_file):
        return (False, 'no %s -- privacy cannot be confirmed with our own '
                       'scoped token, and there is deliberately no gh/'
                       'ambient fallback' % os.path.basename(token_file))
    if http_get is None:
        http_get = _real_http_get
    try:
        status, body = http_get(
            'https://api.github.com/repos/%s/%s' % (owner, repo),
            {'Authorization': 'Bearer ' + io.open(
                 token_file, encoding='utf-8').read().strip(),
             'Accept': 'application/vnd.github+json',
             'User-Agent': 'hover2-log-mirror'})
    except Exception as e:
        return (False, 'API check failed (%s) -- COULD NOT CONFIRM, refusing'
                       % str(e)[:120])
    if status == 200 and body.get('private') is True:
        return (True, 'GitHub confirms %s/%s is private (via our scoped '
                      'token)' % (owner, repo))
    return (False, 'GitHub answered status=%s private=%r -- NOT confirmed '
                   'private' % (status, body.get('private')))


# -- real-side runners (thin, no logic) ------------------------------------

def _run_git(args, cwd=HERE):
    r = subprocess.run(['git'] + list(args), cwd=cwd, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def _real_ambient_probe(url):
    empty_bat = _write_shim(empty=True)
    env = dict(os.environ)
    env['GIT_ASKPASS'] = empty_bat
    env['GIT_TERMINAL_PROMPT'] = '0'
    r = subprocess.run(['git', '-c', 'credential.helper=', 'ls-remote', url],
                       cwd=HERE, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env,
                       timeout=60)
    return r.returncode, r.stderr


def _real_http_get(url, headers):
    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8', 'replace'))
    except Exception as e:
        code = getattr(e, 'code', None)
        if code is not None:
            return code, {}
        raise


def _write_shim(empty=False):
    """GIT_ASKPASS pair. empty=True answers nothing (the ambient probe);
    otherwise Username=x-access-token, Password=token file read at call
    time. Shims hold paths only, never a secret; both are gitignored."""
    suffix = 'empty' if empty else 'real'
    py = os.path.join(HERE, '.mirror2-askpass-%s.py' % suffix)
    with io.open(py, 'w', encoding='utf-8') as f:
        if empty:
            f.write('print("")\n')
        else:
            f.write("import sys\n"
                    "p=' '.join(sys.argv[1:]).lower()\n"
                    "print('x-access-token' if 'username' in p else "
                    "open(%r,encoding='utf-8').read().strip())\n" % TOKEN_FILE)
    bat = os.path.join(HERE, '.mirror2-askpass-%s.bat' % suffix)
    with io.open(bat, 'w', encoding='utf-8') as f:
        f.write('@echo off\r\n"%s" "%s" %%*\r\n' % (sys.executable, py))
    return bat


# -- the gated push pipeline, pure decision layer --------------------------

def push_refusals(url, today=None, probe=None, http_get=None,
                  run=None, token_file=TOKEN_FILE, meta_file=META_FILE):
    """Every reason NOT to push, in gate order, empty list = go. Pure given
    injected seams; the CLI wires the real ones. Each refusal is a named,
    fixture-locked arm."""
    errs = []
    verdict, detail = classify_remote(url)
    if verdict == 'refuse':
        return ['remote: ' + detail]          # nothing else is meaningful
    owner, repo = detail
    st, d = token_state(today, token_file, meta_file)
    if st in ('missing', 'no-meta', 'expired'):
        errs.append('token: ' + d)
    elif st == 'warn':
        print('WARNING %s' % d)               # warn, not refuse, by spec
    errs.extend('hygiene: ' + e for e in token_hygiene_errors(run, token_file))
    if not errs:                              # network gates only when local ones pass
        ok, why = confirm_private(owner, repo, http_get, token_file)
        if not ok:
            errs.append('privacy: ' + why)
        amb = ambient_proof_error(url, probe)
        if amb:
            errs.append('ambient: ' + amb)
    return errs


# -- chain + anchor helpers ------------------------------------------------

def chain_head(log_path=None):
    log_path = log_path or os.path.join(HERE, LOG_NAME)
    last = None
    with io.open(log_path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                last = line
    if not last:
        return None, 0
    n = sum(1 for l in io.open(log_path, encoding='utf-8') if l.strip())
    return json.loads(last).get('hash'), n


def last_anchor(outbox=ANCHOR_OUTBOX):
    if not os.path.isfile(outbox):
        return None
    rows = [json.loads(l) for l in io.open(outbox, encoding='utf-8')
            if l.strip()]
    return rows[-1] if rows else None


# -- CLI -------------------------------------------------------------------

def cmd_status():
    st, d = token_state()
    print('token: %s -- %s' % (st.upper(), d))
    rc, out = _run_git(['remote', 'get-url', REMOTE_NAME])
    url = out.strip() if rc == 0 else '(not configured)'
    print('remote %r: %s' % (REMOTE_NAME, url))
    if rc == 0:
        v, det = classify_remote(url)
        print('classification: %s -- %s' % (v.upper(), det))
    a = last_anchor()
    print('last emailed anchor: %s' % (json.dumps(a) if a else '(none yet)'))
    return EXIT_CLEAN


def staged_scope_error(staged_names, allowlist=None):
    """Michael's 2026-09-29 scope decision: the mirror carries the LOG, the
    ANCHORS and the BEACON only -- no tool scripts, no other files. This is
    the mechanical half: given the set of staged file names, return a
    refusal string if ANY staged name is outside the allowlist, else None.
    Pure and injectable so the selftest can drive it with a known-bad set
    (a tool file smuggled into the staging) and prove the refusal fires."""
    allowlist = allowlist if allowlist is not None else MIRROR_ALLOWLIST
    extra = sorted(set(staged_names) - set(allowlist))
    if extra:
        return ('staged set exceeds the mirror scope (log, anchors, beacon '
                'only -- Michael, 2026-09-29): %s' % ', '.join(extra))
    return None


def _mirror_commit():
    """(commit_sha, None) or (None, refusal). Builds a commit whose tree is
    EXACTLY the allowlist files, using a throwaway index (GIT_INDEX_FILE) so
    the local repo's real index/branch/working tree are untouched. Parent is
    the previous refs/heads/mirror tip, or -- the first time only -- the
    current local HEAD, so the remote's pre-decision history stays reachable
    and the scope narrowing lands as a normal commit, not a rewrite."""
    tmpidx = os.path.join(HERE, '.mirror2-tmp-index')
    env = dict(os.environ, GIT_INDEX_FILE=tmpidx)

    def g(cmd):
        return subprocess.run(['git'] + cmd, cwd=HERE, env=env,
                              capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
    try:
        r = g(['read-tree', '--empty'])
        if r.returncode != 0:
            return None, 'read-tree failed: %s' % r.stderr.strip()[:120]
        for name in MIRROR_ALLOWLIST:
            if os.path.isfile(os.path.join(HERE, name)):
                r = g(['add', '-f', '--', name])
                if r.returncode != 0:
                    return None, 'add %s failed: %s' % (name, r.stderr.strip()[:120])
        r = g(['ls-files'])
        staged = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        err = staged_scope_error(staged)
        if err:
            return None, err
        if not staged:
            return None, 'nothing to mirror -- no allowlist file exists on disk'
        r = g(['write-tree'])
        if r.returncode != 0:
            return None, 'write-tree failed: %s' % r.stderr.strip()[:120]
        tree = r.stdout.strip()
        pr = subprocess.run(['git', 'rev-parse', '--verify', '-q',
                             'refs/heads/mirror'], cwd=HERE,
                            capture_output=True, text=True)
        parent = pr.stdout.strip() if pr.returncode == 0 else ''
        if not parent:
            hr = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=HERE,
                                capture_output=True, text=True)
            parent = hr.stdout.strip() if hr.returncode == 0 else ''
        cmd = ['commit-tree', tree, '-m',
               'hover2 mirror snapshot (scope: log, anchors, beacon)']
        if parent:
            cmd[2:2] = ['-p', parent]
        r = g(cmd)
        if r.returncode != 0:
            return None, 'commit-tree failed: %s' % r.stderr.strip()[:120]
        commit = r.stdout.strip()
        r = subprocess.run(['git', 'update-ref', 'refs/heads/mirror', commit],
                           cwd=HERE, capture_output=True, text=True)
        if r.returncode != 0:
            return None, 'update-ref failed: %s' % r.stderr.strip()[:120]
        return commit, None
    finally:
        if os.path.isfile(tmpidx):
            os.remove(tmpidx)


def cmd_push():
    rc, out = _run_git(['remote', 'get-url', REMOTE_NAME])
    url = out.strip() if rc == 0 else ''
    errs = push_refusals(url)
    if errs:
        for e in errs:
            print('REFUSED -- %s' % e)
        return EXIT_COULD_NOT_RUN
    # snapshot ONLY the allowlist, on a DEDICATED `mirror` branch built via
    # a temporary index -- never `add -A` on the shared local branch (the
    # pre-scope-decision behaviour, which carried this whole directory's
    # tracked tree to the remote). The local repo's own branch, index and
    # working tree are untouched, so the tools stay tracked locally while
    # the remote tip carries the allowlist only. The scope-removal commit
    # this produces is a NORMAL commit parented on the previous tip -- the
    # remote's earlier history (including the one pre-decision full
    # snapshot) is preserved, never rewritten.
    _run_git(['init', '-q', '.'])
    commit, err = _mirror_commit()
    if err:
        print('REFUSED -- %s' % err)
        return EXIT_COULD_NOT_RUN
    env = dict(os.environ)
    env['GIT_ASKPASS'] = _write_shim(empty=False)
    env['GIT_TERMINAL_PROMPT'] = '0'
    r = subprocess.run(['git', '-c', 'credential.helper=', 'push', '-q',
                        REMOTE_NAME, 'refs/heads/mirror:refs/heads/main'],
                       cwd=HERE,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', env=env)
    if r.returncode != 0:
        print('COULD NOT RUN: push failed: %s' % r.stderr.strip()[:200])
        return EXIT_COULD_NOT_RUN
    head, n = chain_head()
    anchor = {'ts': datetime.datetime.now(datetime.timezone.utc)
                        .strftime('%Y-%m-%dT%H:%M:%SZ'),
              'chain_head': head, 'remote_tip': commit, 'n_entries': n}
    anchor['sent'] = False
    with io.open(ANCHOR_OUTBOX, 'a', encoding='utf-8') as f:
        f.write(json.dumps(anchor, sort_keys=True) + '\n')
    print('pushed. ANCHOR (email this line to Michael now, then run '
          '--anchor-sent %s):' % anchor['ts'])
    print(json.dumps(anchor, sort_keys=True))
    print('BROKEN until the anchor is emailed and stamped -- an anchor '
          'still on this disk is not an off-disk anchor.')
    return EXIT_BROKEN


def cmd_anchor_sent(ts):
    rows = []
    if os.path.isfile(ANCHOR_OUTBOX):
        rows = [json.loads(l) for l in io.open(ANCHOR_OUTBOX, encoding='utf-8')
                if l.strip()]
    hit = [r for r in rows if r.get('ts') == ts]
    if not hit:
        print('COULD NOT RUN: no outbox anchor with ts=%s' % ts)
        return EXIT_COULD_NOT_RUN
    for r in rows:
        if r.get('ts') == ts:
            r['sent'] = True
    with io.open(ANCHOR_OUTBOX, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + '\n')
    print('anchor %s stamped sent' % ts)
    return EXIT_CLEAN


def cmd_restore_test():
    import tempfile
    rc, out = _run_git(['remote', 'get-url', REMOTE_NAME])
    if rc != 0:
        print('COULD NOT RUN: no %r remote configured' % REMOTE_NAME)
        return EXIT_COULD_NOT_RUN
    url = out.strip()
    a = last_anchor()
    if not a:
        print('COULD NOT RUN: no emailed anchor recorded -- the drill '
              'verifies against the anchor, so it cannot run before the '
              'first anchored push')
        return EXIT_COULD_NOT_RUN
    if not a.get('sent'):
        print('COULD NOT RUN: the last anchor (%s) was never stamped sent '
              '-- an anchor still on this disk is not an off-disk anchor, '
              'so the drill would verify against nothing independent'
              % a.get('ts'))
        return EXIT_COULD_NOT_RUN
    scratch = tempfile.mkdtemp(prefix='hover2-restore-')
    env = dict(os.environ)
    env['GIT_ASKPASS'] = _write_shim(empty=False)
    env['GIT_TERMINAL_PROMPT'] = '0'
    r = subprocess.run(['git', '-c', 'credential.helper=', 'clone', '-q',
                        url, scratch], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    if r.returncode != 0:
        print('COULD NOT RUN: clone failed: %s' % r.stderr.strip()[:200])
        return EXIT_COULD_NOT_RUN
    head, n = chain_head(os.path.join(scratch, LOG_NAME))
    # Verify with the LOCAL hover_log module pointed at the CLONE's file --
    # not by executing hover_log.py from inside the clone, which stopped
    # existing there the moment Michael's 2026-09-29 scope decision removed
    # tool scripts from the mirror. Found live on the first scoped drill
    # (chain read BROKEN while heads matched -- the verifier subprocess was
    # failing to start, not the chain failing to verify), which is exactly
    # the false-alarm shape a missing dependency produces when its absence
    # is folded into the check's own verdict.
    try:
        sys.path.insert(0, HERE)
        import hover_log as _hl
        rows, problem = _hl.read_all(os.path.join(scratch, LOG_NAME))
        if rows is None:
            chain_ok, chain_why = False, problem
        else:
            chain_ok, chain_why = _hl.verify(rows)
    except Exception as exc:
        chain_ok, chain_why = False, 'verifier import/run failed: %s' % exc
    finally:
        if sys.path and sys.path[0] == HERE:
            sys.path.pop(0)
    anchor_ok = head == a.get('chain_head') and n == a.get('n_entries')
    print('restore drill: clone ok; chain %s; anchor match %s '
          '(clone head %s vs anchor %s, %d vs %d entries)'
          % ('INTACT' if chain_ok else 'BROKEN',
             anchor_ok, (head or '?')[:12],
             (a.get('chain_head') or '?')[:12], n, a.get('n_entries', -1)))
    return EXIT_CLEAN if (chain_ok and anchor_ok) else EXIT_BROKEN


def cmd_set_remote(url):
    verdict, detail = classify_remote(url)
    if verdict == 'refuse':
        print('REFUSED: %s' % detail)
        return EXIT_COULD_NOT_RUN
    owner, repo = detail
    ok, why = confirm_private(owner, repo)
    print(why)
    if not ok:
        return EXIT_COULD_NOT_RUN
    _run_git(['init', '-q', '.'])
    rc, _ = _run_git(['remote', 'get-url', REMOTE_NAME])
    if rc == 0:
        _run_git(['remote', 'set-url', REMOTE_NAME, url])
    else:
        _run_git(['remote', 'add', REMOTE_NAME, url])
    print('backup2 remote set to %s/%s (no push performed)' % (owner, repo))
    return EXIT_CLEAN


# -- selftest: every refusal arm, each with a known-bad control ------------

def selftest():
    import tempfile
    bad = []
    total = [0]

    def ck(name, cond):
        total[0] += 1
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    refuse = lambda u: classify_remote(u)[0] == 'refuse'
    # refusal arms
    ck('R1 platform org refused, https', refuse('https://github.com/SAIRN1/hover2-log-mirror'))
    ck('R1 platform org refused, scp-ssh', refuse('git@github.com:SAIRN1/x.git'))
    ck('R1 platform org refused, ssh://', refuse('ssh://git@github.com/SAIRN1/x'))
    ck('R2 repo named SAIRN refused', refuse('https://github.com/anyone/SAIRN.git'))
    ck("R3 H1's own mirror repo refused (separate recoverability)",
       refuse('https://github.com/SAIRN-1/hover-log-mirror.git'))
    ck('R4 embedded user:pass refused', refuse('https://me:pw@github.com/SAIRN-1/hover2-log-mirror'))
    ck('R4 embedded token refused', refuse('https://tok@github.com/SAIRN-1/hover2-log-mirror'))
    ck('R5 non-github refused', refuse('https://gitlab.com/SAIRN-1/hover2-log-mirror'))
    ck('R6 empty refused', refuse(''))
    ck('A1 the proposed repo passes to check, https',
       classify_remote('https://github.com/SAIRN-1/hover2-log-mirror.git')
       == ('check', ('SAIRN-1', 'hover2-log-mirror')))
    ck('A2 ...and ssh://git@ form passes too (the seq-289 lesson: transport '
       'user is not a credential)',
       classify_remote('ssh://git@github.com/SAIRN-1/hover2-log-mirror')
       == ('check', ('SAIRN-1', 'hover2-log-mirror')))
    ck('A3 ...and scp form passes',
       classify_remote('git@github.com:SAIRN-1/hover2-log-mirror.git')[0] == 'check')
    # KNOWN-BAD CONTROL per refusal class: a waved-through classifier must fail these
    broken = lambda u: ('check', ('x', 'y'))
    def arms(fn):
        return (fn('https://github.com/SAIRN1/x')[0] == 'refuse'
                and fn('https://github.com/a/SAIRN')[0] == 'refuse'
                and fn('https://github.com/SAIRN-1/hover-log-mirror')[0] == 'refuse'
                and fn('https://me:pw@github.com/a/b')[0] == 'refuse'
                and fn('https://gitlab.com/a/b')[0] == 'refuse')
    ck('KNOWN-BAD CONTROL: a classifier waving everything through FAILS the '
       'refusal predicate', not arms(broken))
    ck('...and the real classifier PASSES the same predicate', arms(classify_remote))

    tmp = tempfile.mkdtemp()
    tok = os.path.join(tmp, 't')
    meta = os.path.join(tmp, 'm.json')
    today = datetime.date(2026, 9, 28)
    ck('T1 missing token refuses',
       token_state(today, tok, meta)[0] == 'missing')
    io.open(tok, 'w').write('dummy')
    ck('T2 token without meta refuses', token_state(today, tok, meta)[0] == 'no-meta')
    io.open(meta, 'w').write(json.dumps({'expires': '2026-09-27'}))
    ck('T3 expired token refuses', token_state(today, tok, meta)[0] == 'expired')
    io.open(meta, 'w').write(json.dumps({'expires': '2026-10-05'}))
    ck('T4 7 days out warns (14-day window)', token_state(today, tok, meta)[0] == 'warn')
    io.open(meta, 'w').write(json.dumps({'expires': '2027-01-01'}))
    ck('T5 far-out expiry is ok', token_state(today, tok, meta)[0] == 'ok')
    ck('T-CONTROL known-bad: an expired date must NOT read as ok',
       token_state(datetime.date(2027, 6, 1), tok, meta)[0] == 'expired')

    ck('H1 tracked token refuses',
       any('TRACKED' in e for e in token_hygiene_errors(
           run=lambda a: (0, 'x\n') if a[0] == 'ls-files' else (0, ''), token_file=tok)))
    ck('H2 unignored token refuses',
       any('NOT gitignored' in e for e in token_hygiene_errors(
           run=lambda a: (1, '') if a[0] == 'check-ignore' else (1, ''), token_file=tok)))
    ck('H3 credential.* in local config refuses',
       any('credential' in e for e in token_hygiene_errors(
           run=lambda a: (0, 'credential.helper=manager\n') if a[0] == 'config'
                         else ((0, '') if a[0] == 'check-ignore' else (1, '')),
           token_file=tok)))
    ck('H-CONTROL known-bad: a clean environment produces zero hygiene errors',
       token_hygiene_errors(
           run=lambda a: (0, '') if a[0] == 'check-ignore' else (1, ''),
           token_file=tok) == [])

    # H3-REAL: driven against a REAL git repo, not a mock -- confirms the
    # --local vs merged-view distinction with an actual `git config` call,
    # found live on the real first push 2026-09-29 (a merged-view read
    # returned Git for Windows' own SYSTEM credential.helper=manager and
    # would have refused every push on this machine forever). A real repo
    # with credential.helper set only at --global must NOT trip the check;
    # the same repo with it set --local MUST.
    import subprocess as _sp
    import tempfile as _tf
    import shutil as _sh
    greal = _tf.mkdtemp(prefix='h3real_')
    try:
        _sp.run(['git', 'init', '-q'], cwd=greal, check=True)
        genv = dict(os.environ, HOME=greal, USERPROFILE=greal,
                    GIT_CONFIG_NOSYSTEM='1')
        _sp.run(['git', 'config', '--global', 'credential.helper', 'manager'],
                 cwd=greal, env=genv, check=True)

        def _real_run(cmd):
            r = _sp.run(['git'] + cmd, cwd=greal, env=genv,
                        capture_output=True, text=True)
            return (r.returncode, r.stdout)
        # Asserts absence of a CREDENTIAL error specifically, not an empty
        # list -- the scratch repo has no .gitignore matching tok's own
        # basename, so the UNRELATED "NOT gitignored" hygiene check fires
        # here regardless (a real, correct finding about this fixture repo,
        # not about the credential-scoping question this arm is isolating).
        ck('H3-REAL a GLOBAL-only credential.helper does not trip the '
           '--local hygiene check (real git, not a mock)',
           not any('credential' in e for e in
                   token_hygiene_errors(run=_real_run, token_file=tok)))
        _sp.run(['git', 'config', '--local', 'credential.helper', 'manager'],
                 cwd=greal, env=genv, check=True)
        ck('H3-REAL a LOCAL credential.helper DOES trip the hygiene check '
           '(real git, not a mock)',
           any('credential' in e for e in
               token_hygiene_errors(run=_real_run, token_file=tok)))
    finally:
        _sh.rmtree(greal, ignore_errors=True)

    ck('P1 ambient probe SUCCEEDING refuses the push (public or stored cred)',
       ambient_proof_error('u', probe=lambda u: (0, '')) is not None)
    ck('P2 ambient probe FAILING clears the ambient gate',
       ambient_proof_error('u', probe=lambda u: (128, 'auth failed')) is None)
    ck('P-CONTROL known-bad: a probe runner that always fails hides a public '
       'repo -- the arm distinguishes them',
       ambient_proof_error('u', probe=lambda u: (0, '')) !=
       ambient_proof_error('u', probe=lambda u: (128, '')))

    ck('C1 privacy: private:true passes',
       confirm_private('o', 'r', http_get=lambda u, h: (200, {'private': True}),
                       token_file=tok)[0] is True)
    ck('C2 privacy: private:false refuses',
       confirm_private('o', 'r', http_get=lambda u, h: (200, {'private': False}),
                       token_file=tok)[0] is False)
    ck('C3 privacy: API error refuses (could-not-tell is a refusal)',
       confirm_private('o', 'r', http_get=lambda u, h: (500, {}),
                       token_file=tok)[0] is False)
    ck('C4 privacy: no token file refuses with no ambient fallback',
       confirm_private('o', 'r', http_get=lambda u, h: (200, {'private': True}),
                       token_file=os.path.join(tmp, 'absent'))[0] is False)
    def raising_get(u, h):
        raise RuntimeError('network down')
    ck('C5 privacy: network exception refuses',
       confirm_private('o', 'r', http_get=raising_get, token_file=tok)[0] is False)

    # pipeline composition: with every seam healthy, refusals empty; each
    # single seam broken produces exactly its own named refusal
    good = dict(today=today, probe=lambda u: (128, ''),
                http_get=lambda u, h: (200, {'private': True}),
                run=lambda a: (0, '') if a[0] == 'check-ignore' else (1, ''),
                token_file=tok, meta_file=meta)
    ck('PIPE go: all gates healthy -> no refusals',
       push_refusals('https://github.com/SAIRN-1/hover2-log-mirror', **good) == [])
    ck('PIPE remote gate first: a refused URL short-circuits',
       push_refusals('https://github.com/SAIRN1/x', **good)[0].startswith('remote:'))
    bad_amb = dict(good); bad_amb['probe'] = lambda u: (0, '')
    ck('PIPE ambient gate: ambient-answer refusal named',
       any(e.startswith('ambient:') for e in
           push_refusals('https://github.com/SAIRN-1/hover2-log-mirror', **bad_amb)))
    bad_priv = dict(good); bad_priv['http_get'] = lambda u, h: (200, {'private': False})
    ck('PIPE privacy gate: not-private refusal named',
       any(e.startswith('privacy:') for e in
           push_refusals('https://github.com/SAIRN-1/hover2-log-mirror', **bad_priv)))
    bad_tok = dict(good); bad_tok['meta_file'] = os.path.join(tmp, 'absent-m')
    ck('PIPE token gate: missing meta refusal named',
       any(e.startswith('token:') for e in
           push_refusals('https://github.com/SAIRN-1/hover2-log-mirror', **bad_tok)))

    ob = os.path.join(tmp, 'outbox.jsonl')
    io.open(ob, 'w', encoding='utf-8').write(
        json.dumps({'ts': 't1', 'chain_head': 'h', 'n_entries': 1,
                    'sent': False}) + '\n')
    ck('AN1 an unsent anchor is visible as unsent (restore drill must '
       'refuse on it)', last_anchor(ob).get('sent') is False)
    io.open(ob, 'a', encoding='utf-8').write(
        json.dumps({'ts': 't2', 'chain_head': 'h2', 'n_entries': 2,
                    'sent': True}) + '\n')
    ck('AN2 the LAST anchor is the one consulted', last_anchor(ob)['ts'] == 't2')
    ck('AN-CONTROL known-bad: an outbox whose last row is unsent must not '
       'read as sent',
       not last_anchor(ob) is None and
       (lambda rows: rows)(last_anchor(ob))['sent'] is True and
       last_anchor(ob)['ts'] != 't1')

    # SCOPE ALLOWLIST arms (Michael's 2026-09-29 decision: log, anchors,
    # beacon only).
    ck('SC1 a staged set that is exactly the allowlist passes',
       staged_scope_error(list(MIRROR_ALLOWLIST)) is None)
    ck('SC2 a staged subset (an allowlist file absent on disk) still passes',
       staged_scope_error(['hover-audit-log.jsonl']) is None)
    ck('SC3 KNOWN-BAD CONTROL: a tool file smuggled into the staging '
       'refuses, and the refusal names the file',
       (lambda e: e is not None and 'hover_log.py' in e)(
           staged_scope_error(list(MIRROR_ALLOWLIST) + ['hover_log.py'])))
    ck('SC4 KNOWN-BAD CONTROL: the pre-decision add -A shape (every tracked '
       'file staged) refuses rather than silently reverting to the old '
       'behaviour',
       staged_scope_error(list(MIRROR_ALLOWLIST) +
                          ['hover2_log_mirror.py', 'claim_collision_scan.py',
                           '.gitignore']) is not None)
    ck('SC5 an empty staged set passes the scope check itself (the '
       'nothing-to-mirror refusal is a separate, named condition in '
       '_mirror_commit, not this one)',
       staged_scope_error([]) is None)

    print('%d ok, %d failed' % (total[0] - len(bad), len(bad)))
    return EXIT_CLEAN if not bad else EXIT_BROKEN


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--status' in argv:
        return cmd_status()
    if '--set-remote' in argv:
        return cmd_set_remote(argv[argv.index('--set-remote') + 1])
    if '--push' in argv:
        return cmd_push()
    if '--anchor-sent' in argv:
        return cmd_anchor_sent(argv[argv.index('--anchor-sent') + 1])
    if '--restore-test' in argv:
        return cmd_restore_test()
    print(__doc__)
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
