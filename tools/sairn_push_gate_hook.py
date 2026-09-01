"""Pre-push checks that must not depend on memory. FOUR of them as of 2026-09-01.

DO NOT TRUST THAT NUMBER -- count the `CHECK n:` markers in this file. A count
in a header is exactly the kind of claim that goes stale the day someone adds
the fifth, and CLAUDE.md already records the Guardian skill drifting to three
different check counts at once.

TWO ENTRY POINTS, and the difference matters more than the checks do:

  * PreToolUse (Bash) -- fires when the command TEXT matches a git push. Fast
    feedback inside a session, and structurally leaky: it cannot see a push
    driven from Python (tools/sairn_claim.py), and it runs BEFORE the command
    executes, so `git add && git commit && git push` in one call is invisible
    to it -- at hook time the commit does not exist yet. Both holes were hit
    in production on 2026-09-01, hours apart, by different sessions.

  * pre-push (git, via .githooks/pre-push --pre-push) -- fires on the git
    OPERATION. Every caller, every spelling, and always after the commit
    exists. This is the one that actually holds; install it per clone with
    tools/install_git_hooks.py.

  1. SEED LOAD STATE -- blocks a push that ships a reference-seed change while
     the live licence is still serving the old value.
  2. CREDENTIAL-WRITER GUARD -- blocks a push adding or changing a SQL file
     that writes an `*_employee_auth` table without the guard that stops it
     leaving a licence with rows and ZERO active provisioners. SQL is the only
     path into that state; the API cannot reach it.
  3. SQL PREFLIGHT (added 2026-08-31, switched to LIVE + FAIL-CLOSED 2026-09-01)
     -- blocks a push whose SQL names a table or column the live database does
     not have. Checked against db/schema_snapshot.json (override with
     SAIRN_SCHEMA_SNAPSHOT), produced by running sql/schema_snapshot_query.sql
     in the Supabase editor. If that snapshot is missing, unreadable or empty,
     THE PUSH IS DENIED -- see the block comment at the check itself for why
     that is not the same trade as check 1's could-not-tell allowance.
  4. ENDPOINT/ENGINE SEAM (added 2026-09-01) -- blocks a push where an endpoint
     does not forward every input its api/_lib engine reads. SAIRNlaw's engine
     grew a `service_methods` input, api/legal-deadlines.js was never updated,
     and Florida deadlines came back five days late for five days with both
     test suites green, because they call the engine directly and never
     traverse the endpoint. Runs on any api/*.js change, not only on changed
     endpoints: editing the ENGINE is how the seam breaks, and the endpoint
     that stops matching it is a file the push never touched.

None of them run unless the commits being pushed actually touch the relevant
files, so an ordinary push costs nothing.

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


# ── TWO ENTRY POINTS, ONE SET OF CHECKS -- added 2026-09-01 ────────────────
# This file used to be reachable ONE way: as a Claude Code PreToolUse hook that
# fires when the Bash COMMAND TEXT matches \bgit\s+push\b. That is a gate on
# how a push was spelled, not on the push.
#
# tools/sairn_claim.py pushes with subprocess.run(['git','push','origin',
# 'HEAD:main']) from inside Python. No Bash command text ever contains "git
# push", the regex never matches, and EVERY claim and release call sent
# whatever commits were sitting on the branch straight past all three checks.
#
# That was not theoretical. On 2026-09-01 this gate DENIED a commit touching
# sql/ for a missing schema snapshot, and minutes later `sairn_claim.py claim`
# pushed the identical commit to origin, unchecked. The gate was not overridden
# and did not fail -- it was simply never asked.
#
# So the checks now also run as a git PRE-PUSH hook, which git invokes for any
# push from any caller: Bash, a Python subprocess, an IDE, a script nobody has
# written yet. `--pre-push` selects that mode; the check bodies are identical
# and are deliberately NOT duplicated, because two copies of a gate is how one
# of them silently goes stale.
MODE = 'pretooluse'


def deny(reason):
    if MODE == 'prepush':
        # Non-zero from a pre-push hook aborts the push itself. stderr, because
        # git relays it to whoever ran the push -- including a subprocess caller
        # that only ever looks at returncode and stderr.
        sys.stderr.write('\n' + reason + '\n\n')
        sys.stderr.write('(blocked by .githooks/pre-push -> tools/sairn_push_gate_hook.py --pre-push)\n')
        sys.exit(1)
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


def outgoing_files(repo, base=None):
    """Files changed by the commits this push would actually send.

    Falls back through three references rather than assuming an upstream is
    configured: @{u} is right when it exists, origin/main is right in this repo,
    and HEAD~1 is a last resort that at least sees the newest commit. Returning
    an EMPTY list means 'no seed touched', so a wrong answer here fails open --
    which is why the fallbacks get progressively wider rather than narrower.

    `base` is the remote sha git hands a PRE-PUSH hook on stdin. It is strictly
    better than origin/main when present, because it is what the REMOTE has
    right now rather than what this clone last fetched -- the same stale-ref
    trap that made the deploy-drift hook false-alarm three times in one night.
    """
    refs = ([base] if base else []) + ['@{u}', 'origin/main']
    for ref in refs:
        out = git(repo, 'log', ref + '..HEAD', '--name-only', '--pretty=format:')
        if out.strip():
            return sorted({ln.strip().replace('\\', '/') for ln in out.splitlines() if ln.strip()})
    return []


def prepush_base():
    """Remote sha for the ref being pushed, read from git's pre-push stdin.

    Format per `git help hooks`: '<local ref> <local sha> <remote ref> <remote
    sha>' per line. An all-zero remote sha means a brand-new branch, which has
    no base -- return None and let the caller fall back rather than diffing
    against a sha that does not exist.

    A push that only DELETES refs ships no content and is exempt: git sends an
    all-zero LOCAL sha for a deletion. Without this, `git push origin --delete
    somebranch` was refused while HEAD happened to sit on a branch with
    uncommitted-looking SQL outgoing -- verified 2026-09-01 by having a branch
    deletion blocked, which is a pure false positive: deleting a remote ref
    cannot ship a migration.

    Returns (base_sha_or_None, is_delete_only).
    """
    try:
        data = sys.stdin.read()
    except Exception:
        return None, False
    lines = [l.split() for l in data.splitlines() if l.split()]
    refs = [p for p in lines if len(p) == 4]
    if refs and all(set(p[1]) == {'0'} for p in refs):
        return None, True
    for parts in refs:
        if set(parts[3]) != {'0'}:
            return parts[3], False
    return None, False


def main():
    base = None
    # Only ever assigned in pretooluse mode. It is initialised here because the
    # combined-commit check further down referenced it unguarded, which raised
    # UnboundLocalError in PREPUSH mode -- swallowed by the fail-open handler,
    # so the pre-push hook silently allowed every push it was added to catch.
    # Found 2026-09-01 by instrumenting the shell hook to prove git really was
    # invoking it, then reproducing with git's actual new-branch stdin. Two
    # bypass fixes landed within minutes of each other and the second disabled
    # the first; neither test would have caught it alone.
    cmd = ''
    if MODE == 'prepush':
        # git already decided a push is happening. There is no command text to
        # match and nothing to opt out of -- that is the entire point of this
        # entry point existing.
        base, delete_only = prepush_base()
        if delete_only:
            sys.exit(0)
    else:
        payload = json.load(sys.stdin)
        cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
        if not re.search(r'\bgit\s+push\b', cmd):
            sys.exit(0)

    repo = git(os.getcwd(), 'rev-parse', '--show-toplevel').strip()
    if not repo or not os.path.isdir(os.path.join(repo, 'sql')):
        sys.exit(0)

    # ── COMMIT-AND-PUSH IN ONE CALL: A REAL HOLE, FOUND BY FALLING INTO IT ──
    # This is a PreToolUse hook. It runs BEFORE a single character of the
    # command executes, so it sees the repo as it is NOW. A command shaped
    #
    #     git add sql/x.sql && git commit -m ... && git push
    #
    # is therefore invisible to every check below: at hook time the commit does
    # not exist, `origin/main..HEAD` contains no SQL, and the gate allows.
    #
    # THIS IS NOT HYPOTHETICAL. On 2026-09-01, hours after this file was made
    # fail-closed, a migration (sql/sd_subs_compliance_2026-09-01.sql) reached
    # origin/main through exactly this shape, in the same session that wrote
    # the fail-closed logic and had just verified it denying correctly on a
    # separate push. The gate was working; it was simply looking at a moment
    # before the thing it guards existed.
    #
    # The fix cannot be "inspect what is about to be committed" -- the hook has
    # no way to know what the command will stage. So it refuses only the narrow
    # case where the ambiguity is real: a combined commit+push while SQL is
    # uncommitted in the working tree or the index. An ordinary combined
    # commit+push that touches no SQL is unaffected, which matters -- a gate
    # that blocks every routine workflow gets switched off within a day.
    # PRETOOLUSE ONLY. In prepush mode git has already built the commit list,
    # so there is no "the commit does not exist yet" ambiguity to guard against
    # -- and cmd is empty there by construction.
    if MODE == 'pretooluse' and re.search(r'\bgit\s+commit\b', cmd):
        pending = [ln[3:].strip().replace('\\', '/')
                   for ln in git(repo, 'status', '--porcelain').splitlines() if ln.strip()]
        pending_sql = sorted(q for q in pending if q.startswith('sql/') and q.endswith('.sql'))
        if pending_sql:
            deny(chr(10).join([
                "Blocked: this command commits AND pushes SQL in one step, so the push gate",
                "cannot see what it is being asked to check.",
                "",
                "Uncommitted SQL in the working tree or index:",
                ] + ["  " + q for q in pending_sql] + [
                "",
                "This hook runs BEFORE the command does. At this moment the commit does not",
                "exist yet, so the outgoing-file list is empty and checks 2 and 3 would pass",
                "on a push that in fact ships these files. A migration reached origin/main",
                "through exactly this shape on 2026-09-01, hours after the gate was made",
                "fail-closed and verified denying correctly on a separate push.",
                "",
                "Run the commit and the push as TWO separate commands. The gate then sees",
                "the real commit and checks it.",
                "",
                "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
            ]))

    checker = os.path.join(repo, 'tools', 'sairn_load_state_check.py')
    if not os.path.isfile(checker):
        sys.exit(0)

    # ── CHECK 2: credential-writer guard on any changed sql/*.sql ──────────
    changed = outgoing_files(repo, base)
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

        # ── CHECK 3: SQL preflight, LIVE and FAIL-CLOSED ──────────────────
        # LIVE MODE ENABLED 2026-09-01 (Michael's call), replacing declared-only.
        # The file is now checked against a snapshot of what the DATABASE
        # actually has, so MISSING_TABLE becomes a fact rather than an
        # observation about the repo, and both it and MISSING_COLUMN block.
        #
        # AND IT FAILS CLOSED. This is the half that matters. The declared-only
        # version denied on exit 1 and allowed on EVERYTHING ELSE -- including
        # the tool refusing to run, and including there being no schema to check
        # against at all. Every one of those allowed the push in silence, which
        # is the exact could-not-tell-reported-as-a-pass shape that check 1 has
        # a whole paragraph warning about and that check 3 then reproduced.
        #
        # So: no snapshot, an unreadable snapshot, a snapshot with no tables, a
        # subprocess that will not start, or a timeout, ALL DENY. The tool's
        # --require-live gives that its own exit code (4) rather than leaving
        # this hook to infer it from prose.
        #
        # THE COST OF THIS IS REAL AND IS THE POINT: until db/schema_snapshot.json
        # exists, every push that touches sql/ is denied. Generating it is a
        # manual step (sql/schema_snapshot_query.sql in the Supabase editor) and
        # the deny message says so. A push that touches no SQL is unaffected.
        pf = os.path.join(repo, 'tools', 'sairn_sql_preflight.py')
        snapshot = (os.environ.get('SAIRN_SCHEMA_SNAPSHOT')
                    or os.path.join(repo, 'db', 'schema_snapshot.json'))
        if os.path.isfile(pf):
            try:
                p = subprocess.run(
                    [sys.executable, pf, '--gate', '--require-live', '--live', snapshot]
                    + [os.path.join(repo, q) for q in sql_changed],
                    capture_output=True, text=True, timeout=120, cwd=repo)
            except Exception as e:
                # Was `p = None` followed by a check that skipped silently. A
                # checker that cannot be run has not passed anything.
                deny(chr(10).join([
                    "Blocked: the SQL preflight could not be run, so this push is unchecked.",
                    "",
                    "  %s: %s" % (type(e).__name__, e),
                    "",
                    "Check 3 runs live and fails closed as of 2026-09-01. An unrunnable",
                    "checker used to allow the push silently; that is the failure mode this",
                    "gate exists to prevent, so it now denies instead.",
                    "",
                    "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
                ]))
            if p.returncode == 4:
                deny(chr(10).join([
                    "Blocked: no live schema snapshot, so this push's SQL cannot be checked.",
                    "",
                    p.stdout.strip(),
                    "",
                    "This is a DENY and not a warning on purpose. Until 2026-09-01 this check",
                    "ran against the repo's own CREATE TABLE statements and allowed anything",
                    "it could not answer, which meant a missing schema and a clean file were",
                    "indistinguishable from the outside.",
                    "",
                    "Point it somewhere else with SAIRN_SCHEMA_SNAPSHOT=<path> if the snapshot",
                    "lives outside the clone.",
                    "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
                ]))
            if p.returncode == 1:
                msg = [
                    "Blocked: this push contains SQL naming a table or column that the live",
                    "database does not have.",
                    "",
                    p.stdout.strip(),
                    "",
                    "A wrong column in an INSERT fails loudly and is survivable. A wrong",
                    "column in the WHERE of an UPDATE or DELETE does not fail -- it matches",
                    "nothing and reports success, and '0 rows' is indistinguishable from",
                    "'nothing needed changing'. That is why this blocks before the file can",
                    "be pasted into the editor rather than after.",
                    "",
                    "Checked against %s, which is a SNAPSHOT and is only as current as the" % snapshot,
                    "last time someone ran sql/schema_snapshot_query.sql. If the object really",
                    "does exist because a migration was applied after that, regenerate the",
                    "snapshot rather than overriding the gate.",
                    "",
                    "Full detail:  python tools/sairn_sql_preflight.py --live %s <file>" % snapshot,
                    "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
                ]
                deny(chr(10).join(msg))

    # ── CHECK 4: endpoint/engine seam ──────────────────────────────────────
    # Added 2026-09-01. SAIRNlaw's deadline engine grew a `service_methods`
    # input and api/legal-deadlines.js was never updated, so the field was
    # dropped on every live request for five days -- Florida answers five days
    # late on the shortest period in the engine. Both suites stayed green the
    # whole time because they call the engine directly and never traverse the
    # endpoint.
    #
    # Runs on any api/*.js change, not only on changed endpoints: editing an
    # ENGINE is how the seam breaks, and the endpoint that stops matching it is
    # a file the push never touched. Checking only changed files would have
    # missed the original incident exactly.
    api_changed = [q for q in changed if q.startswith('api/') and q.endswith('.js')]
    if api_changed:
        seam = os.path.join(repo, 'tools', 'sairn_seam_check.py')
        if os.path.isfile(seam):
            try:
                s = subprocess.run([sys.executable, seam],
                                   capture_output=True, text=True, timeout=90, cwd=repo)
            except Exception as e:
                deny(chr(10).join([
                    "Blocked: the endpoint/engine seam check could not be run, so this",
                    "push is unchecked.",
                    "",
                    "  %s: %s" % (type(e).__name__, e),
                    "",
                    "A checker that cannot be run has not passed anything.",
                    "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
                ]))
            if s.returncode == 1:
                deny(chr(10).join([
                    "Blocked: an endpoint does not forward every input its engine reads.",
                    "",
                    s.stdout.strip(),
                    "",
                    "This does not throw at run time. The field arrives undefined, the",
                    "engine takes its default branch, and the response looks entirely",
                    "reasonable -- which is how SAIRNlaw returned Florida deadlines five",
                    "days late for five days with both test suites green.",
                    "",
                    "Fix by forwarding the field, or -- if the engine supplies it itself or",
                    "the endpoint fills it from the database -- declare it in the ENGINE",
                    "file next to the contract it describes:",
                    "    // seam-check: server-supplied <field> [<field>...]",
                    "",
                    "Full detail:  python tools/sairn_seam_check.py",
                    "Override with SAIRN_SEED_GATE=off, and say so out loud if you do.",
                ]))
            if s.returncode == 2:
                # A seam this tool cannot parse is not a pass and does not
                # pretend to be, but blocking on it would make an unanalysable
                # shape unshippable -- same trade as check 1's could-not-tell.
                note = ("Seam check COULD NOT TELL for at least one endpoint/engine pair. "
                        "The push is allowed, but nothing was verified about that seam. "
                        "Run: python tools/sairn_seam_check.py")
                if MODE == 'prepush':
                    sys.stderr.write('\n' + note + '\n\n')
                else:
                    print(json.dumps({"hookSpecificOutput": {
                        "hookEventName": "PreToolUse", "additionalContext": note}}))

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

    if untold and MODE == 'prepush':
        # Same "could not tell is not a pass" rule, said where a pre-push caller
        # will actually see it. Allowed, but never silently.
        sys.stderr.write(
            "\nSeed-load gate COULD NOT TELL for: "
            + "; ".join("%s (%s)" % (a, why) for a, why in untold)
            + ".\nThe push is allowed because a missing licence key must not block a legitimate\n"
              "push, but nothing was verified about that app's live rules.\n\n")
        sys.exit(0)

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
        if '--pre-push' in sys.argv:
            MODE = 'prepush'
        if os.environ.get('SAIRN_SEED_GATE', '').lower() == 'off':
            sys.exit(0)
        main()
    except Exception:
        # Fail open -- never let a hook bug block a legitimate command. Exit 0
        # means "allow" in BOTH modes, so this is the same promise either way:
        # a gate that crashes closed gets disabled, and then protects nothing.
        sys.exit(0)
