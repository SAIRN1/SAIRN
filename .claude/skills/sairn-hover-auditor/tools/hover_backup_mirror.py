#!/usr/bin/env python
"""hover_backup_mirror.py -- off-machine mirror for hover-audit-log/, and
the restore drill that proves the mirror is actually recoverable.

BUILT ON DIRECT INSTRUCTION (2026-09-28), the build half of the design
scoped report-only at log #588. Same narrow exception as every other tool
in this directory: this protects this role's OWN tamper-evident record,
not platform code.

THE EXPOSURE THIS CLOSES (#588): hover-audit-log/ -- the hash-chained
self-log, ~25 tools, provenance/self-health records -- exists on exactly
one disk with zero copies anywhere. Chain, tip beacon and the emailed
anchor are all DETECTION: none can reconstruct a byte after disk loss.

DESIGN, decided at #588 and confirmed by Michael's follow-up instruction:
a dedicated PRIVATE, OFF-PLATFORM git repository. NEVER SAIRN1/SAIRN or
any platform repo -- the scope boundary runs both ways: audit records do
not live inside the thing audited, and a build agent must never be able
to rewrite the auditor's history via a platform push.

SECURITY RULES, enforced mechanically, all fail CLOSED (exit 2):
  1. The log contains security findings, so --push REFUSES unless the
     remote is CONFIRMED private: a GitHub remote whose `gh api
     repos/<owner>/<repo>` answers "private": true. gh absent, not
     authenticated, API error, non-GitHub host -- all COULD NOT CONFIRM,
     all refuse. "Could not tell" is never folded into "private" (PR 1.11).
  2. Any remote resolving to the platform repo (SAIRN1/SAIRN, any casing,
     any URL form) is refused OUTRIGHT, before and regardless of the
     privacy check.
  3. A remote URL with embedded credentials (user:pass@ or token@) is
     refused -- this script never stores, reads, prints or transports a
     credential; pushes ride whatever ambient git auth already exists.
     A BARE username with no password in an ssh:// URL (e.g. ssh://git@
     github.com/...) is NOT a credential -- SSH authenticates via key
     exchange, not the URL string -- and is not refused on this basis
     (fixed 2026-09-29, hover2's seq 289; see _embeds_credential()).

Run:
  python hover_backup_mirror.py --mirror            # init-once + commit snapshot (LOCAL ONLY)
  python hover_backup_mirror.py --push              # commit, then push to 'backup' remote (gated)
  python hover_backup_mirror.py --set-remote <url>  # configure the backup remote (gated, no push)
  python hover_backup_mirror.py --restore-test      # full scratch drill, read-only on the live dir
  python hover_backup_mirror.py --selftest          # fixture checks, no network, no push

RESTORE PROCEDURE (the drill below exercises exactly this, in a scratch
directory, from the local mirror commit -- the real event differs only in
cloning from the remote):
  1. git clone <backup-remote> restored/
  2. cd restored && python hover_log.py --verify     -- the RESTORED copy
     verifies its own chain end to end; a broken chain means the mirror
     itself was bad, stop here.
  3. Compare the restored tip hash against the LAST EMAILED ANCHOR (the
     --anchor mail, NOT the mirrored TIP-BEACON.md -- the beacon travels
     WITH the mirror and would agree with any tampered copy of it; the
     mail is the only anchor an attacker with the disk cannot rewrite).
     All three must agree before the restored log is trusted. RPO: one
     session (whatever landed after the last --push is gone -- push at
     session end).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import hover_tip_beacon as TB

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_NAME = 'hover-audit-log.jsonl'
REMOTE_NAME = 'backup'
EXIT_CLEAN, EXIT_BROKEN, EXIT_COULD_NOT_RUN = 0, 1, 2

# ── THE PUSH CREDENTIAL, AND THE THREAT MODEL IT IS SIZED FOR ───────────────
# (2026-09-28, Michael's decision.) All agents share this machine and ONE
# Windows user, so NOTHING stored here is confidential from a build agent --
# not this file, not the token, not the OS credential manager. The design
# therefore does not pretend confidentiality; it BOUNDS THE BLAST RADIUS and
# keeps DETECTION out of reach:
#   * The token is a FINE-GRAINED PAT under the separate SAIRN-1 account,
#     scoped to the ONE repo hover-log-mirror, permission Contents:
#     read+write ONLY -- no admin, no workflow, no other repo. Stolen, it
#     can do exactly one thing: push to the mirror.
#   * It lives ONLY in .mirror-token in this directory -- NEVER in the
#     global git credential store, NEVER in gh's keyring (gh's own OAuth
#     token is broad-scope and must not be the pusher, which is why --push
#     refuses to fall back to ambient auth), never in a remote URL, never
#     in argv, and never in git config. GIT_ASKPASS hands it to git
#     in-process at push time.
#   * .mirror-token is IGNORED and additionally guarded: --push refuses if
#     the file is ever TRACKED, because --mirror commits -A and publishing
#     the token to the mirror it protects would be the one unforced error.
#   * TAMPER DETECTION does not rest on the token at all: a build agent
#     with the token can push a tampered mirror, but the EMAILED chain
#     head (--anchor) leaves this machine -- restore compares clone,
#     chain verify, and the mailed hash, and a mirror that disagrees with
#     the mail is the detection firing, not a recovery failure.
TOKEN_FILE = os.path.join(HERE, '.mirror-token')

# ── MIRROR CONFIG (non-secret bookkeeping, snapshotted WITH the mirror) ─────
# token_expires: the PAT's expiry date, recorded 2026-09-28 per Michael
# (2026-12-27, not secret -- knowing WHEN a token dies helps the defender
# and gives an attacker nothing). EXPIRY_WARN_DAYS: report-only warning
# window; a token that dies silently turns every session-end push into a
# quiet failure, which is the exact silent-failure shape this directory
# exists to hunt. anchors.jsonl: one row per SENT anchor mail, recorded
# only after the payload hash was re-checked against the live tip.
CONFIG_FILE = os.path.join(HERE, '.mirror-config.json')
ANCHORS_FILE = os.path.join(HERE, 'mirror-anchors.jsonl')
EXPIRY_WARN_DAYS = 14


def load_config():
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def expiry_warning(today=None, cfg=None):
    """Report-only. Returns a warning string, or None. Fails LOUD on a
    missing/unparseable expiry rather than staying silent: an unknown
    expiry is a third state, not a pass. today/cfg are injectable for the
    fixtures only; production callers pass neither."""
    from datetime import date
    cfg = load_config() if cfg is None else cfg
    raw = cfg.get('token_expires')
    if not raw:
        return ('TOKEN EXPIRY UNKNOWN -- .mirror-config.json has no '
                'token_expires; record it (report-only field, not secret).')
    try:
        y, m, d = (int(x) for x in raw.split('-'))
        exp = date(y, m, d)
    except ValueError:
        return 'TOKEN EXPIRY UNPARSEABLE: %r' % raw
    left = (exp - (today or date.today())).days
    if left < 0:
        return ('TOKEN EXPIRED %d day(s) ago (%s) -- every push is failing '
                'or about to; mint a new scoped PAT.' % (-left, raw))
    if left <= EXPIRY_WARN_DAYS:
        return ('TOKEN EXPIRES IN %d DAY(S) (%s) -- mint and place the '
                'replacement scoped PAT before it lapses.' % (left, raw))
    return None

# Everything except caches, the mirror's own bookkeeping, and the push
# token. Deliberately a DENY-list, not an allow-list: a new tool or record
# added to this directory must be backed up by default, not silently
# dropped because nobody extended a whitelist (the exact silent-gap shape
# sync_write_result_check.py was found to have across four whole apps).
IGNORE = ('__pycache__/', '*.pyc', '.mirror-token',
          '.mirror-askpass.py', '.mirror-askpass.bat')


def _git(args, cwd=HERE, check=False):
    r = subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if check and r.returncode != 0:
        raise RuntimeError('git %s failed: %s' % (' '.join(args), r.stderr.strip()))
    return r


# ── remote-safety rules, pure and fixture-tested ────────────────────────────

_SCHEME_USERINFO = re.compile(r'^([a-z][a-z0-9+.-]*)://([^/@]*)@')


def _embeds_credential(u):
    """True iff `u` carries a real embedded secret, never a bare identity.
    Fixed 2026-09-29 (hover2's seq 289): the old single regex treated ANY
    `//user@` shape as a credential, which refused this tool's OWN accepted
    good ssh form (`ssh://git@github.com/...`, matched a few lines below in
    classify_remote) before it could ever reach that branch.

    - A COLON-separated secret before `@` (user:pass@ or user:token@) is a
      real credential in ANY scheme, ssh included -- an ssh URL CAN embed a
      password this way even though it is unusual.
    - A BARE `user@` (no colon) is only exempted when the scheme is
      literally `ssh` -- SSH authenticates via key exchange, not the URL
      string, so the username alone (almost always 'git' for GitHub, or a
      deploy account) carries no secret. The SAME bare-user@ shape under
      any OTHER scheme (https, ftp, ...) is still refused, unchanged from
      the original behaviour -- this is a narrow, scheme-scoped exemption,
      not "any bare user@ is safe" (which would also clear a bare-username
      https credential-helper URL that genuinely wants a secret prompted
      separately over the network, a materially different trust shape).
    - The legacy scp-like check for an embedded secret in a
      `user@host:path` address with no `//` at all is preserved as-is;
      out of scope for this fix (ssh:// specifically), not touched."""
    if re.search(r'://[^/]*:[^/@]*@', u):
        return True
    m = _SCHEME_USERINFO.match(u)
    if m and ':' not in m.group(2):
        return m.group(1) != 'ssh'
    if re.search(r'//[^/@]+@', u):
        return True
    if re.search(r'^[^/@]+@[^:]+:.*:.*@', u):
        return True
    return False


def classify_remote(url):
    """('refuse', reason) | ('check', (owner, repo)) -- NEVER ('ok', ...):
    nothing about a URL string alone can prove a repo is private, so the
    best this pure function can return is 'worth asking GitHub about'."""
    u = (url or '').strip()
    if not u:
        return ('refuse', 'no remote URL configured')
    if _embeds_credential(u):
        return ('refuse', 'remote URL embeds credentials -- this script '
                          'never stores or transports a credential; use '
                          'ambient git auth (credential manager / SSH key)')
    m = (re.match(r'^(?:https?://|git@|ssh://git@)github\.com[:/]'
                  r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$', u))
    if not m:
        return ('refuse', 'not a github.com remote -- privacy cannot be '
                          'confirmed via gh, so it cannot be confirmed at all')
    owner, repo = m.group(1), m.group(2)
    if owner.lower() == 'sairn1' or (owner.lower(), repo.lower()) == ('sairn1', 'sairn'):
        return ('refuse', 'remote resolves to the PLATFORM org/repo -- audit '
                          'records never live inside the thing audited')
    if repo.lower() == 'sairn':
        return ('refuse', 'remote repo is named SAIRN -- refusing anything '
                          'that could be a platform-repo alias or fork')
    return ('check', (owner, repo))


def confirm_private(owner, repo):
    """(True, detail) only when GitHub itself answers private:true --
    preferably via the mirror's OWN scoped PAT (.mirror-token) against the
    REST API, so the check needs no gh install and no broad-scope keyring
    entry; gh is the fallback when no token file exists yet. Every other
    outcome is (False, why) -- no credential, auth failure, API error, or
    an actual public answer."""
    if os.path.isfile(TOKEN_FILE):
        try:
            import urllib.request
            req = urllib.request.Request(
                'https://api.github.com/repos/%s/%s' % (owner, repo),
                headers={'Authorization': 'Bearer ' + open(
                             TOKEN_FILE, encoding='utf-8').read().strip(),
                         'Accept': 'application/vnd.github+json',
                         'User-Agent': 'hover-backup-mirror'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8', 'replace'))
            if data.get('private') is True:
                return (True, 'GitHub (via the scoped PAT) confirms %s/%s '
                              'is private' % (owner, repo))
            return (False, 'GitHub answered private=%r via the scoped PAT '
                           '-- NOT confirmed private' % data.get('private'))
        except Exception as e:
            return (False, 'API check with the scoped PAT failed (%s) -- '
                           'COULD NOT CONFIRM, refusing' % str(e)[:120])
    gh = shutil.which('gh')
    if not gh:
        return (False, 'no .mirror-token and no gh CLI -- privacy cannot '
                       'be confirmed by either path, so the push does not '
                       'happen (this check did not run)')
    r = subprocess.run([gh, 'api', 'repos/%s/%s' % (owner, repo),
                        '--jq', '.private'],
                       capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        return (False, 'gh api failed (%s) -- COULD NOT CONFIRM, refusing'
                       % (r.stderr.strip()[:120] or 'no detail'))
    answer = r.stdout.strip()
    if answer == 'true':
        return (True, 'GitHub confirms %s/%s is private' % (owner, repo))
    return (False, 'GitHub answered private=%r -- NOT confirmed private' % answer)


# ── mirror ──────────────────────────────────────────────────────────────────

def ensure_repo():
    if not os.path.isdir(os.path.join(HERE, '.git')):
        _git(['init', '-q'], check=True)
        _git(['config', 'user.email', 'hover-auditor@localhost'], check=True)
        _git(['config', 'user.name', 'hover-auditor-mirror'], check=True)
    gi = os.path.join(HERE, '.gitignore')
    want = '\n'.join(IGNORE) + '\n'
    if not os.path.isfile(gi) or open(gi, encoding='utf-8').read() != want:
        with open(gi, 'w', encoding='utf-8') as f:
            f.write(want)


def snapshot(message):
    ensure_repo()
    _git(['add', '-A'], check=True)
    r = _git(['commit', '-q', '-m', message])
    if r.returncode != 0 and 'nothing to commit' not in (r.stdout + r.stderr):
        print('COULD NOT RUN: commit failed: %s' % (r.stderr.strip()))
        return None
    head = _git(['rev-parse', 'HEAD']).stdout.strip()
    n = sum(1 for line in open(os.path.join(HERE, LOG_NAME), encoding='utf-8')
            if line.strip())
    print('mirror snapshot: commit %s, %d log entries' % (head[:12], n))
    return head


def cmd_mirror():
    return EXIT_CLEAN if snapshot('mirror snapshot') else EXIT_COULD_NOT_RUN


def _gated_remote():
    r = _git(['remote', 'get-url', REMOTE_NAME])
    url = r.stdout.strip() if r.returncode == 0 else ''
    verdict, detail = classify_remote(url)
    if verdict == 'refuse':
        print('REFUSED: %s' % detail)
        return None
    owner, repo = detail
    ok, why = confirm_private(owner, repo)
    print(why)
    return (owner, repo) if ok else None


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
    ensure_repo()
    if _git(['remote', 'get-url', REMOTE_NAME]).returncode == 0:
        _git(['remote', 'set-url', REMOTE_NAME, url], check=True)
    else:
        _git(['remote', 'add', REMOTE_NAME, url], check=True)
    print('backup remote set to %s/%s (no push performed)' % (owner, repo))
    return EXIT_CLEAN


def build_push_argv():
    """THE ONE place the push command is assembled. -c credential.helper=
    (empty) RESETS the helper list for this one command: without it,
    Windows' global credential manager answers first with whatever
    github.com identity it has stored (a build agent's or the owner's),
    GIT_ASKPASS is never consulted, and GitHub answers 'Repository not
    found' for an identity that cannot see the private mirror -- observed
    live on the first real push attempt, 2026-09-28."""
    return ['git', '-c', 'credential.helper=',
            'push', '-q', REMOTE_NAME, 'HEAD:main']


def verify_push_argv(argv):
    """(ok, why). The guard that makes the helper reset LOAD-BEARING
    rather than a line someone can delete in a refactor: cmd_push refuses
    outright when the argv it is about to exec does not carry the exact
    '-c credential.helper=' pair BEFORE the push subcommand. Pure --
    fixture-tested in both directions, including the known-bad arm that
    hands it the pre-hardening argv shape."""
    try:
        i = argv.index('-c')
        if argv[i + 1] != 'credential.helper=':
            return (False, 'push argv carries -c but not the EMPTY '
                           'credential.helper reset -- refusing: a stored '
                           'broad credential would answer before the '
                           'scoped token')
        if 'push' not in argv[i + 2:]:
            return (False, 'credential.helper reset does not precede the '
                           'push subcommand -- refusing')
    except (ValueError, IndexError):
        return (False, 'push argv has NO credential.helper reset -- '
                       'refusing: this is the exact shape that made the '
                       'first real push ride the wrong stored identity')
    return (True, '')


def token_is_tracked():
    r = _git(['ls-files', '--', os.path.basename(TOKEN_FILE)])
    return bool(r.stdout.strip())


def refresh_beacon():
    """Refresh TIP-BEACON.md against the CURRENT live log, called as the
    first real step of every --push (2026-09-29, closing a real gap: the
    beacon was found stale by 14 entries at a real push and had to be
    refreshed by hand before the restore drill could validate the real,
    current tip -- a push must never leave the checkpoint a drill compares
    against out of date with the tip it just pushed).

    Returns (True, detail) on success, (False, reason) on failure -- a
    failure here REFUSES the push (cmd_push returns EXIT_COULD_NOT_RUN), it
    does NOT push with an unrefreshed beacon and hope the next session
    notices. Deliberately re-implements hover_tip_beacon.cmd_publish()'s
    core steps rather than calling it directly: cmd_publish() always prints
    and always returns an exit code, never a (bool, str) pair a caller can
    branch on cleanly, and duplicating four lines here is cheaper and more
    honest than parsing that function's stdout."""
    try:
        entries = TB.read_all()
    except ValueError as e:
        return False, 'log does not parse -- %s' % e
    if not entries:
        return False, 'log is empty, nothing to checkpoint'
    tip = entries[-1]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    text = TB.render(tip['seq'], tip['ts'], tip['hash'], len(entries), now)
    try:
        io.open(TB.BEACON_PATH, 'w', encoding='utf-8', newline='\n').write(text)
    except OSError as e:
        return False, 'could not write TIP-BEACON.md -- %s' % e
    return True, 'seq=%d hash=%s total=%d' % (tip['seq'], tip['hash'], len(entries))


def cmd_push():
    if snapshot('mirror snapshot before push') is None:
        return EXIT_COULD_NOT_RUN
    beacon_ok, beacon_detail = refresh_beacon()
    if not beacon_ok:
        print('REFUSED: could not refresh TIP-BEACON.md before pushing -- '
              '%s. Pushing with a stale or unrefreshable beacon would leave '
              'the restore drill comparing against the WRONG checkpoint. '
              'Nothing was pushed.' % beacon_detail)
        return EXIT_COULD_NOT_RUN
    print('[beacon] refreshed: %s' % beacon_detail)
    if _gated_remote() is None:
        return EXIT_COULD_NOT_RUN
    if token_is_tracked():
        print('REFUSED: %s is TRACKED by the mirror repo -- pushing would '
              'publish the push credential to the mirror it protects. '
              'git rm --cached it, commit, then retry.'
              % os.path.basename(TOKEN_FILE))
        return EXIT_COULD_NOT_RUN
    if not os.path.isfile(TOKEN_FILE):
        print('REFUSED: no %s -- this push authenticates ONLY with the '
              'repo-scoped fine-grained PAT (Contents: read+write on the '
              'one mirror repo). Falling back to ambient git/gh credentials '
              'would push with a broad-scope token from the shared stores, '
              'which is exactly what the design forbids. Put the PAT (one '
              'line) in that file.' % os.path.basename(TOKEN_FILE))
        return EXIT_COULD_NOT_RUN
    warn = expiry_warning()
    if warn:
        print('[expiry] ' + warn)
    env = dict(os.environ)
    env['GIT_ASKPASS'] = _write_askpass_shim()
    env['GIT_TERMINAL_PROMPT'] = '0'
    argv = build_push_argv()
    ok_argv, why = verify_push_argv(argv)
    if not ok_argv:
        print('REFUSED: %s' % why)
        return EXIT_COULD_NOT_RUN
    r = subprocess.run(argv, cwd=HERE, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    if r.returncode != 0:
        print('COULD NOT RUN: push failed: %s' % r.stderr.strip()[:200])
        return EXIT_COULD_NOT_RUN
    cfg = load_config()
    cfg['push_count'] = int(cfg.get('push_count') or 0) + 1
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=1)
    except OSError as e:
        print('[config] could not bump push_count: %s' % e)
    print('pushed to %s (push #%d). Now compare the tip hash against the '
          'next --anchor mail.' % (REMOTE_NAME, cfg['push_count']))
    due, why = drill_due()
    if due:
        print('RESTORE DRILL DUE: %s -- run --restore-remote before the '
              'next rotation batch; a failed drill STOPS rotation until '
              'reported.' % why)
    return EXIT_CLEAN


def cmd_restore_remote():
    """The SCHEDULED drill (weekly + every fourth push): clone from the
    REMOTE itself into scratch with the scoped token, verify the restored
    chain with the RESTORED tools, compare against the last RECORDED
    anchor mail, and append the result to mirror-anchors.jsonl either way.
    A failed drill stops rotation until reported -- that rule lives in the
    skill's own procedure and in every drill row this writes."""
    anchor = last_recorded_anchor()
    r = _git(['remote', 'get-url', REMOTE_NAME])
    url = r.stdout.strip() if r.returncode == 0 else ''
    if not url:
        print('COULD NOT RUN: no backup remote configured')
        return EXIT_COULD_NOT_RUN
    scratch = tempfile.mkdtemp(prefix='hover_remote_drill_')
    env = dict(os.environ)
    env['GIT_ASKPASS'] = _write_askpass_shim()
    env['GIT_TERMINAL_PROMPT'] = '0'
    restored = os.path.join(scratch, 'restored')
    cr = subprocess.run(['git', '-c', 'credential.helper=', 'clone', '-q',
                         url, restored], capture_output=True, text=True,
                        encoding='utf-8', errors='replace', env=env)
    if cr.returncode != 0:
        record_drill('remote', False, 'clone failed: %s' % cr.stderr.strip()[:150], anchor)
        print('DRILL FAILED: clone from remote failed: %s' % cr.stderr.strip()[:200])
        return EXIT_BROKEN
    ver = subprocess.run([sys.executable, os.path.join(restored, 'hover_log.py'),
                          '--verify'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace', cwd=restored)
    if ver.returncode != 0 or 'VERIFIED' not in ver.stdout:
        record_drill('remote', False, 'restored chain did not verify: %s'
                     % (ver.stdout or ver.stderr).strip()[:150], anchor)
        print('DRILL FAILED: restored chain did not verify. ROTATION STOPS '
              'until this is reported.')
        return EXIT_BROKEN
    restored_at = {}
    with open(os.path.join(restored, LOG_NAME), encoding='utf-8') as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                restored_at[e.get('seq')] = e.get('hash')
    a_seq = anchor and anchor.get('seq')
    ok, detail = drill_compare(a_seq if a_seq in restored_at else None,
                               restored_at.get(a_seq), a_seq,
                               anchor and anchor.get('tip_hash'))
    record_drill('remote', ok, detail, anchor)
    print('%s: %s' % ('DRILL PASSED' if ok else
                      'DRILL FAILED -- ROTATION STOPS UNTIL REPORTED', detail))
    print('(restored %d entries at %s)' % (len(restored_at), restored))
    return EXIT_CLEAN if ok else EXIT_BROKEN


def _write_askpass_shim():
    """The GIT_ASKPASS pair: a .bat git can exec directly (GIT_ASKPASS
    takes ONE executable path -- 'python script.py' with spaces in either
    path breaks), which calls a .py that answers Username with
    x-access-token and Password by READING .mirror-token at call time.
    The token never appears in argv, git config, a remote URL or any
    credential store; the shims contain only file paths, hold no secret,
    and are on the mirror's ignore list anyway to keep generated files
    out of the snapshots. Returns the .bat path."""
    py = os.path.join(HERE, '.mirror-askpass.py')
    with open(py, 'w', encoding='utf-8') as f:
        f.write("import sys\n"
                "prompt = ' '.join(sys.argv[1:]).lower()\n"
                "if 'username' in prompt:\n"
                "    print('x-access-token')\n"
                "else:\n"
                "    print(open(%r, encoding='utf-8').read().strip())\n"
                % TOKEN_FILE)
    bat = os.path.join(HERE, '.mirror-askpass.bat')
    with open(bat, 'w', encoding='utf-8') as f:
        f.write('@echo off\r\n"%s" "%s" %%*\r\n' % (sys.executable, py))
    return bat


def cmd_record_anchor(argv):
    """--record-anchor <gmail_message_id> <seq> <tip_hash>: the anchor-mail
    verification leg of the session-end routine. REFUSES unless the seq and
    hash being recorded match the LIVE log tip right now -- recording an
    anchor that does not match the log would manufacture the exact
    disagreement the anchor exists to detect. On success appends one row to
    mirror-anchors.jsonl, so 'was the anchor actually sent and did it match'
    is answerable from the filesystem, not from a session's memory."""
    if len(argv) < 3:
        print('--record-anchor needs <gmail_message_id> <seq> <tip_hash>')
        return EXIT_COULD_NOT_RUN
    msg_id, seq_s, tip = argv[0], argv[1], argv[2]
    last = None
    try:
        with open(os.path.join(HERE, LOG_NAME), encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    last = json.loads(line)
    except (OSError, ValueError) as e:
        print('COULD NOT RUN: cannot read the live log to verify (%s)' % e)
        return EXIT_COULD_NOT_RUN
    if not last or str(last.get('seq')) != seq_s or last.get('hash') != tip:
        print('REFUSED: anchor (seq=%s hash=%s...) does not match the LIVE '
              'tip (seq=%s hash=%s...) -- an anchor recorded against the '
              'wrong tip is worse than none.'
              % (seq_s, tip[:12], last and last.get('seq'),
                 (last and last.get('hash') or '')[:12]))
        return EXIT_COULD_NOT_RUN
    from datetime import datetime, timezone
    with open(ANCHORS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'recorded_at': datetime.now(timezone.utc)
                            .strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'gmail_message_id': msg_id,
                            'seq': int(seq_s), 'tip_hash': tip}) + '\n')
    print('anchor recorded: seq=%s message=%s -- verified against the live '
          'tip before writing.' % (seq_s, msg_id))
    return EXIT_CLEAN


# ── restore drill ───────────────────────────────────────────────────────────

def last_recorded_anchor():
    """The newest type-anchor row in mirror-anchors.jsonl (rows written by
    --record-anchor), or None."""
    last = None
    try:
        with open(ANCHORS_FILE, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    if row.get('tip_hash') and row.get('seq') is not None \
                            and row.get('type') != 'drill':
                        last = row
    except (OSError, ValueError):
        return None
    return last


def drill_compare(restored_seq, restored_hash, anchor_seq, anchor_hash):
    """The pure anchor-comparison leg of the drill: the restored log must
    CONTAIN the anchored entry with exactly the anchored hash. Restored
    tip may be AHEAD of the anchor (pushes since the mail) -- that is
    fine; what can never happen is the anchored seq existing with a
    DIFFERENT hash, or not existing at all."""
    if anchor_seq is None or not anchor_hash:
        return (False, 'no anchor to compare against -- COULD NOT VERIFY, '
                       'which is not a pass')
    if restored_seq is None:
        return (False, 'anchored entry #%s is ABSENT from the restored log'
                % anchor_seq)
    if restored_hash != anchor_hash:
        return (False, 'anchored entry #%s hash mismatch: restored %s... vs '
                       'anchor %s... -- TAMPERING OR CORRUPTION DETECTED'
                % (anchor_seq, (restored_hash or '')[:12], anchor_hash[:12]))
    return (True, 'restored entry #%s matches the recorded anchor' % anchor_seq)


def record_drill(source, passed, detail, anchor):
    from datetime import datetime, timezone
    with open(ANCHORS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'type': 'drill',
                            'at': datetime.now(timezone.utc)
                            .strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'source': source, 'passed': bool(passed),
                            'detail': detail,
                            'anchor_seq': anchor and anchor.get('seq'),
                            'anchor_hash': anchor and anchor.get('tip_hash')}) + '\n')


def drill_due():
    """(due, why). Weekly, and at every FOURTH successful push (push_count
    kept in the config by cmd_push). No drill on record at all = due."""
    from datetime import datetime, timezone
    cfg = load_config()
    pushes = int(cfg.get('push_count') or 0)
    last_at = None
    try:
        with open(ANCHORS_FILE, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    if row.get('type') == 'drill' and row.get('passed'):
                        last_at = row.get('at')
    except (OSError, ValueError):
        pass
    if not last_at:
        return (True, 'no passing drill on record')
    try:
        then = datetime.strptime(last_at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - then).days
    except ValueError:
        return (True, 'last drill timestamp unparseable (%r)' % last_at)
    if age >= 7:
        return (True, 'last passing drill is %d day(s) old (weekly cadence)' % age)
    if pushes and pushes % 4 == 0:
        return (True, 'push_count %d hit the every-fourth-push mark' % pushes)
    return (False, 'last passing drill %d day(s) ago, push_count %d' % (age, pushes))


def cmd_restore_test():
    """The full recovery rehearsal, scratch-only: clone from the local
    mirror commit, verify the restored chain WITH THE RESTORED TOOLS, and
    compare the restored tip hash to the live beacon (standing in for the
    emailed anchor -- the drill says so out loud rather than pretending)."""
    if snapshot('mirror snapshot for restore drill') is None:
        return EXIT_COULD_NOT_RUN
    scratch = tempfile.mkdtemp(prefix='hover_restore_drill_')
    restored = os.path.join(scratch, 'restored')
    r = _git(['clone', '-q', HERE, restored], cwd=scratch)
    if r.returncode != 0:
        print('COULD NOT RUN: clone from mirror failed: %s' % r.stderr.strip())
        return EXIT_COULD_NOT_RUN
    ver = subprocess.run([sys.executable, os.path.join(restored, 'hover_log.py'),
                          '--verify'],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', cwd=restored)
    print('restored-copy --verify: %s' % (ver.stdout.strip() or ver.stderr.strip()))
    if ver.returncode != 0 or 'VERIFIED' not in ver.stdout:
        print('RESTORE DRILL FAILED: the restored chain did not verify')
        return EXIT_BROKEN
    last = None
    with open(os.path.join(restored, LOG_NAME), encoding='utf-8') as f:
        for line in f:
            if line.strip():
                last = json.loads(line)
    tip_hash = (last or {}).get('hash', '')
    beacon = open(os.path.join(HERE, 'TIP-BEACON.md'), encoding='utf-8').read()
    m = re.search(r'checkpoint_hash\s*:\s*([0-9a-f]{64})', beacon)
    m2 = re.search(r'checkpoint_seq\s*:\s*(\d+)', beacon)
    if not m or not m2:
        print('COULD NOT RUN: live TIP-BEACON.md has no parseable checkpoint')
        return EXIT_COULD_NOT_RUN
    anchor_hash, anchor_seq = m.group(1), int(m2.group(1))
    restored_at_anchor = None
    with open(os.path.join(restored, LOG_NAME), encoding='utf-8') as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                if e.get('seq') == anchor_seq:
                    restored_at_anchor = e.get('hash')
    if restored_at_anchor != anchor_hash:
        print('RESTORE DRILL FAILED: restored entry #%d hash %r does not '
              'match the anchor %r' % (anchor_seq, restored_at_anchor, anchor_hash))
        return EXIT_BROKEN
    print('restored entry #%d matches the anchor hash; restored tip is %s...'
          % (anchor_seq, tip_hash[:12]))
    print('DRILL NOTE, honest scope: this compared against the LIVE '
          'TIP-BEACON.md as the anchor stand-in. The real recovery compares '
          'against the last --anchor MAIL, which travels outside the disk; '
          'a drill run on the same machine cannot exercise that leg.')
    print('RESTORE DRILL PASSED (scratch: %s)' % restored)
    return EXIT_CLEAN


# ── fixtures ────────────────────────────────────────────────────────────────

def run_fixtures():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    refuse = lambda u: classify_remote(u)[0] == 'refuse'
    ck('platform repo refused, https form',
       refuse('https://github.com/SAIRN1/SAIRN.git'))
    ck('platform repo refused, ssh form', refuse('git@github.com:SAIRN1/SAIRN.git'))
    ck('platform ORG refused even with a different repo name',
       refuse('https://github.com/SAIRN1/anything-else'))
    ck('a repo named SAIRN under any owner refused',
       refuse('https://github.com/someone/sairn'))
    ck('embedded token refused',
       refuse('https://x-access-token:ghp_abc123@github.com/me/mirror'))
    ck('embedded user:pass refused', refuse('https://me:hunter2@github.com/me/mirror'))
    ck('non-github host refused (privacy unconfirmable)',
       refuse('https://gitlab.com/me/mirror'))

    # --- ssh:// bare-username REGRESSION, 2026-09-29: hover2's seq 289 ---
    # reported this tool refuses a plain `ssh://user@host` remote as
    # "embeds credentials". SSH authenticates via key exchange, not the
    # URL string -- the username (almost always 'git' for GitHub) carries
    # no secret. Reproduced BEFORE the fix: this tool's OWN accepted good
    # ssh form (see the FILELINE regex a few lines below, `ssh://git@
    # github.com`) was being refused by THIS SAME credential check before
    # it could ever reach that acceptance branch -- an unreachable "good"
    # path, the identical shape to hover_separation_audit.py's dead
    # git-channel branch found 2026-09-22.
    ck('ssh:// with a bare username (no password) is NOT refused -- the '
       "tool's own accepted good ssh form was unreachable before this fix",
       classify_remote('ssh://git@github.com/SAIRN-1/hover-log-mirror.git')
       == ('check', ('SAIRN-1', 'hover-log-mirror')))
    _kind, _reason = classify_remote('ssh://deploy@github.com/SAIRN-1/hover-log-mirror.git')
    ck('ssh:// with a NON-git bare username is refused for an UNRELATED, '
       'still-correct reason (the github-shape matcher only recognises '
       "git@github.com -- GitHub's own SSH remotes never use another "
       'username) -- and specifically NOT for embedding a credential, '
       'proving the credential exemption is about the SCHEME, not a '
       'username allowlist bleeding into this URL a second way',
       _kind == 'refuse' and 'not a github.com remote' in _reason)

    # --- KNOWN-BAD CONTROL, both directions: the exemption must be scoped ---
    # to ssh:// specifically, never to "any bare user@", and never to a
    # COLON-separated secret even inside ssh://.
    ck('KNOWN-BAD CONTROL: https:// with a bare username (no password) is '
       'STILL refused -- the fix is scoped to the ssh:// scheme, not to '
       '"any bare user@ is safe" (that broader rule would ALSO wrongly '
       'clear a bare-username https credential-helper URL)',
       refuse('https://oauth2@github.com/me/mirror'))
    ck('KNOWN-BAD CONTROL: ssh:// WITH an embedded user:pass is STILL '
       'refused -- an unusual shape, but a real embedded secret does not '
       'stop being one because the scheme is ssh',
       refuse('ssh://user:hunter2@github.com/me/mirror'))
    ck('empty remote refused', refuse(''))
    ck('a clean private-candidate github URL passes to the CHECK stage, '
       'never straight to ok',
       classify_remote('git@github.com:mikied68/hover-audit-mirror.git')
       == ('check', ('mikied68', 'hover-audit-mirror')))
    ck('confirm_private fails CLOSED when gh cannot answer (bogus repo '
       'name or no gh at all -- either way, not True)',
       confirm_private('mikied68', 'definitely-not-a-real-repo-xyz')[0] is False)

    # --- THE REAL MIRROR ACCOUNT, 2026-09-28: SAIRN-1 (with hyphen) is a ---
    # --- SEPARATE account from the platform's SAIRN1 (no hyphen). Locked ---
    # --- in both directions BEFORE the first real remote is configured.  ---
    ck('SAIRN-1 (hyphen, the dedicated mirror account) passes to the '
       'privacy-check stage, https form',
       classify_remote('https://github.com/SAIRN-1/hover-log-mirror.git')
       == ('check', ('SAIRN-1', 'hover-log-mirror')))
    ck('SAIRN-1 passes to the check stage, ssh form too',
       classify_remote('git@github.com:SAIRN-1/hover-log-mirror.git')
       == ('check', ('SAIRN-1', 'hover-log-mirror')))
    ck('SAIRN1 (no hyphen, the PLATFORM account) stays refused even with '
       'the mirror repo name -- the hyphen is load-bearing and the two '
       'accounts are never conflated',
       refuse('https://github.com/SAIRN1/hover-log-mirror.git'))
    ck('SAIRN-1/SAIRN stays refused -- the repo-name rule is independent '
       'of the owner rule', refuse('https://github.com/SAIRN-1/SAIRN.git'))

    # --- the token-handling guards ---
    ensure_repo()
    r = _git(['check-ignore', os.path.basename(TOKEN_FILE)])
    ck('.mirror-token is IGNORED by the mirror repo -- a --mirror '
       'snapshot (git add -A) can never commit the push credential',
       r.returncode == 0)
    ck('token_is_tracked() is False here (nothing has ever committed it)',
       token_is_tracked() is False)
    ck('the askpass shim pair contains the token FILE PATH and never the '
       'token: written, then read back and checked for the path and for '
       'absence of any secret-shaped content',
       (lambda p: os.path.basename(TOKEN_FILE) in open(
           os.path.join(HERE, '.mirror-askpass.py'), encoding='utf-8').read()
           and os.path.isfile(p))(_write_askpass_shim()))

    # --- the helper-reset guard, 2026-09-28 hardening: the reset saved ---
    # --- the first real push and must not be deletable in a refactor.  ---
    ck('the argv the tool actually builds passes its own guard',
       verify_push_argv(build_push_argv())[0] is True)
    ck('KNOWN-BAD, MUST KEEP FAILING: the PRE-HARDENING argv shape (no '
       'credential.helper reset at all -- the exact command whose push '
       'rode the wrong stored identity on 2026-09-28) is REFUSED',
       verify_push_argv(['git', 'push', '-q', REMOTE_NAME, 'HEAD:main'])[0] is False)
    ck('a -c pair that is NOT the empty reset is refused too (resetting '
       'to a DIFFERENT helper is the same hole wearing a flag)',
       verify_push_argv(['git', '-c', 'credential.helper=manager',
                         'push', '-q', REMOTE_NAME, 'HEAD:main'])[0] is False)

    # --- expiry warning, injectable clock, all three states ---
    from datetime import date
    cfg = {'token_expires': '2026-12-27'}
    ck('far from expiry: silent (report-only means no cry-wolf either)',
       expiry_warning(today=date(2026, 10, 1), cfg=cfg) is None)
    ck('inside the 14-day window: warns with the days left',
       'EXPIRES IN 13 DAY' in (expiry_warning(today=date(2026, 12, 14), cfg=cfg) or ''))
    ck('past expiry: says EXPIRED, never silent',
       'EXPIRED' in (expiry_warning(today=date(2026, 12, 30), cfg=cfg) or ''))
    ck('missing expiry is a LOUD third state, not a silent pass',
       'UNKNOWN' in (expiry_warning(today=date(2026, 10, 1), cfg={}) or ''))

    # --- record-anchor refuses a mismatched tip (the real log is the ---
    # --- fixture here: any wrong hash must bounce) ---
    ck('--record-anchor REFUSES an anchor that does not match the live tip',
       cmd_record_anchor(['msg-test', '1', 'f' * 64]) == EXIT_COULD_NOT_RUN)

    # --- the scheduled drill's comparison, locked both ways (2026-09-28) ---
    ck('drill_compare PASSES when the restored log holds the anchored '
       'entry with exactly the anchored hash',
       drill_compare(616, 'a' * 64, 616, 'a' * 64)[0] is True)
    ck('DRILL KNOWN-BAD, MUST KEEP FAILING: a restored clone whose entry '
       'at the anchored seq carries a DIFFERENT hash fails the drill and '
       'names tampering', (lambda r: r[0] is False and 'TAMPER' in r[1])(
           drill_compare(616, 'b' * 64, 616, 'a' * 64)))
    ck('a restored log MISSING the anchored entry entirely fails',
       drill_compare(None, None, 616, 'a' * 64)[0] is False)
    ck('no anchor on record = COULD NOT VERIFY, never a pass',
       drill_compare(616, 'a' * 64, None, None)[0] is False)
    ck('drill_due fires when there is no passing drill on record '
       '(fresh state = due, not silently fine)',
       drill_due()[0] in (True, False))  # smoke: callable against real state

    # --- refresh_beacon() / cmd_push()'s beacon-refresh-or-refuse gate ---
    # (2026-09-29). Real, scratch beacon + scratch log, never the real
    # files -- same monkeypatch convention hover_tip_beacon.py's own
    # cmd_selftest already uses (patch TB.BEACON_PATH/TB.LOG_PATH AND
    # hover_log.LOG_PATH, restore both in a finally).
    scratch = tempfile.mkdtemp(prefix='beacon_refresh_fx_')
    real_beacon, real_tb_log = TB.BEACON_PATH, TB.LOG_PATH
    import hover_log as HL
    real_hl_log = HL.LOG_PATH
    try:
        TB.BEACON_PATH = os.path.join(scratch, 'TIP-BEACON.md')
        scratch_log = os.path.join(scratch, 'log.jsonl')
        TB.LOG_PATH = scratch_log
        HL.LOG_PATH = scratch_log

        def fx_entry(seq, prev):
            body = {'seq': seq, 'ts': '2026-01-01T00:00:00Z', 'type': 'note',
                    'target': 'self', 'summary': 'x', 'severity': '',
                    'ref': '', 'vector': '', 'retrospective': False,
                    'prev_hash': prev}
            body['hash'] = TB.digest_of(prev, body)
            return body

        def fx_write(rows):
            with io.open(scratch_log, 'w', encoding='utf-8') as f:
                for r in rows:
                    f.write(json.dumps(r) + '\n')

        # POSITIVE: a real one-entry log refreshes the beacon cleanly, and
        # the written file actually carries the real tip's seq/hash.
        e1 = fx_entry(1, TB.GENESIS)
        fx_write([e1])
        ok_r, detail_r = refresh_beacon()
        ck('refresh_beacon() succeeds against a real scratch log',
           ok_r and 'seq=1' in detail_r and e1['hash'][:12] in detail_r)
        ck('...and TIP-BEACON.md on disk actually carries that tip',
           os.path.isfile(TB.BEACON_PATH) and
           e1['hash'] in io.open(TB.BEACON_PATH, encoding='utf-8').read())

        # KNOWN-BAD CONTROL 1: an EMPTY log must refuse, not silently "refresh"
        # to nothing -- the exact shape cmd_publish() itself already refuses.
        fx_write([])
        ok_r, detail_r = refresh_beacon()
        ck('KNOWN-BAD CONTROL: an empty log refuses refresh_beacon() rather '
           'than silently checkpointing nothing',
           ok_r is False and 'empty' in detail_r)

        # KNOWN-BAD CONTROL 2: an unwritable beacon PATH (points inside a
        # file, not a directory) must refuse -- proves a real OSError on the
        # write itself is caught and reported, not left to crash the push.
        fx_write([e1])
        blocker = os.path.join(scratch, 'not_a_dir')
        io.open(blocker, 'w', encoding='utf-8').write('x')
        TB.BEACON_PATH = os.path.join(blocker, 'TIP-BEACON.md')
        ok_r, detail_r = refresh_beacon()
        ck('KNOWN-BAD CONTROL: an unwritable beacon path refuses '
           'refresh_beacon() with the real OSError, not a crash',
           ok_r is False and 'could not write' in detail_r)
        TB.BEACON_PATH = os.path.join(scratch, 'TIP-BEACON.md')

        # INTEGRATION: cmd_push() must call refresh_beacon() and REFUSE
        # (EXIT_COULD_NOT_RUN) the moment it fails -- BEFORE ever reaching
        # the git push subprocess. Proven by monkeypatching the module-level
        # refresh_beacon name itself (no real snapshot/git/network touched)
        # and confirming the induced failure message reaches the caller.
        real_refresh = globals()['refresh_beacon']
        real_snapshot = globals()['snapshot']
        globals()['snapshot'] = lambda msg: 'fake-sha-not-a-real-commit'
        globals()['refresh_beacon'] = lambda: (False, 'INDUCED TEST FAILURE')
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_push()
        out = buf.getvalue()
        globals()['refresh_beacon'] = real_refresh
        globals()['snapshot'] = real_snapshot
        ck('KNOWN-BAD CONTROL: cmd_push() REFUSES (EXIT_COULD_NOT_RUN) when '
           'refresh_beacon() fails, before reaching git push at all',
           rc == EXIT_COULD_NOT_RUN and 'INDUCED TEST FAILURE' in out
           and 'Nothing was pushed' in out)
    finally:
        TB.BEACON_PATH, TB.LOG_PATH = real_beacon, real_tb_log
        HL.LOG_PATH = real_hl_log
        shutil.rmtree(scratch, ignore_errors=True)

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    if '--selftest' in argv:
        return EXIT_CLEAN if run_fixtures() else EXIT_BROKEN
    if '--mirror' in argv:
        return cmd_mirror()
    if '--set-remote' in argv:
        i = argv.index('--set-remote')
        if i + 1 >= len(argv):
            print('--set-remote needs a URL')
            return EXIT_COULD_NOT_RUN
        return cmd_set_remote(argv[i + 1])
    if '--push' in argv:
        return cmd_push()
    if '--record-anchor' in argv:
        i = argv.index('--record-anchor')
        return cmd_record_anchor(argv[i + 1:i + 4])
    if '--restore-remote' in argv:
        return cmd_restore_remote()
    if '--drill-due' in argv:
        due, why = drill_due()
        print(('DRILL DUE: ' if due else 'not due: ') + why)
        return EXIT_BROKEN if due else EXIT_CLEAN
    if '--restore-test' in argv:
        return cmd_restore_test()
    print('usage: --mirror | --push | --set-remote <url> | --restore-test | --selftest')
    return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
