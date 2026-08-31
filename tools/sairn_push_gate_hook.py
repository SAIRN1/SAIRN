"""PreToolUse hook for Bash. Three pre-push checks that must not depend on memory.

  1. SEED LOAD STATE -- blocks a push that ships a reference-seed change while
     the live licence is still serving the old value.
  2. CREDENTIAL-WRITER GUARD -- blocks a push adding or changing a SQL file
     that writes an `*_employee_auth` table without the guard that stops it
     leaving a licence with rows and ZERO active provisioners. SQL is the only
     path into that state; the API cannot reach it.
  3. SQL PREFLIGHT (added 2026-08-31) -- blocks a push whose SQL names a column
     the repo declares no such column for. Runs tools/sairn_sql_preflight.py in
     DECLARED mode, which needs no schema snapshot and so costs an ordinary push
     nothing. It blocks on MISSING_COLUMN only; UNDECLARED_TABLE is reported and
     allowed, because in declared mode that fires on every real table with no
     tracked CREATE TABLE (`license_keys` alone: 17 occurrences of correct code).
     Live-snapshot blocking is deliberately NOT enabled -- that is a separate
     decision about whether every SQL push should require a current snapshot.

Neither runs unless the commits being pushed actually touch the relevant files,
so an ordinary push costs nothing.

CHECK 1 IN DETAIL.

WHY THIS EXISTS
---------------
On 2026-08-27 two committed SAIRNlaw corrections were never LOADED. A seed-file
change is inert until a loader runs, and nobody ran it, so LAW-PINNACLE-2026 --
the canonical customer licence -- computed federal answer deadlines three days
late for a day. It was found by accident, chasing an unrelated false positive.

The push protocol in CLAUDE.md already says to live-verify after pushing. That
step covers deployed CODE. Rule DATA had no equivalent, and "remember to load
the seed you just changed" is exactly the kind of instruction that holds until
the night it doesn't. tools/sairn_load_state_check.py can answer the question
mechanically; this makes it run without anyone remembering to.

WHAT IT DOES
------------
On a `git push`, it looks at the commits actually being pushed. If none of them
touch a reference seed file it allows immediately and costs nothing. If one
does, it runs the load-state gate for the affected apps ONLY, and:

  gate exit 0  -> live already matches the repo. Allow, silently. This is the
                  normal case when you loaded before pushing, and it is why the
                  hook adds no friction to a correct workflow.
  gate exit 1  -> DRIFT. Deny, naming the app and the reload command. The push
                  is not wrong in itself, but shipping a seed change while live
                  still serves the old one is the exact state that produced the
                  original defect.
  gate exit 2  -> COULD NOT TELL (no key, endpoint unreachable). ALLOW, with a
                  loud note. Blocking someone who simply has no licence key
                  would get this hook deleted within a day, and a hook that is
                  deleted checks nothing. It says plainly that it is not a pass.

ORDER DOES NOT MATTER, which is the point. Load-then-push and push-then-load
both end with live == repo; the hook only cares that they agree by the time the
push happens. Loading first is the safer order anyway, because a denied push
costs nothing and a shipped-but-unloaded correction costs a wrong legal date.

CLONE-AGNOSTIC BY CONSTRUCTION. There are four SAIRN clones. The repo is found
from the CWD via `git rev-parse --show-toplevel`, never a fixed path, so the
hook checks the clone the push is actually coming from.

FAILS OPEN on any exception, same standard as git_push_master_guard.py and
redaction_check.py: never let a hook bug block a legitimate command. That is a
deliberate trade -- a hook that crashes closed gets disabled, and then it
protects nothing at all.
"""
import json
import os
import re
import subprocess
import sys

# The canonical licence per app. These are the demo/verification keys already
# committed in sql/*_license_seed.sql -- no secret is introduced by naming them,
# and an env var wins so a session can point the check at another tenant.
APP_KEYS = {
    'sairnlaw': ('SAIRNLAW_LICENSE_KEY', 'LAW-PINNACLE-2026'),
    'sairncare': ('SAIRNCARE_LICENSE_KEY', 'ALF-TEST-2026'),
    'sairndental': ('SAIRNDENTAL_LICENSE_KEY', 'DNT-PINNACLE-2026'),
    'sairnroofing': ('SAIRNROOFING_LICENSE_KEY', 'RF-PINNACLE-2026'),
}

# Which seed files belong to which app. Path-shape rather than a file list, so a
# new jurisdiction or a new seed file is covered the day it is added -- the same
# reason the fingerprint endpoint matches a table NAME SHAPE instead of keeping
# a table list. A new APP still has to be added here, and that is the one thing
# in this file that can go stale.
SEED_PATTERNS = [
    (re.compile(r'^sql/sairnlaw_deadline_.*\.json$'), 'sairnlaw'),
    (re.compile(r'^sql/sairncare_(compliance|payer_rules)_seed.*\.json$'), 'sairncare'),
    (re.compile(r'^sql/sairndental_credentials_seed.*\.json$'), 'sairndental'),
    (re.compile(r'^sql/sairnroofing_(certifications|contingency)_seed.*\.json$'), 'sairnroofing'),
]


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def git(repo, *args):
    out = subprocess.run(['git', '-C', repo] + list(args),
                         capture_output=True, text=True, timeout=20)
    return out.stdout if out.returncode == 0 else ''


def outgoing_files(repo):
    """Files changed by the commits this push would actually send.

    Falls back through three references rather than assuming an upstream is
    configured: @{u} is right when it exists, origin/main is right in this repo,
    and HEAD~1 is a last resort that at least sees the newest commit. Returning
    an EMPTY list means 'no seed touched', so a wrong answer here fails open --
    which is why the fallbacks get progressively wider rather than narrower.
    """
    for ref in ('@{u}', 'origin/main'):
        out = git(repo, 'log', ref + '..HEAD', '--name-only', '--pretty=format:')
        if out.strip():
            return sorted({ln.strip().replace('\\', '/') for ln in out.splitlines() if ln.strip()})
    return []


def main():
    payload = json.load(sys.stdin)
    cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
    if not re.search(r'\bgit\s+push\b', cmd):
        sys.exit(0)

    repo = git(os.getcwd(), 'rev-parse', '--show-toplevel').strip()
    if not repo or not os.path.isdir(os.path.join(repo, 'sql')):
        sys.exit(0)

    checker = os.path.join(repo, 'tools', 'sairn_load_state_check.py')
    if not os.path.isfile(checker):
        sys.exit(0)

    # ── CHECK 2: credential-writer guard on any changed sql/*.sql ──────────
    changed = outgoing_files(repo)
    sql_changed = [q for q in changed if q.startswith('sql/') and q.endswith('.sql')]
    if sql_changed:
        gcheck = os.path.join(repo, 'tools', 'employee_auth_guard_check.py')
        if os.path.isfile(gcheck):
            try:
                g = subprocess.run(
                    [sys.executable, gcheck, '--changed']
                    + [os.path.join(repo, q) for q in sql_changed],
                    capture_output=True, text=True, timeout=60, cwd=repo)
            except Exception:
                g = None
            if g is not None and g.returncode == 1:
                msg = [
                    "Blocked: this push adds or changes a SQL file that writes credential",
                    "rows without the guard that keeps a licence recoverable.",
                    "",
                    g.stdout.strip(),
                    "",
                    "SQL is the ONLY path into the zero-active-provisioner state -- the API",
                    "refuses self-deactivation and refuses to deactivate the last active",
                    "provisioner, so it cannot get there. That is why the guard belongs in",
                    "the file rather than in the app.",
                    "",
                    "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
                ]
                deny(chr(10).join(msg))

        # ── CHECK 3: SQL preflight, declared-only ─────────────────────────
        # Blocks a push whose SQL names a column the repo declares no such
        # column for. DECLARED mode on purpose: it needs no snapshot, so it adds
        # zero freshness friction to an ordinary push. Full --live blocking is a
        # separate, later decision.
        #
        # IT BLOCKS ON MISSING_COLUMN ONLY. UNDECLARED_TABLE fires on every real
        # table with no tracked CREATE TABLE -- `license_keys` alone accounts for
        # 17 across sql/, all correct code -- so blocking on it would stop every
        # licence-seed push on day one, and a gate that cries wolf gets switched
        # off. The tool's --gate mode encodes that split in its EXIT CODE rather
        # than in prose this hook would have to parse, so a change to its output
        # format cannot silently disarm the gate.
        pf = os.path.join(repo, 'tools', 'sairn_sql_preflight.py')
        if os.path.isfile(pf):
            try:
                p = subprocess.run(
                    [sys.executable, pf, '--gate']
                    + [os.path.join(repo, q) for q in sql_changed],
                    capture_output=True, text=True, timeout=120, cwd=repo)
            except Exception:
                p = None
            if p is not None and p.returncode == 1:
                msg = [
                    "Blocked: this push contains SQL naming a column that does not exist.",
                    "",
                    p.stdout.strip(),
                    "",
                    "A wrong column in an INSERT fails loudly and is survivable. A wrong",
                    "column in the WHERE of an UPDATE or DELETE does not fail -- it matches",
                    "nothing and reports success, and '0 rows' is indistinguishable from",
                    "'nothing needed changing'. That is why this blocks before the file can",
                    "be pasted into the editor rather than after.",
                    "",
                    "Checked against the repo's CREATE TABLE / ALTER TABLE ADD COLUMN",
                    "statements, not the database. If the column really does exist because",
                    "it was added by hand in the editor, the fix is to write that ALTER down",
                    "in sql/ -- an undeclared column is the reason this can be wrong, and",
                    "declaring it fixes the gate and the repo at the same time.",
                    "",
                    "Full detail:  python tools/sairn_sql_preflight.py <file>",
                    "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
                ]
                deny(chr(10).join(msg))

    # ── CHECK 1: seed load state ──────────────────────────────
    apps = []
    for path in changed:
        for pattern, app in SEED_PATTERNS:
            if pattern.match(path) and app not in apps:
                apps.append(app)
    if not apps:
        sys.exit(0)

    drifted, untold = [], []
    for app in apps:
        env_name, default_key = APP_KEYS[app]
        key = os.environ.get(env_name) or default_key
        try:
            r = subprocess.run(
                [sys.executable, checker, '--app', app, '--key', key],
                capture_output=True, text=True, timeout=60, cwd=repo)
        except Exception:
            untold.append((app, 'the check could not be run'))
            continue
        if r.returncode == 1:
            tail = [ln for ln in r.stdout.splitlines()
                    if ln.strip().startswith(('MISSING', 'STALE', 'EXTRA', '=='))
                    or 'seed ' in ln and '!= live' in ln]
            drifted.append((app, key, tail[-12:]))
        elif r.returncode != 0:
            untold.append((app, (r.stdout.strip().splitlines() or ['no output'])[-1]))

    if drifted:
        lines = [
            "Blocked: this push ships a reference-seed change while the live licence still holds the old value.",
            "",
            "A seed-file change is INERT until a loader runs. That is the exact defect this gate exists for --",
            "on 2026-08-27 two committed corrections were never loaded and the canonical SAIRNlaw licence",
            "computed federal answer deadlines three days late for a day.",
            "",
        ]
        for app, key, tail in drifted:
            lines.append("  %s (%s) -- tools/sairn_load_state_check.py --app %s reports drift:" % (app, key, app))
            lines.extend("      " + t for t in tail)
            lines.append("")
        lines += [
            "Load first, then push. For SAIRNlaw:  python tools/load_deadline_seed.py <jurisdiction>",
            "Then verify by a CHANGED result on identical inputs -- a loader's exit code is not evidence.",
            "",
            "If the drift is deliberate and unrelated to this push, re-run with SAIRN_SEED_GATE=off in the",
            "environment. Say so out loud when you do; an override nobody mentions is how this gets hollowed out.",
        ]
        deny("\n".join(lines))

    if untold:
        # Not a block. Not a pass either, and it says so rather than being silent.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext":
                    "Seed-load gate COULD NOT TELL for: "
                    + "; ".join("%s (%s)" % (a, why) for a, why in untold)
                    + ". The push is allowed because a missing licence key must not block a legitimate "
                      "push, but nothing was verified about that app's live rules. Run "
                      "tools/sairn_load_state_check.py --app <app> --key <key> and report the real result "
                      "rather than treating this as a pass."
            }
        }))
    sys.exit(0)


if __name__ == '__main__':
    try:
        if os.environ.get('SAIRN_SEED_GATE', '').lower() == 'off':
            sys.exit(0)
        main()
    except Exception:
        # Fail open -- never let a hook bug block a legitimate command.
        sys.exit(0)
