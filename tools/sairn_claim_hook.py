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


def try_refresh(repo):
    """Best-effort. Returns True if claims were refreshed from origin."""
    try:
        r = subprocess.run(['git', 'fetch', 'origin'], cwd=repo,
                           capture_output=True, timeout=FETCH_TIMEOUT)
        if r.returncode != 0:
            return False
        # Read the claims as they exist on origin/main. Another session's claim
        # is only visible here after this step; without it the hook reports on
        # whatever this clone last happened to pull.
        subprocess.run(['git', 'checkout', 'origin/main', '--', '.claude/claims'],
                       cwd=repo, capture_output=True, timeout=FETCH_TIMEOUT)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def read_claims(repo):
    out = []
    for path in sorted(glob.glob(os.path.join(repo, '.claude', 'claims', '*.json'))):
        try:
            with open(path, encoding='utf-8') as f:
                doc = json.load(f)
        except (ValueError, OSError):
            continue        # a broken file must never break session start
        for c in doc.get('claims', []):
            out.append(c)
    return out


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
    fresh = try_refresh(repo)

    now = time.time()
    active = []
    for c in read_claims(repo):
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
        lines.append('NOTE: `git fetch` failed or timed out (%ds), so the claim '
                     'list above is only as current as this clone\'s last '
                     'fetch and MAY BE INCOMPLETE. Treat "no claims" as '
                     '"unknown", not as "nobody is working".' % FETCH_TIMEOUT)

    emit('\n'.join(lines))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Fail open, loudly in nothing and silently in everything. A session
        # must always start, whatever went wrong in here.
        sys.exit(0)
