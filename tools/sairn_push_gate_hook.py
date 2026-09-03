"""Pre-push checks that must not depend on memory. FIVE of them as of 2026-09-01.

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
  5. REACHABILITY (added 2026-09-01) -- REPORT ONLY, never blocks. Reports
     shipped features a customer cannot reach: an id squatted by an empty
     display:none stub, a control injected into a hidden container, an entry
     point nothing wires. stonedesk.html carries 9 standing findings, all
     confirmed against the RENDERED DOM rather than inferred, so switching this
     to a deny today would refuse every StoneDesk push. Promote it once that
     file is clean.

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

WHAT "THE COMMITS BEING PUSHED" MEANS -- CORRECTED 2026-09-03
------------------------------------------------------------
It used to mean `origin/main..HEAD`, unconditionally, in both modes. That is
right only when the push sends HEAD, and two failures followed from it:

  * `git push origin <sha>:main` was checked as though it pushed HEAD. On
    2026-09-01 an engine-only commit touching zero seed files was DENIED for 13
    New Hampshire rules living in a LATER seed commit that the push was not
    sending. The gate refused the deploy-then-load-then-push ordering that this
    file's own documentation prescribes.
  * check 1 then read sql/*.json off DISK, so even a correctly-scoped push was
    compared against whatever happened to be checked out.

Both are fixed by asking a narrower question: which commit does this push
actually send, and what did the seed files look like AT THAT COMMIT. prepush
mode reads the local sha git supplies on stdin; pretooluse mode parses the
refspec out of the command text (see pushed_tip). Check 1 exports sql/ at that
tip (see export_sql_at) and points the checker at it with --sql-dir. If the
export fails, the working tree is used and the deny message SAYS which reading
it got -- the old behaviour is still available, it is just no longer silent.

THE OVERRIDE IS REACHABLE NOW, AND WAS NOT BEFORE
-------------------------------------------------
`SAIRN_SEED_GATE=off` was read from os.environ only. That works in prepush mode
(git runs the hook as a child of the shell) and CANNOT work in pretooluse mode:
the hook runs inside Claude Code's process and inherits Claude Code's
environment, not the environment of the command it is inspecting. An inline
`SAIRN_SEED_GATE=off git push ...` set the variable in a child shell the hook
never saw, and the push was denied identically -- while eight deny messages
told the reader to do exactly that. Pretooluse mode now reads the assignment
out of the command text, ignoring quoted mentions so that a commit message
quoting the string cannot disable the gate.
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


def pushed_tip(repo, cmd):
    """The LOCAL commit a pretooluse-mode push would actually send.

    ADDED 2026-09-03, because every check below used to diff against HEAD no
    matter what the command said. `git push origin <sha>:main` therefore got
    checked as if it were pushing HEAD, and on 2026-09-01 an engine-only commit
    was DENIED naming 13 New Hampshire rules that lived in a LATER seed commit
    sitting in HEAD -- a commit the push was not sending. The gate was refusing
    the exact load-then-push ordering its own documentation prescribes.

    Parsed from the command text because that is the only description of the
    push a PreToolUse hook gets. Handles the shapes that actually occur:

        git push                      -> HEAD
        git push origin main          -> main
        git push origin HEAD:main     -> HEAD
        git push origin abc123:main   -> abc123
        git push -u origin feature    -> feature
        git push --dry-run origin x:main -> x

    Anything unparseable falls back to HEAD, which is what this always did --
    so a refspec shape not handled here is no worse than before, never worse.
    """
    tail = re.split(r'\bgit\s+push\b', cmd, maxsplit=1)
    if len(tail) < 2:
        return 'HEAD'
    words = []
    for w in tail[1].split():
        if w in (';', '&&', '||', '|'):
            break
        if w.startswith('-'):
            # --dry-run, -u, --force, --set-upstream ... none name a ref.
            continue
        words.append(w)
    if not words:
        return 'HEAD'
    # First word after the flags is the remote; the second, if any, is the
    # refspec. `git push` with a lone argument is a remote, not a ref.
    spec = words[1] if len(words) > 1 else None
    if not spec:
        return 'HEAD'
    local = spec.split(':', 1)[0].lstrip('+')
    if not local:
        # `git push origin :branch` DELETES a remote branch and ships nothing.
        return None
    if not git(repo, 'rev-parse', '--verify', '--quiet', local + '^{commit}').strip():
        return 'HEAD'
    return local


def outgoing_files(repo, base=None, tip='HEAD'):
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

    `tip` is the LOCAL end of the range and was hardcoded to HEAD until
    2026-09-03. See pushed_tip() for what that cost.
    """
    refs = ([base] if base else []) + ['@{u}', 'origin/main']
    for ref in refs:
        out = git(repo, 'log', ref + '..' + tip, '--name-only', '--pretty=format:')
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

    Returns (base_sha_or_None, is_delete_only, local_sha_or_None).

    The LOCAL sha was added 2026-09-03. git states outright which commit is
    being sent, so prepush mode never has to guess it from HEAD -- and pushing
    a ref that is not HEAD is precisely the case the gate got wrong.
    """
    try:
        data = sys.stdin.read()
    except Exception:
        return None, False, None
    lines = [l.split() for l in data.splitlines() if l.split()]
    refs = [p for p in lines if len(p) == 4]
    if refs and all(set(p[1]) == {'0'} for p in refs):
        return None, True, None
    local = next((p[1] for p in refs if set(p[1]) != {'0'}), None)
    for parts in refs:
        if set(parts[3]) != {'0'}:
            return parts[3], False, local
    return None, False, local


# The override line every deny message ends with. It is a single constant
# because it was WRONG in eight places at once between 2026-09-01 and
# 2026-09-03: it told the reader to set an environment variable the PreToolUse
# hook could not see, so the documented escape hatch did nothing and eight
# copies of the instruction all had to be believed to find that out.
OVERRIDE_HINT = ("Override by putting SAIRN_SEED_GATE=off at the FRONT of the push command "
                 "itself (SAIRN_SEED_GATE=off git push ...), not in a separate export. "
                 "Say so out loud if you do.")

OVERRIDE_RE = re.compile(
    r"""(?:^|[;&|\n]|\bexport\s+)\s*SAIRN_SEED_GATE\s*=\s*(['"]?)off\1(?=\s|$|[;&|])""",
    re.IGNORECASE)


def override_in_command(cmd):
    """Is `SAIRN_SEED_GATE=off` set as a real shell assignment in this command?

    WHY THIS EXISTS -- found 2026-09-01, fixed 2026-09-03. The override was
    read from os.environ only. In PREPUSH mode that is correct: git runs the
    hook as a child of the shell, so `SAIRN_SEED_GATE=off git push` reaches it.
    In PRETOOLUSE mode it is unreachable -- the hook runs inside Claude Code's
    own process and inherits Claude Code's environment, not the environment of
    the command it is inspecting. The inline prefix sets the variable in a child
    shell the hook never sees, so the documented escape hatch did nothing and
    the push was denied identically. Every deny message in this file told the
    reader to do something that could not work.

    So the assignment is read out of the command TEXT, which is the same payload
    already parsed for the push refspec.

    QUOTED MENTIONS DO NOT COUNT, and that matters here more than it usually
    would: this repo's commit messages and this very file quote the string
    "SAIRN_SEED_GATE=off" in prose. `git commit -m "... SAIRN_SEED_GATE=off"
    && git push` must NOT disable the gate. A match is honoured only when it is
    anchored at a command boundary AND falls outside every quoted span.
    """
    for m in OVERRIDE_RE.finditer(cmd):
        head = cmd[:m.start()]
        # An odd count of either quote means the match sits inside a string.
        # Escaped quotes are removed first so \" does not open a span.
        plain = head.replace('\\"', '').replace("\\'", '')
        if plain.count('"') % 2 == 0 and plain.count("'") % 2 == 0:
            return True
    return False


def _nl(b):
    """Normalise line endings before comparing two versions of a text file."""
    return b.replace(b'\r\n', b'\n')


def export_sql_at(repo, tip):
    """Write sql/ as it exists at `tip` to a temp dir. Returns (dir, note).

    ADDED 2026-09-03 alongside pushed_tip(). Deriving the seed FILE LIST from
    the pushed range fixed which apps get checked; this fixes what their content
    is compared against. Both were the same bug seen from two ends: the gate
    asked "does live match the repo" when the only question that matters at push
    time is "does live match what this push will SHIP".

    Returns (None, note) on any failure. The caller then falls back to the
    working tree, which is what this always did -- an export that cannot be made
    must not turn a working gate into a denied push.

    `note` is non-empty only when the exported seeds DIFFER from the working
    tree, because that is the one case where a reader who assumes the old
    behaviour would misread identical output. Reconciling the two readings
    rather than silently replacing one with the other.
    """
    import atexit
    import shutil
    import tempfile
    try:
        out = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', tip, 'sql/'],
                             capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return None, 'sql/ could not be listed at %s' % tip
        names = [n.strip() for n in out.stdout.splitlines()
                 if n.strip().endswith('.json')]
        if not names:
            return None, ''
        dest = tempfile.mkdtemp(prefix='sairn-seed-')
        # atexit rather than a try/finally: every deny path below calls
        # sys.exit() from inside the caller, so a finally here would never run
        # on the branches that matter and the dirs would accumulate one per
        # blocked push.
        atexit.register(shutil.rmtree, dest, True)
        differs = []
        for name in names:
            blob = subprocess.run(['git', '-C', repo, 'show', '%s:%s' % (tip, name)],
                                  capture_output=True, timeout=20)
            if blob.returncode != 0:
                return None, 'could not read %s at %s' % (name, tip)
            data = blob.stdout
            with open(os.path.join(dest, os.path.basename(name)), 'wb') as f:
                f.write(data)
            disk = os.path.join(repo, name)
            if os.path.isfile(disk):
                with open(disk, 'rb') as f:
                    # LINE ENDINGS ARE NOT A CONTENT DIFFERENCE, and comparing
                    # raw bytes said they were. `git show` hands back the blob
                    # with LF; core.autocrlf leaves CRLF in the working tree, so
                    # the first version of this reported ALL 72 seed files as
                    # diverged on a clean checkout -- caught by this change's own
                    # probe before it shipped. A note that fires on every push is
                    # a note nobody reads, and it would have buried the real
                    # divergence it exists to surface. Same false-alarm class as
                    # the skill-store mirror diff and the deploy-drift hook.
                    if _nl(f.read()) != _nl(data):
                        differs.append(os.path.basename(name))
            else:
                differs.append(os.path.basename(name) + ' (absent from the working tree)')
        note = ''
        if differs:
            shown = ', '.join(differs[:8])
            if len(differs) > 8:
                shown += ' and %d more' % (len(differs) - 8)
            note = ("Seeds were read from the PUSHED commit %s, which differs from the working "
                    "tree for: %s. The working tree is not what gets deployed, so the pushed "
                    "content is the honest comparison -- but the loader you run reads the "
                    "WORKING TREE, so loading and then pushing these will not agree."
                    % (tip, shown))
        return dest, note
    except Exception as e:
        return None, '%s: %s' % (type(e).__name__, e)


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
    tip = 'HEAD'
    if MODE == 'prepush':
        # git already decided a push is happening. There is no command text to
        # match and nothing to opt out of -- that is the entire point of this
        # entry point existing.
        base, delete_only, local = prepush_base()
        if delete_only:
            sys.exit(0)
    else:
        payload = json.load(sys.stdin)
        cmd = (payload.get('tool_input', {}) or {}).get('command', '') or ''
        if not re.search(r'\bgit\s+push\b', cmd):
            sys.exit(0)
        # The override, read where it is actually reachable from a Bash call.
        # Checked BEFORE any work so an override costs nothing and behaves
        # exactly like the env var does in prepush mode.
        if override_in_command(cmd):
            sys.exit(0)
        local = None

    repo = git(os.getcwd(), 'rev-parse', '--show-toplevel').strip()
    if not repo or not os.path.isdir(os.path.join(repo, 'sql')):
        sys.exit(0)

    if MODE == 'prepush':
        tip = local or 'HEAD'
    else:
        tip = pushed_tip(repo, cmd)
        if tip is None:
            # `git push origin :branch` -- a deletion, which ships nothing.
            # Same exemption prepush mode already had for an all-zero local sha.
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
                OVERRIDE_HINT,
            ]))

    checker = os.path.join(repo, 'tools', 'sairn_load_state_check.py')
    if not os.path.isfile(checker):
        sys.exit(0)

    # ── CHECK 2: credential-writer guard on any changed sql/*.sql ──────────
    changed = outgoing_files(repo, base, tip)
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
                    OVERRIDE_HINT,
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
                    OVERRIDE_HINT,
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
                    OVERRIDE_HINT,
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
                    OVERRIDE_HINT,
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
                    OVERRIDE_HINT,
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
                    OVERRIDE_HINT,
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

    # ── CHECK 5: reachability -- BLOCKING as of 2026-09-02 ─────────────────
    # Added 2026-09-01. Three complete, working, AI-backed StoneDesk features
    # were unreachable by a customer on 2026-08-30: each injected its only
    # trigger into an empty display:none placeholder. Nothing was broken and
    # there was simply no way in.
    #
    # IT SHIPPED REPORT-ONLY ON PURPOSE, because stonedesk.html carried 9 real
    # standing findings and a gate switched on before its findings are cleared
    # is a gate someone disables within the hour. Those are now cleared:
    # 4 dead exports removed, the Field Quote modal retired in favour of the
    # page, its entry points wired, and 2 stub collisions moved to
    # tools/reachability_exemptions.json with written justifications. The
    # checker exits 0 on stonedesk.html, so this is now a deny.
    #
    # THE EXEMPTION FILE IS WHAT MAKES BLOCKING SURVIVABLE. Two of the nine were
    # the checker being WRONG -- sairn-voice-btn's stub is the thing preventing a
    # duplicate mic button, and sairn-lock-overlay no longer short-circuits
    # anything. Without a way to record that, promoting this would have meant
    # refusing correct code forever. An exemption is a claim the checker is
    # wrong; a real-but-unfixed finding belongs in SAIRN-BACKLOG.md, and stale
    # entries are reported rather than left to accumulate.
    #
    # It still only runs on a push that CHANGES HTML, so an ordinary push costs
    # nothing.
    html_changed = [q for q in changed if q.endswith('.html')]
    if html_changed:
        reach = os.path.join(repo, 'tools', 'sairn_reachability_check.py')
        if os.path.isfile(reach):
            try:
                rr = subprocess.run([sys.executable, reach] + html_changed,
                                    capture_output=True, text=True, timeout=120, cwd=repo)
                if rr.returncode == 1:
                    deny(chr(10).join([
                        "Blocked: this push touches HTML that ships an unreachable feature.",
                        "",
                        rr.stdout.strip(),
                        "",
                        "Every finding here is a feature a customer cannot get to. Three such",
                        "features shipped in StoneDesk and nobody noticed, because nothing was",
                        "broken -- there was simply no way in, and that is invisible to every",
                        "other check in this file.",
                        "",
                        "Settle an R3 against the REAL page rather than by grepping: these names",
                        "all appear in the source, which is why a grep cannot answer it. Use",
                        "tools/sairn_dom_snapshot.js then",
                        "  python tools/sairn_reachability_check.py --live <snapshot.json> <file>",
                        "",
                        "If the checker is WRONG about a finding, add it to",
                        "tools/reachability_exemptions.json with a reason a reader can check",
                        "against the source. If the finding is REAL and you are not fixing it now,",
                        "it belongs in SAIRN-BACKLOG.md -- the exemption file is for the checker",
                        "being wrong, not for work being deferred.",
                        "",
                        OVERRIDE_HINT,
                    ]))
                if rr.returncode == 2:
                    # The checker itself could not run -- a broken exemption file,
                    # or --require-live with no snapshot. Same standard as check 3:
                    # a checker that cannot answer has not passed anything.
                    deny(chr(10).join([
                        "Blocked: the reachability check could not complete.",
                        "",
                        rr.stdout.strip(),
                        "",
                        OVERRIDE_HINT,
                    ]))
            except Exception as e:
                deny(chr(10).join([
                    "Blocked: the reachability check could not be run, so this push is unchecked.",
                    "",
                    "  %s: %s" % (type(e).__name__, e),
                    "",
                    "This check became blocking on 2026-09-02. An unrunnable checker used to be",
                    "ignored here; that is the failure mode the whole gate exists to prevent.",
                    "",
                    OVERRIDE_HINT,
                ]))

    # ── CHECK 1: seed load state ──────────────────────────────
    apps = []
    for path in changed:
        for pattern, app in SEED_PATTERNS:
            if pattern.match(path) and app not in apps:
                apps.append(app)
    if not apps:
        sys.exit(0)

    # ── COMPARE LIVE AGAINST THE PUSHED COMMIT, NOT THE WORKING TREE ────────
    # Added 2026-09-03. The checker reads sql/*.json off disk, so the drift it
    # reported described whatever was checked out rather than what the push
    # would ship. Export sql/ at the tip instead. If the export fails for any
    # reason the working tree is used, which is exactly the old behaviour --
    # degraded, never worse, and said out loud below when the two differ.
    seed_dir, seed_note = export_sql_at(repo, tip)

    drifted, untold = [], []
    for app in apps:
        env_name, default_key = APP_KEYS[app]
        key = os.environ.get(env_name) or default_key
        try:
            r = subprocess.run(
                [sys.executable, checker, '--app', app, '--key', key]
                + (['--sql-dir', seed_dir] if seed_dir else []),
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
        ]
        lines.append("Seeds compared as of the pushed commit %s, not the working tree." % tip
                     if seed_dir else
                     "Seeds compared from the WORKING TREE -- the pushed commit could not be read"
                     + ((" (%s)" % seed_note) if seed_note else "")
                     + ". That is the pre-2026-09-03 behaviour and can name rules this push does"
                       " not contain; check the range before trusting the list above.")
        if seed_dir and seed_note:
            lines += ["", seed_note]
        lines += [
            "",
            "If the drift is deliberate and unrelated to this push, " + OVERRIDE_HINT[0].lower() + OVERRIDE_HINT[1:],
            "An override nobody mentions is how this gets hollowed out.",
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
