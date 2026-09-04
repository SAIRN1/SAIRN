#!/usr/bin/env python
"""sairn_claim_hook.py -- SessionStart hook: what is every OTHER session on?

Companion to tools/sairn_claim.py. That tool answers "is anyone already doing
THIS?", which requires knowing what you are about to do. At session start nobody
knows that yet -- so this answers the question that CAN be answered then:

    who else is holding an active work claim right now, and on what?

That is the automatic half of the 2026-08-30 convention. The manual half stays:
run `sairn_claim.py check <subject>` before an unassigned gate, because a
subject-specific overlap test is strictly better than a list. This exists so a
session that never runs the tool still sees the other three.

── DESIGN CONSTRAINTS, ALL THREE LOAD-BEARING ─────────────────────────────
1. ADVISORY, NEVER BLOCKING. It reports and gets out of the way. The decision
   to proceed belongs to whoever is starting the session.
2. FAILS OPEN on every error, matching every other hook on this platform. A
   hook that crashes closed gets disabled, and a disabled hook protects
   nothing. Every failure path here ends in a clean exit 0.
3. FAST, AND HONEST WHEN IT IS NOT. Claims travel by git, so a truthful answer
   needs a fetch, and a fetch can hang. The fetch is capped at FETCH_TIMEOUT.
   On timeout it does NOT silently fall back to stale local data pretending to
   be current -- it reports what it has AND says the fetch failed, because a
   confidently wrong "nobody else is working" is worse than no check at all.
4. READ-ONLY ON THE REPO, and not merely by intention. It fetches and then
   reads origin/main's claim files with `git show`. It must never write the
   working tree or the index -- see read_origin_claims() for the version of
   this hook that did, and what that cost. Held by
   tests/claims/run_push_verify_probe.py section 8.

Silent when there is nothing to say: no other session holding a claim means no
output, so this costs a session that is alone exactly one line of noise: none.

Usage (SessionStart hook):  python tools/sairn_claim_hook.py
"""
import glob
import json
import os
import subprocess
import sys
import time

FETCH_TIMEOUT = 8          # seconds; a session start must not hang on the network
STALE_HOURS = float(os.environ.get('SAIRN_CLAIM_STALE_HOURS', '4'))


def repo_root(start):
    """Nearest ancestor that is a git repo AND participates in the claim system.

    THE `.claude/claims` REQUIREMENT IS NOT COSMETIC. `C:\\Users\\marsh` is
    itself a git repo, so a plain walk-up finds a repo from ANY directory under
    the home folder. Without this guard the hook fires on every unrelated
    project on this machine and, since that repo has no origin to fetch, greets
    each one with a spurious "git fetch failed" warning. Found while testing
    exactly that case. A repo with no claims directory is not using this system
    and must be left alone in silence.
    """
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, '.git')):
            if os.path.isdir(os.path.join(d, '.claude', 'claims')):
                return d
            return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def session_name(repo):
    base = os.path.basename(repo)
    return base[6:].lower() if base.lower().startswith('sairn-') else base.lower()


def try_fetch(repo):
    """Best-effort `git fetch`. Returns True if origin/main is now current.

    Fetch ONLY. It updates a remote-tracking ref and writes nothing into the
    working tree or the index.
    """
    try:
        r = subprocess.run(['git', 'fetch', 'origin'], cwd=repo,
                           capture_output=True, timeout=FETCH_TIMEOUT)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def read_origin_claims(repo):
    """Every session's claim file AS IT EXISTS ON origin/main, read without
    touching the working tree. Returns a list of claims, or None if unreadable.

    ── WHY NOT `git checkout origin/main -- .claude/claims` (2026-09-04) ──────
    This hook used to do exactly that, and it is the same defect
    tools/sairn_claim.py was fixed for earlier the same day -- fixed there and
    NOT here, which meant the danger was never actually closed, only closed in
    the copy a session is LESS likely to run. This one runs automatically at
    every single session start.

    `git checkout <ref> -- path` OVERWRITES the working tree, so a claim written
    but not yet committed was silently gone. It also STAGES what it wrote:
    observed live on 2026-09-04 in SAIRN-fourth, where a plain session start
    left `M .claude/claims/hank.json` staged. Any later `git commit` sweeping
    the index would have committed whatever origin happened to hold at that
    moment -- including, in the general case, a revert of a claim this clone
    had already made. The tool that exists to stop sessions colliding, deleting
    the record of one, from a step that reads as read-only.

    `git show` reads the same bytes and cannot write anything.
    """
    ls = subprocess.run(['git', 'ls-tree', '--name-only', 'origin/main',
                         '.claude/claims/'], cwd=repo,
                        capture_output=True, text=True, timeout=FETCH_TIMEOUT)
    if ls.returncode != 0:
        return None
    out = []
    for path in ls.stdout.split('\n'):
        path = path.strip()
        if not path.endswith('.json'):
            continue
        r = subprocess.run(['git', 'show', 'origin/main:' + path], cwd=repo,
                           capture_output=True, text=True, timeout=FETCH_TIMEOUT)
        if r.returncode != 0:
            continue
        try:
            doc = json.loads(r.stdout)
        except ValueError:
            continue        # a broken file must never break session start
        out.extend(doc.get('claims', []))
    return out


def read_local_claims(repo):
    """This clone's own copies. The fallback when origin cannot be read -- and
    a weaker answer, because another session's claim is only a fact once it is
    on origin. The caller says so rather than presenting it as current."""
    out = []
    for path in sorted(glob.glob(os.path.join(repo, '.claude', 'claims', '*.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                doc = json.load(f)
        except (ValueError, OSError):
            continue        # a broken file must never break session start
        out.extend(doc.get('claims', []))
    return out


def read_claims(repo, fresh):
    """Claims as origin/main holds them, falling back to disk. Returns
    (claims, fresh) -- fresh goes False if the origin read failed, so a
    fallback answer is never reported as a current one."""
    if fresh:
        try:
            claims = read_origin_claims(repo)
        except (OSError, subprocess.SubprocessError):
            claims = None
        if claims is not None:
            return claims, True
        fresh = False
    return read_local_claims(repo), fresh


def emit(text):
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'SessionStart',
            'additionalContext': text
        },
        'suppressOutput': True
    }))


def main():
    repo = repo_root(os.getcwd())
    if not repo:
        return 0
    me = session_name(repo)
    claims, fresh = read_claims(repo, try_fetch(repo))

    now = time.time()
    active = []
    for c in claims:
        if c.get('session') == me or c.get('status') != 'active':
            continue
        age_h = (now - c.get('claimed_at_epoch', 0)) / 3600.0
        if age_h < STALE_HOURS:
            active.append((age_h, c))

    if not active and fresh:
        return 0            # nobody else is on anything: say nothing

    lines = []
    if active:
        lines.append('WORK CLAIMS -- %d other session(s) are holding an active '
                     'claim right now:' % len(active))
        lines.append('')
        for age_h, c in sorted(active):
            lines.append('  %s -- %s: %s  (claimed %.1fh ago)'
                         % (c.get('session'), c.get('subject'),
                            c.get('task'), age_h))
        lines.append('')
        lines.append('This is ADVISORY, not a block. Nothing here stops you '
                     'working. But if what you are about to be asked to do '
                     'overlaps one of these, say so to the user BEFORE '
                     'starting, rather than discovering it in a rebase after '
                     'four hours -- which is the failure this exists to '
                     'prevent (2026-08-30, SAIRNfreedom gates, run twice).')
        lines.append('Before any unassigned research or build gate, run: '
                     'python tools/sairn_claim.py check <subject> <task words>')

    if not fresh:
        if lines:
            lines.append('')
        lines.append('NOTE: could not read .claude/claims from origin/main '
                     '(`git fetch` failed or timed out at %ds, or the ref was '
                     'unreadable), so the list above came from THIS CLONE\'S '
                     'copy and is only as current as its last fetch. It MAY BE '
                     'INCOMPLETE. Treat "no claims" as "unknown", not as '
                     '"nobody is working".' % FETCH_TIMEOUT)

    emit('\n'.join(lines))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Fail open, loudly in nothing and silently in everything. A session
        # must always start, whatever went wrong in here.
        sys.exit(0)
