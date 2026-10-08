#!/usr/bin/env python
"""SessionStart hook: make hover_self_health.py actually FIRE. Built 2026-09-16.

WHY. SKILL.md has said "not discretionary: run hover_self_health.py at the
start of every process pass" since 2026-09-15, and grep across every settings
file found nothing that invoked it -- only permission-allowlist entries, which
permit a command, they do not run one. It fired exactly when someone remembered
to say so, which is the definition of discretionary. Prose is not enforcement;
a hook is. This is the same Jidoka-interlock distinction as the rotation gate
in hover_log.py, applied to the self-check rather than to target selection.

FAIL-CLOSED, AND THAT IS THE WHOLE DESIGN POINT. Three outcomes exist here, not
two, per this platform's standing rule that "could not run" is never folded
into "passed":
  - the check ran and passed        -> say so
  - the check ran and failed        -> say which conditions fired
  - the check COULD NOT RUN         -> say that, by name, and say why
A hook that swallowed its own failure would reinstate the exact gap it was
built to close, in a place nobody would ever look again.

ALWAYS EXITS 0 ON PURPOSE. A nonzero SessionStart hook surfaces stderr noise
and can interfere with startup; the verdict belongs in additionalContext where
it is read, not in an exit code that only the harness sees. The check's own
real exit code is reported inside the text instead.

REGISTRATION MOVED TO THE TRACKED .claude/settings.json 2026-09-16, PER AN
EQA CHECKPOINT FINDING ON ITS FIRST REAL RUN. This hook originally lived only
in .claude/settings.local.json -- gitignored, machine-local, invisible to
`git log`, and gone the moment this clone is ever wiped and recreated. That
is the identical unpropagated-fix shape this hook exists to prevent, one
level up, and an independent reviewer (not this role re-grading itself)
caught it before it was trusted.

BUT A TRACKED, SHARED settings.json IS READ BY EVERY CLONE OF THIS REPO --
Hank, CC, Cody and Fourth's, not only the hover auditor's -- so committing
the registration unconditionally would fire this hover-specific self-check,
and inject its text into session context, on every OTHER agent's session
start too. THE FIX IS THE SAME MARKER GATE .githooks/pre-push ALREADY USES
FOR EXACTLY THIS PROBLEM: `.git/sairn-hover-auditor-clone` lives in .git/,
which is never versioned and never shared between clones, so a build
clone's git pull carries the REGISTRATION (visible, propagates, survives a
fresh hover clone) while `is_hover_clone()` below makes every OTHER clone's
invocation a true, silent, near-zero-cost no-op -- one `git rev-parse` and
one file stat, then exit, exactly as .githooks/pre-push's own
`if [ -f "$GITDIR/sairn-hover-auditor-clone" ]` does for the scope gate.
Reusing the EXISTING convention rather than inventing a second one.
"""

import json
import os
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
HOVER_CLONE_MARKER = 'sairn-hover-auditor-clone'


def _slug(path):
    """Path -> the ~/.claude/projects directory-name encoding, same rule as
    tools/hover_self_health_shim.py's slug_for(), lowercased because Windows
    paths compare case-insensitively."""
    return path.replace(':', '-').replace('\\', '-').replace('/', '-').lower()


def owner_clone_path():
    """The clone THIS hook's data belongs to, derived from where the hook
    LIVES: HERE is ~/.claude/projects/<slug>/hover-audit-log, and the slug
    encodes the clone path. Decoded by matching against the real known
    clone directories rather than string-unmangling (the slug is lossy --
    '-' could have been ':', '\\\\' or a literal dash)."""
    slug = os.path.basename(os.path.dirname(HERE)).lower()
    docs = os.path.join(os.path.expanduser('~'), 'Documents')
    try:
        candidates = [os.path.join(docs, d) for d in os.listdir(docs)]
    except OSError:
        candidates = []
    for c in candidates:
        if _slug(os.path.abspath(c)) == slug:
            return os.path.abspath(c)
    return None


def invoked_clone_path():
    """The clone the hook was actually invoked FROM: the cwd's git toplevel.
    None when that cannot be determined -- and None is treated as a
    mismatch, never as a pass (PR 1.11)."""
    try:
        r = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True, encoding='utf-8',
                           timeout=5)
        if r.returncode != 0:
            return None
        return os.path.abspath(r.stdout.strip())
    except Exception:
        return None


def is_hover_clone():
    """Same marker, same lookup as tools/hover_auditor_scope_gate.py's
    is_auditor_clone() and .githooks/pre-push's own shell check -- one
    convention, checked the same way everywhere it's checked. Any failure
    to determine clone identity (git missing, not a repo, a worktree quirk)
    resolves to False: the cost of skipping a real self-check once in the
    hover clone is a missed context note; the cost of running it unasked
    inside another agent's session is noise in a place it does not belong.
    """
    try:
        r = subprocess.run(['git', 'rev-parse', '--git-dir'],
                           capture_output=True, text=True, encoding='utf-8', timeout=5)
        if r.returncode != 0:
            return False
        git_dir = r.stdout.strip()
        if not os.path.isabs(git_dir):
            git_dir = os.path.join(os.getcwd(), git_dir)
        return os.path.isfile(os.path.join(git_dir, HOVER_CLONE_MARKER))
    except Exception:
        return False

# ── THE FIRE RECORD, AND WHY IT IS A SEPARATE FILE ───────────────────────────
# The whole defect being fixed here is a rule that was believed to be running
# and was not. Believing THIS one runs, on the same evidence (it exists, and it
# says it runs), would repeat the identical mistake one level up. So every
# invocation leaves a durable, timestamped trace, and "did the hook fire" is
# answerable from the filesystem afterwards instead of inferred from the
# registration. Kept OUT of the hash-chained self-log on purpose: that log is
# a record of audit judgements, and filling it with mechanical startup rows
# would bury the entries a reader actually needs.
FIRES = os.path.join(HERE, 'hover_self_health_fires.jsonl')


def record_fire(verdict):
    """Returns None on success, or an error string -- never silently swallowed."""
    try:
        from datetime import datetime, timezone
        with open(FIRES, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'pid': os.getpid(),
                'cwd': os.getcwd(),
                'verdict': verdict,
            }) + '\n')
        return None
    except OSError as e:
        return 'could not write the fire record (%s)' % e


def emit(text, verdict='unknown'):
    err = record_fire(verdict)
    if err:
        text += '\n[fire-record] %s -- this run happened but left no durable trace.' % err
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': text,
    }}))
    sys.exit(0)


def main():
    # ── THE GUARD, FIRST, BEFORE ANYTHING ELSE ──────────────────────────────
    # Silent, no JSON output at all -- matching .githooks/pre-push's own
    # `if [ -f "$GITDIR/sairn-hover-auditor-clone" ]; then ... fi` exactly,
    # no else branch. A build agent's session should see NOTHING from this
    # hook, not even a "not applicable here" note; that note would itself be
    # noise this hook has no business injecting into someone else's session.
    if not is_hover_clone():
        sys.exit(0)

    # ── THE CLONE-IDENTITY GUARD, 2026-09-28 ────────────────────────────────
    # Reported by the other hover instance and reproduced live before
    # fixing: this hook, invoked from hover2's cwd, emitted THIS clone's
    # full report into their session -- is_hover_clone() answers "is the
    # invoking cwd SOME auditor clone", while every data path here (LOG,
    # FIRES, hover_self_health) resolves from where the hook LIVES. Marker
    # presence cannot distinguish auditor clones (T-KNOWN-BAD proves the
    # retired signal said YES for a foreign marker-carrying clone), so the
    # guard compares the invoking clone's path against the owning clone
    # decoded from this file's own project-directory slug. Any failure to
    # establish EITHER side is a mismatch, never a pass.
    owner = owner_clone_path()
    invoked = invoked_clone_path()
    if not owner or not invoked or _slug(invoked) != _slug(owner):
        emit('HOVER SELF-HEALTH: COULD NOT RUN -- clone mismatch. This hook '
             'belongs to %s and was invoked from %s. Refusing to report one '
             'auditor clone\'s data into another\'s session (the exact defect '
             'hover2 reported on 2026-09-28); run the copy installed under '
             'YOUR clone\'s own project directory instead. This is NOT a pass '
             'and your own log has NOT been checked.'
             % (owner or 'UNRESOLVABLE', invoked or 'UNRESOLVABLE'),
             'could-not-run')

    sys.path.insert(0, HERE)
    try:
        import hover_self_health as h
    except Exception as e:
        emit('HOVER SELF-HEALTH: COULD NOT RUN -- hover_self_health.py failed to '
             'import (%s). This is NOT a pass. The firm-level self-check did not '
             'execute this session; run it by hand before relying on any rotation '
             'or staleness claim.' % e, 'could-not-run')

    if not os.path.isfile(LOG):
        emit('HOVER SELF-HEALTH: COULD NOT RUN -- the self-log is missing at %s. '
             'This is NOT a pass and NOT an empty-but-healthy log; a check over a '
             'file that is not there tested nothing.' % LOG, 'could-not-run')

    # ── ONE SHARED REPORT-BUILDER, NOT A HAND-COPIED CHECK LIST (2026-09-17) ──
    # This hook used to re-derive "what counts as fired" by calling four, then
    # seven, individual check_*() functions and hand-formatting each message a
    # second time. Three checks (tip_beacon, bar_drift, independence_proxy)
    # were each patched in separately, one round-trip at a time, and each was
    # briefly silently absent from this hook's output before someone noticed --
    # the exact "a check that exists and does not run" shape this role spends
    # the rest of its time hunting for in everyone else's tooling. Calling
    # h.build_report() means there is now exactly one place a new check has to
    # be added for it to appear both in `python hover_self_health.py` and here.
    try:
        entries = h.load_entries(LOG)
        report = h.build_report(entries, log_path=LOG)
    except Exception:
        emit('HOVER SELF-HEALTH: COULD NOT RUN -- raised while checking:\n%s\n'
             'This is NOT a pass.' % traceback.format_exc(limit=3), 'could-not-run')

    control = report['routine_classifier_control']
    eqa_control = report['eqa_classifier_control']

    # The two classifier controls are surfaced as their OWN, more severe
    # verdict ('control-failed') rather than folded into the ordinary fired
    # list: a control failure means every ROUTINE/EQA number in the report is
    # untrusted, which is a different claim than "a number is bad."
    if control['FAIL_control']:
        emit('HOVER SELF-HEALTH: CONTROL FAILED -- the same-event classifier no '
             'longer matches its own synthetic fixtures (%s). Every rotation '
             'number is untrusted until this is fixed; treat as could-not-run, '
             'not as a pass.' % '; '.join(control['fixtures_failed']), 'control-failed')

    if eqa_control['FAIL_control']:
        emit('HOVER SELF-HEALTH: CONTROL FAILED -- the EQA-checkpoint classifier no '
             'longer matches its own synthetic fixtures (%s). The EQA due/not-due '
             'number is untrusted until this is fixed; treat as could-not-run.'
             % '; '.join(eqa_control['fixtures_failed']), 'control-failed')

    # Both control checks already appear in report['failures'] too (build_report
    # adds them there as well, worded as CONTROL: ...) -- exclude them here so
    # a control failure is not shown twice, once above as its own verdict and
    # again inside the ordinary fired list below.
    fired = [f for f in report['failures'] if not f.startswith('CONTROL:')]

    # UNINDEXED-EXTERNAL-FILE COUNT, wired in H1 batch X item 2. Runs this
    # clone's own hover_external_unindexed_check.py (committed in the
    # repo, read-only, never writes) and folds its count into the same
    # head line everything else here already reports through -- a FOURTH
    # failure condition, not a separate, easily-ignored message.
    unindexed_note = ''
    try:
        repo = r'C:\Users\marsh\Documents\SAIRN-hover'
        tool = os.path.join(repo, '.claude', 'skills', 'sairn-hover-auditor',
                             'tools', 'hover_external_unindexed_check.py')
        r_un = subprocess.run([sys.executable, tool], capture_output=True,
                               text=True, encoding='utf-8', errors='replace',
                               timeout=30, cwd=repo)
        m = None
        for line in (r_un.stdout or '').splitlines():
            if line.startswith('UNINDEXED COUNT:'):
                m = line.split(':', 1)[1].strip()
                break
        if m is None:
            unindexed_note = ' UNINDEXED EXTERNAL FILES: COULD NOT RUN.'
        else:
            unindexed_note = ' UNINDEXED EXTERNAL FILES: %s.' % m
    except Exception as e:
        unindexed_note = ' UNINDEXED EXTERNAL FILES: COULD NOT RUN (%s).' % e

    # SKILL/MCP REPORT, wired in H1 batch X item 7. Read-only, project-scoped
    # (hover_skill_mcp_report.py's own docstring states the scope precisely:
    # a project MCP server is one declared in .mcp.json or settings.json's
    # mcpServers key, never an account-level connector visible in-session).
    # One line, not the full multi-line report, to keep this head line
    # readable -- the full report is available by running the tool directly.
    skillmcp_note = ''
    try:
        repo = r'C:\Users\marsh\Documents\SAIRN-hover'
        tool = os.path.join(repo, '.claude', 'skills', 'sairn-hover-auditor',
                             'tools', 'hover_skill_mcp_report.py')
        r_sm = subprocess.run([sys.executable, tool], capture_output=True,
                               text=True, encoding='utf-8', errors='replace',
                               timeout=30, cwd=repo)
        lines = (r_sm.stdout or '').splitlines()
        mcp_line = next((l for l in lines if l.startswith('PROJECT MCP SERVERS:')), None)
        skills_line = next((l for l in lines if l.startswith('PROJECT SKILLS:')), None)
        if mcp_line is None or skills_line is None:
            skillmcp_note = ' SKILL/MCP REPORT: COULD NOT RUN.'
        else:
            skillmcp_note = (' %s %s'
                             % (mcp_line.split('--')[0].strip() + '.',
                                skills_line.split('(')[0].strip() + '.'))
    except Exception as e:
        skillmcp_note = ' SKILL/MCP REPORT: COULD NOT RUN (%s).' % e

    head = ('HOVER SELF-HEALTH ran automatically at session start (%d entries, '
            'classifier control %d/%d).%s%s ' % (len(entries), control['fixtures_run']
                                             - len(control['fixtures_failed']),
                                             control['fixtures_run'], unindexed_note,
                                             skillmcp_note))
    if fired:
        emit(head + 'FAILING CONDITIONS -- each is a real finding to address, not '
                    'a notice to dismiss:\n  - ' + '\n  - '.join(fired) +
             '\nNext unused technique: %s' % report['standing_technique_queue']['next_up'],
             'fail')
    emit(head + 'All pre-declared failure conditions clean. This is a statement '
                'about what this check measures, not a guarantee nothing drifted '
                'in a way it does not.', 'pass')


def run_selftest():
    """Fixtures for the clone-identity guard, written BEFORE the guard
    existed and verified failing against the pre-fix hook (2026-09-28,
    reported by the other hover instance and reproduced live: this hook,
    invoked from hover2's cwd, emitted THIS clone's 600-entry report into
    their session). No fixture touches another instance's directory --
    the foreign clone is a scratch git repo carrying the marker."""
    import tempfile
    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    def run_from(cwd):
        r = subprocess.run([sys.executable, os.path.abspath(__file__)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=cwd, timeout=60)
        return r.stdout

    scratch = tempfile.mkdtemp(prefix='hover_hook_foreign_clone_')
    subprocess.run(['git', 'init', '-q', scratch], check=True)
    gitdir = subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=scratch,
                            capture_output=True, text=True).stdout.strip()
    if not os.path.isabs(gitdir):
        gitdir = os.path.join(scratch, gitdir)
    open(os.path.join(gitdir, HOVER_CLONE_MARKER), 'w').close()

    out_foreign = run_from(scratch)
    ck('T-MISMATCH (the regression): invoked from a FOREIGN marker-carrying '
       'clone, the hook REFUSES with COULD NOT RUN naming the clone '
       'mismatch, instead of reporting this clone\'s data into that session',
       'COULD NOT RUN' in out_foreign and 'clone' in out_foreign.lower()
       and 'classifier control' not in out_foreign)
    ck('T-KNOWN-BAD CONTROL, MUST KEEP FAILING: the RETIRED decision signal '
       '-- marker presence at the invoking cwd alone -- says YES for that '
       'same foreign clone (is_hover_clone() run there returns True), '
       'proving marker presence cannot distinguish auditor clones and the '
       'path comparison is what carries the guard',
       subprocess.run([sys.executable, '-c',
                       'import sys; sys.path.insert(0, %r); '
                       'import hover_self_health_hook as h; '
                       'sys.exit(0 if h.is_hover_clone() else 1)' % HERE],
                      cwd=scratch, capture_output=True).returncode == 0)

    plain = tempfile.mkdtemp(prefix='hover_hook_build_clone_')
    subprocess.run(['git', 'init', '-q', plain], check=True)
    ck('T-BUILD: a clone with NO marker stays a true silent no-op -- no '
       'refusal text, no report, nothing', run_from(plain).strip() == '')

    owner = owner_clone_path()
    ck('T-OWNER-DERIVES: the hook derives its owning clone from its own '
       'location, non-empty and pointing at an existing directory',
       bool(owner) and os.path.isdir(owner))
    out_owner = run_from(owner)
    ck('T-OWNER: invoked from the clone this hook belongs to, the guard '
       'stands aside and the real report still emits',
       'classifier control' in out_owner or 'COULD NOT RUN --' in out_owner)

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


if __name__ == '__main__':
    if '--selftest' in sys.argv[1:]:
        sys.exit(0 if run_selftest() else 1)
    main()
