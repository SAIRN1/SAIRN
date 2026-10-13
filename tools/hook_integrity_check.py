r"""A SILENTLY EDITED HOOK IS TRUSTED EXACTLY LIKE A CORRECT ONE.

    python tools/hook_integrity_check.py
    python tools/hook_integrity_check.py --json
    python tools/hook_integrity_check.py --regenerate   # names every change
    python tools/hook_integrity_check.py --repo <path>  # e.g. a fresh clone

REPORT ONLY. Exit 0 clean, 1 drift, 2 COULD NOT RUN. It writes nothing except
under `--regenerate`, which is an explicit, separate invocation.

── WHY, AND IT IS A GAP RATHER THAN AN INCIDENT ────────────────────────────
Every enforcement control on this platform is a hook or a tool a hook invokes.
They are git-tracked, and `core.hooksPath` is set, so a hook edit shows up in a
diff **if anybody looks at the diff**. NOTHING LOOKS.

There is no check that the push gate still denies, that the credential scanner
still scans, or that `.claude/settings.json` still names them. Each of those
failures is silent in the worst way available: the hook runs, exits 0, and the
absence of a complaint reads exactly like a pass. A hook edited to `exit 0` and a
hook that found nothing are the same observation.

**And the failure does not need malice.** A merge resolved with `--ours` on
`settings.json` drops a wiring line. A `git config core.hooksPath` set for an
unrelated reason unhooks all four at once. A tool renamed without its caller
updated leaves a hook invoking a path that no longer exists -- and
`.githooks/pre-commit` already records five places where `exit 0` was reached by
accident rather than by decision.

── WHAT IS COVERED, DERIVED WHERE POSSIBLE ─────────────────────────────────
1. **Every file in `.githooks/`** -- sha256 of each, plus that the directory is
   the one git is actually using.
2. **`core.hooksPath` itself.** A perfect set of hooks in a directory git is not
   reading is the failure with the least evidence, because every file is intact.
3. **Every `tools/*.py` any hook invokes** -- DERIVED by scanning the hook
   sources, never typed, so a hook that starts calling a new tool brings it under
   the manifest instead of quietly leaving it out.
4. **The `.claude/settings.json` wiring** -- every PreToolUse, PostToolUse and
   SessionStart command, and its matcher, hashed as a set.
5. **THIS FILE.** A manifest checker that does not cover itself is one edit away
   from blessing everything.

── THE THREE-WAY COMPARISON, AND WHY TWO WOULD NOT DO ──────────────────────
Working tree against MANIFEST catches an edit. Working tree against HEAD catches
an uncommitted edit. **Neither alone catches a committed edit to both the hook and
the manifest in one push** -- which is what a normal, legitimate hook change looks
like, and is therefore what a bad one can hide inside.

So all three are compared and the states are kept apart:

  tree == HEAD == manifest   clean
  tree != HEAD               UNCOMMITTED EDIT -- loud, and possibly fine
  HEAD != manifest           COMMITTED DRIFT -- the manifest was not regenerated
  tree != manifest, == HEAD  the manifest is stale in HEAD too

── THE MANIFEST CHANGES ONLY BY AN EXPLICIT STEP THAT NAMES EACH CHANGE ────
`--regenerate` prints every hook whose hash moves, old and new, and refuses to
run silently. There is no auto-fix and no `--force`: a checker that quietly
rewrote its own expectations would be item 8's defect one step later -- a detector
blessing its own subject.

── FAIL CLOSED ON UNKNOWN, AND THE OPPOSITE FOR THE HOOK PATH ──────────────
Unreadable manifest, unreadable settings, git not answering: all exit 2. "I could
not check the hooks" is not "the hooks are fine", and those two answers look
identical in a terminal.

**This tool is deliberately NOT a PreToolUse hook**, and that is the fail-open
rule applied honestly rather than waived: a check that throws inside a Bash
PreToolUse hook blocks every command in the session, and the first thing anybody
does about that is switch it off -- which would remove the thing it was protecting.
It belongs in the recurring report-only set and in a pre-push read, where a crash
costs one message.
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

CRITERIA_VERSION = '2026-09-29.1'
MANIFEST_REL = os.path.join('docs', 'hook-manifest.json')
SETTINGS_REL = os.path.join('.claude', 'settings.json')
# The record of the hook-disabling decision. Its PRESENCE is what tells an
# empty `hooks` object apart from one a tool stripped by accident -- see
# intentionally_disarmed().
DISARMED_REL = os.path.join('docs', 'hooks-disabled-2026-10-13.json')
SELF_REL = os.path.join('tools', 'hook_integrity_check.py')

# The hook events whose wiring is enforcement. PostToolUse is included: several
# of this repo's detectors run there, and an unwired detector is as silent as an
# unwired gate.
WIRED_EVENTS = ('PreToolUse', 'PostToolUse', 'SessionStart', 'UserPromptSubmit')

# A tools/ path named inside a hook. Matched on the PATH SHAPE rather than on a
# list of tool names, so a hook that starts invoking something new is covered
# without this file being edited.
TOOL_REF_RE = re.compile(r'tools/([a-z0-9_]+\.py)')


class CouldNotRun(Exception):
    """Something needed could not be read. Never folded into a clean result."""


# ── LINE ENDINGS ARE NORMALISED, AND THIS IS NOT A CONVENIENCE ──────────────
# The FIRST run of this check reported three tools as drifted in both directions
# at once -- tree != HEAD *and* HEAD != manifest -- on a working tree `git status`
# called clean. The cause is the one CLAUDE.md names explicitly: `git show`
# emits the STORED blob, which `.gitattributes` keeps at LF, while the working
# tree can hold CRLF, and this clone has both states in different files.
#
# "A CRLF-vs-LF difference is not drift" is a standing rule here precisely because
# it produced three separate false alarms in one session on 2026-09-03. A hook's
# behaviour does not depend on its line endings, so hashing them in would make
# this check fire on a difference that changes nothing -- and a check that fires
# on nothing is one somebody turns off, taking the real coverage with it.
#
# Normalising in ONE function rather than at each call site, so the tree side and
# the HEAD side cannot end up normalised differently. That asymmetry is how the
# false alarm would come back looking like a real finding.
def _normalise(raw):
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', 'replace')
    CR, LF = chr(13), chr(10)
    return raw.replace(CR + LF, LF).replace(CR, LF)


def sha256_file(path):
    try:
        with open(path, 'rb') as fh:
            return sha256_text(_normalise(fh.read()))
    except OSError as exc:
        raise CouldNotRun('could not read %s (%s)' % (path, exc))


def sha256_text(text):
    return hashlib.sha256(_normalise(text).encode('utf-8')).hexdigest()


def git(repo, *args):
    try:
        p = subprocess.run(['git', '-C', repo] + list(args), capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=30)
    except Exception as exc:
        raise CouldNotRun('git %s raised %s' % (' '.join(args),
                                                type(exc).__name__))
    return p.returncode, (p.stdout or '')


def head_blob_sha(repo, rel):
    """sha256 of the file AS COMMITTED AT HEAD, or None if absent there.

    Hashed from `git show` rather than compared by git's own blob id, because the
    manifest stores content hashes and mixing the two would make the three-way
    comparison compare different things.
    """
    rc, out = git(repo, 'show', 'HEAD:' + rel.replace('\\', '/'))
    if rc != 0:
        return None
    return sha256_text(out)


def hooks_path(repo):
    """The hooks directory git is ACTUALLY using, and whether it is ours."""
    rc, out = git(repo, 'config', '--get', 'core.hooksPath')
    configured = out.strip() if rc == 0 else ''
    return configured


def githook_files(repo):
    d = os.path.join(repo, '.githooks')
    if not os.path.isdir(d):
        raise CouldNotRun('.githooks/ is not a directory in %s, so there is '
                          'nothing to hash and this is not a clean answer' % repo)
    names = sorted(f for f in os.listdir(d)
                   if os.path.isfile(os.path.join(d, f)) and not f.startswith('.'))
    if not names:
        raise CouldNotRun('.githooks/ is EMPTY. Zero hooks reads as nothing to '
                          'check and means every gate is gone.')
    return names


def wiring(repo):
    """{event: [ 'matcher :: command', ... ]} from settings.json, sorted.

    A SET rather than a list-with-positions on purpose: reordering the hooks is
    not a security change, and treating it as one would make the check fire on
    every unrelated edit until somebody turned it off.
    """
    path = os.path.join(repo, SETTINGS_REL)
    try:
        doc = json.loads(io.open(path, encoding='utf-8').read())
    except Exception as exc:
        raise CouldNotRun('could not read %s (%s). The wiring is half the '
                          'control and an unreadable settings file is not a '
                          'clean one.' % (SETTINGS_REL, exc))
    out = {}
    for ev in WIRED_EVENTS:
        rows = []
        for m in (doc.get('hooks', {}).get(ev) or []):
            matcher = m.get('matcher') or '*'
            for h in (m.get('hooks') or []):
                cmd = h.get('command') or ''
                rows.append('%s :: %s' % (matcher, ' '.join(cmd.split())))
        out[ev] = sorted(rows)
    return out


def invoked_tools(repo, hook_names, wiring_map):
    """tools/*.py named by any hook OR by the settings wiring. Derived."""
    found = set()
    for n in hook_names:
        p = os.path.join(repo, '.githooks', n)
        try:
            src = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError as exc:
            raise CouldNotRun('could not read .githooks/%s (%s)' % (n, exc))
        found.update(TOOL_REF_RE.findall(src))
    for rows in wiring_map.values():
        for r in rows:
            found.update(TOOL_REF_RE.findall(r))
    # Only the ones that exist; a named-but-absent tool is its own finding below.
    return sorted(found)


def observe(repo):
    """Everything this check knows how to hash, from the WORKING TREE."""
    names = githook_files(repo)
    wmap = wiring(repo)
    tools = invoked_tools(repo, names, wmap)

    obs = {'hooks': {}, 'tools': {}, 'wiring': {}, 'missing_tools': [],
           'hooks_path': hooks_path(repo), 'self': None}

    for n in names:
        obs['hooks'][n] = sha256_file(os.path.join(repo, '.githooks', n))
    for t in tools:
        p = os.path.join(repo, 'tools', t)
        if not os.path.isfile(p):
            # A hook invoking a tool that is not there. NOT silent: the hook
            # will fail or skip, and which of those it does is the hook's
            # problem -- this check's job is to say the reference is broken.
            obs['missing_tools'].append(t)
            continue
        obs['tools'][t] = sha256_file(p)
    for ev, rows in wmap.items():
        obs['wiring'][ev] = sha256_text('\n'.join(rows))
    obs['wiring_rows'] = wmap
    # ── AND ITSELF. See the header: a manifest checker that does not cover
    # itself is one edit away from blessing everything.
    obs['self'] = sha256_file(os.path.join(repo, SELF_REL))
    return obs


def load_manifest(repo):
    path = os.path.join(repo, MANIFEST_REL)
    if not os.path.isfile(path):
        raise CouldNotRun(
            '%s is not on disk. Without a manifest there is no expectation to '
            'compare against, and a check with nothing to compare reports clean '
            'for every possible state of the hooks. Generate it with '
            '--regenerate.' % MANIFEST_REL)
    try:
        return json.loads(io.open(path, encoding='utf-8').read())
    except Exception as exc:
        raise CouldNotRun('could not parse %s (%s)' % (MANIFEST_REL, exc))


# ── THE WIRING COMPARISON, LIFTED OUT OF compare() ON 2026-10-11 ───────────
# Lifted rather than copied, and that is the whole point of doing it this way.
# `--wiring-only` below needs exactly this comparison and nothing else; a second
# implementation of it would be free to drift from this one, and the drift would
# show up as the cheap check reporting clean while the full check reports a
# removal -- which is the shape of defect this file exists to catch.
def wiring_findings(obs, man):
    """Settings-wiring drift only. Same text the full run prints."""
    findings = []
    for ev, sha in sorted(obs['wiring'].items()):
        expected = (man.get('wiring') or {}).get(ev)
        if expected is None:
            findings.append('WIRING %s is not in the manifest.' % ev)
            continue
        if sha != expected:
            exp_rows = (man.get('wiring_rows') or {}).get(ev) or []
            now_rows = obs['wiring_rows'].get(ev) or []
            gone = [r for r in exp_rows if r not in now_rows]
            added = [r for r in now_rows if r not in exp_rows]
            findings.append(
                'WIRING %s CHANGED. %d line(s) REMOVED, %d added. A removed line '
                'is an unwired control: the tool is still on disk, still correct, '
                'and never runs.%s%s'
                % (ev, len(gone), len(added),
                   ''.join('\n        REMOVED: ' + r for r in gone),
                   ''.join('\n        ADDED:   ' + r for r in added)))
    return findings


# ── WHY A CHEAP MODE EXISTS AT ALL, 2026-10-11 ──────────────────────────────
# MEASURED, not hypothesised. At 20:45 on 2026-10-11 this clone's working-tree
# `.claude/settings.json` held `"hooks": {"SessionStart": []}` against a HEAD
# (a8956a6f) carrying six SessionStart commands. The six that stopped running:
# session_lock_check.py start, sairn_claim_hook.py, sairn_status.py --hook,
# dispatch_state.py --hook, hover_self_health_shim.py -- and THIS FILE.
# `SAIRN-fourth` was in the same state at the same minute; cc and cody were too
# and were restored at 20:55 and 20:57. A harness-side rewrite of settings.json
# is the only cause consistent with four clones at one minute, and it kept
# PreToolUse, PostToolUse, PreCompact and UserPromptSubmit intact.
#
# THE FULL RUN ALREADY DETECTS THIS EXACTLY -- verified against the still-
# disarmed SAIRN-fourth, which printed `WIRING SessionStart CHANGED. 6 line(s)
# REMOVED` and named all six. Nothing about the detection was missing.
#
# WHAT WAS MISSING IS THAT ITS ONLY TRIGGER WAS THE EVENT THAT GOT EMPTIED. A
# detector wired solely to SessionStart cannot report the removal of SessionStart;
# it is removed by the same edit, and a session that never runs it is
# indistinguishable from a session where it found nothing. Self-concealing, and
# it concealed itself for at least one session in four clones.
#
# So this mode runs from UserPromptSubmit, which survived. TWO JSON READS, no
# hashing of 60 files and no git subprocess, because a per-prompt check that
# costs seconds is one somebody turns off -- taking the coverage with it.
#
# IT DOES NOT CLOSE THE HOLE, IT NARROWS IT, and overstating that would be worse
# than leaving it open. Removal of SessionStart alone is now reported on the first
# prompt. Removal of BOTH SessionStart and UserPromptSubmit is still invisible to
# this file, because nothing it can be wired to is guaranteed to survive. The
# remaining residue is named in the report rather than left for somebody to
# discover the same way.
# ── THE ONE HOOK THE DISARMED STATE STILL ALLOWS (2026-10-13) ──────────────
# Michael authorised a single SessionStart hook with matcher `compact` for
# compaction survival -- the OPPOSITE problem to the one that got the 23
# cleared. So "disarmed" now means EMPTY *or* exactly that one entry, and
# nothing else.
#
# THE TEST IS DELIBERATELY EXACT, not a prefix or a count. One event, one
# matcher, one command, and the command must name this tool. A second command
# beside it, a different matcher, or any other event is drift again -- which is
# the whole point, because the failure being guarded against is a hook quietly
# reappearing.
COMPACTION_TOOL = 'compaction_brief.py'


def _only_compaction_brief(hooks):
    if set(hooks) != {'SessionStart'}:
        return False
    groups = hooks.get('SessionStart') or []
    if len(groups) != 1:
        return False
    g = groups[0] or {}
    if (g.get('matcher') or '') != 'compact':
        return False
    cmds = g.get('hooks') or []
    if len(cmds) != 1:
        return False
    return COMPACTION_TOOL in (cmds[0] or {}).get('command', '')


def intentionally_disarmed(repo):
    """Is `hooks` present and EMPTY in this clone's settings.json?

    ── AN EMPTY HOOKS OBJECT IS A DECISION NOW, NOT DRIFT (2026-10-13) ──────
    Michael cleared the hooks on 2026-10-11 because they were causing agent
    compaction, and the decision is standing: they are never to be restored.
    This check was built for the opposite case -- a control silently going
    missing -- and at that point `hooks: {}` and `hooks: <stripped by a
    PowerShell round trip>` were indistinguishable from here. They no longer
    are, because the empty object is now COMMITTED and
    docs/hooks-disabled-2026-10-13.json carries what was removed and why.

    SO THE TEST IS DELIBERATELY NARROW: the key must EXIST and be EMPTY. A
    `hooks` key that is absent entirely is still a finding -- that is a
    different file, not a disarmed one -- and a hooks object with SOME events
    wired and others missing is still drift, which is the case the 2026-10-11
    incident actually was (`{"SessionStart": []}` against 23 commands).
    """
    path = os.path.join(repo, SETTINGS_REL)
    try:
        doc = json.loads(io.open(path, encoding='utf-8').read())
    except Exception:                                            # noqa: BLE001
        return False
    if 'hooks' not in doc:
        return False
    h = doc.get('hooks')
    if not isinstance(h, dict):
        return False
    if h and not _only_compaction_brief(h):
        return False
    # The record of the decision has to be THERE. Without it this is just an
    # empty object again, and accepting it would be the self-certifying
    # exemption this file refuses everywhere else.
    return os.path.isfile(os.path.join(repo, DISARMED_REL))


def wiring_only(repo):
    """(findings, could_not) for the settings wiring alone. May raise."""
    if intentionally_disarmed(repo):
        return [], []
    wmap = wiring(repo)
    man = load_manifest(repo)
    obs = {'wiring': dict((ev, sha256_text('\n'.join(rows)))
                          for ev, rows in wmap.items()),
           'wiring_rows': wmap}
    could_not = []
    if not (man.get('wiring') or {}):
        could_not.append(
            'the manifest records no wiring at all, so NOTHING was compared. '
            'Regenerate it with --regenerate.')
    return wiring_findings(obs, man), could_not


def compare(repo, obs, man):
    """(findings, could_not) -- the three-way comparison, states kept apart."""
    findings, could_not = [], []

    def three_way(kind, key, rel, seen):
        expected = (man.get(kind) or {}).get(key)
        at_head = head_blob_sha(repo, rel)
        if expected is None:
            findings.append('%s %s is NOT IN THE MANIFEST at all. An enforcement '
                            'control nothing has an expectation for is unchecked, '
                            'which is the state this tool exists to end.'
                            % (kind[:-1].upper(), key))
            return
        if seen == expected and at_head == expected:
            return
        if at_head is None:
            findings.append('%s %s is in the manifest and NOT AT HEAD -- it is '
                            'untracked or was deleted in a commit.'
                            % (kind[:-1].upper(), key))
            return
        if seen != at_head:
            findings.append('%s %s DIFFERS BETWEEN THE WORKING TREE AND HEAD -- an '
                            'uncommitted edit. That may be legitimate; it is never '
                            'silent. tree=%s head=%s'
                            % (kind[:-1].upper(), key, seen[:12], at_head[:12]))
        if at_head != expected:
            findings.append('%s %s CHANGED IN A COMMIT AND THE MANIFEST WAS NOT '
                            'REGENERATED. This is the one a two-way check misses: '
                            'a hook and its expectation moving together in one '
                            'push is what a legitimate change looks like. '
                            'head=%s manifest=%s'
                            % (kind[:-1].upper(), key, at_head[:12],
                               expected[:12]))

    for n, sha in sorted(obs['hooks'].items()):
        three_way('hooks', n, os.path.join('.githooks', n), sha)
    for n in sorted(set(man.get('hooks') or {}) - set(obs['hooks'])):
        findings.append('HOOK %s is in the manifest and NOT IN .githooks/. A hook '
                        'that is gone enforces nothing, and its absence is the '
                        'quietest possible failure.' % n)

    # ── THE DISARMED CASE, AND WHAT IT DOES *NOT* EXCUSE (2026-10-13) ───────
    # `invoked_tools()` DERIVES its set from the hook files and the settings
    # wiring, so an intentionally empty `hooks` object makes that set shrink to
    # whatever .githooks/ still names -- and every manifest tool it no longer
    # reaches reports as "no longer hashed". Measured on the clone the moment
    # the hooks were emptied: 17 of those rows plus 4 WIRING rows, all of them
    # restating the decision rather than finding anything.
    #
    # THE NARROWNESS IS THE WHOLE POINT. Only the two WIRING-DERIVED families
    # are expected: a tool the wiring no longer reaches, and the wiring hashes
    # themselves. The `TOOL x CHANGED IN A COMMIT AND THE MANIFEST WAS NOT
    # REGENERATED` rows are NOT excused -- they are about a tool's CONTENT
    # against its recorded expectation, they were red before the hooks were
    # emptied, and they stay red. 7 of them at this HEAD, none of them this
    # session's.
    disarmed = intentionally_disarmed(repo)
    expected_under_disarm = []
    for t, sha in sorted(obs['tools'].items()):
        three_way('tools', t, os.path.join('tools', t), sha)
    for t in sorted(set(man.get('tools') or {}) - set(obs['tools'])):
        row = ('TOOL %s is in the manifest and is no longer hashed -- either '
               'the file is gone or no hook invokes it any more. Both change '
               'what is enforced.' % t)
        if disarmed and os.path.isfile(os.path.join(repo, 'tools', t)):
            # The FILE IS STILL THERE, so "gone" is excluded by measurement
            # rather than by assumption; what changed is which hook reaches it.
            expected_under_disarm.append(
                'TOOL %s is unreached because the hooks are intentionally '
                'empty. The file is still on disk.' % t)
        else:
            findings.append(row)

    if disarmed:
        expected_under_disarm.extend(
            'EXPECTED: ' + w for w in wiring_findings(obs, man))
    else:
        findings.extend(wiring_findings(obs, man))
    # A THIRD CHANNEL, AND NOT could_not. The first draft appended this to
    # could_not and the run exited 2 -- COULD NOT RUN -- which is false: the
    # check ran, compared everything, and these rows are a DELIBERATE
    # exemption with a committed record behind them. Exit 2 is reserved for
    # "nothing was checked" and overloading it would make a working run
    # indistinguishable from a broken one, which is the defect this file's own
    # header is about. Carried on the function so the signature stays
    # (findings, could_not) for every existing caller.
    compare.expected_under_disarm = expected_under_disarm

    expected_path = man.get('hooks_path')
    if expected_path is None:
        could_not.append('the manifest records no core.hooksPath, so whether git '
                         'is reading .githooks/ was NOT checked.')
    elif obs['hooks_path'] != expected_path:
        # ── TWO CAUSES, AND THEY NEED DIFFERENT SENTENCES ──────────────────
        # UNSET is the default state of a FRESH CLONE: core.hooksPath is local
        # git config, not tracked content, so cloning this repository installs
        # every hook file and arms NONE of them. Found by running this check
        # against a fresh clone of origin/main on 2026-09-29 -- the content half
        # matched byte-for-byte and the arming half was simply absent.
        # REPOINTED is the other cause and is a deliberate act.
        # A message naming the wrong one sends the reader to the wrong fix.
        if not (obs['hooks_path'] or '').strip():
            findings.append(
                'core.hooksPath IS NOT SET AND THE MANIFEST EXPECTS %r, so GIT IS '
                'RUNNING NO HOOKS AT ALL IN THIS CLONE. Every hook file is '
                'present and every hash matches -- they are simply not armed. '
                'THIS IS THE DEFAULT STATE OF A FRESH CLONE, because '
                'core.hooksPath is local config rather than tracked content: '
                'cloning installs the files and arms none of them. Fix: python '
                'tools/install_git_hooks.py' % expected_path)
        else:
            findings.append(
                'core.hooksPath IS %r AND THE MANIFEST EXPECTS %r -- it has been '
                'REPOINTED. This is the failure with the least evidence on it: '
                'every hook file can be byte-perfect while git reads a different '
                'directory, so nothing in any diff shows it and every gate is '
                'off at once.' % (obs['hooks_path'], expected_path))

    if obs['missing_tools']:
        findings.append(
            'A HOOK OR THE WIRING NAMES %d tool(s) THAT ARE NOT ON DISK: %s. '
            'Whether that hook then fails loudly or skips silently is its own '
            'business; the reference is broken either way.'
            % (len(obs['missing_tools']), ', '.join(obs['missing_tools'])))

    exp_self = man.get('self')
    if exp_self is None:
        could_not.append('the manifest does not record this file\'s own hash, so '
                         'the checker is NOT covering itself -- one edit away from '
                         'blessing everything.')
    else:
        three_way_self_head = head_blob_sha(repo, SELF_REL)
        if obs['self'] != exp_self or three_way_self_head != exp_self:
            findings.append(
                'THIS CHECKER ITSELF has drifted from the manifest '
                '(tree=%s head=%s manifest=%s). Read this one first: a checker '
                'that changed without its expectation changing can be reporting '
                'anything at all.'
                % (obs['self'][:12],
                   (three_way_self_head or 'absent')[:12], exp_self[:12]))

    return findings, could_not


def regenerate(repo, obs, man):
    """Write the manifest, NAMING every hash that moves. No silent path."""
    changes = []
    for kind in ('hooks', 'tools', 'wiring'):
        old, new = man.get(kind) or {}, obs[kind]
        for k in sorted(set(old) | set(new)):
            if old.get(k) != new.get(k):
                changes.append('%-7s %-34s %s -> %s'
                               % (kind, k, (old.get(k) or 'absent')[:12],
                                  (new.get(k) or 'absent')[:12]))
    if (man.get('hooks_path') or None) != obs['hooks_path']:
        changes.append('%-7s %-34s %r -> %r' % ('config', 'core.hooksPath',
                                                man.get('hooks_path'),
                                                obs['hooks_path']))
    if (man.get('self') or None) != obs['self']:
        changes.append('%-7s %-34s %s -> %s'
                       % ('self', SELF_REL, (man.get('self') or 'absent')[:12],
                          obs['self'][:12]))

    print('REGENERATING %s' % MANIFEST_REL)
    if not changes:
        print('  nothing moved. The manifest already matches the working tree.')
    else:
        print('  %d change(s), EACH NAMED -- this is the whole point of the step '
              'being explicit:' % len(changes))
        for c in changes:
            print('    ' + c)

    out = {
        'criteria': CRITERIA_VERSION,
        'note': ('GENERATED by tools/hook_integrity_check.py --regenerate. '
                 'Do not hand-edit: the whole value of this file is that a hook '
                 'and its expectation cannot move together without somebody '
                 'running a command that names the change.'),
        'hooks_path': obs['hooks_path'],
        'hooks': obs['hooks'],
        'tools': obs['tools'],
        'wiring': obs['wiring'],
        'wiring_rows': obs['wiring_rows'],
        'self': obs['self'],
    }
    io.open(os.path.join(repo, MANIFEST_REL), 'w', encoding='utf-8',
            newline='\n').write(json.dumps(out, indent=1, sort_keys=True) + '\n')
    print('  wrote %s' % MANIFEST_REL)
    print()
    print('  THE SELF HASH IS NOW STALE BY CONSTRUCTION if this run also changed')
    print('  this file. Re-run --regenerate once more in that case; it converges')
    print('  in one step and says so rather than looping.')
    return EXIT_CLEAN


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', default=REPO,
                    help='the working copy to check. Exists so the manifest can '
                         'be verified against a FRESH CLONE of origin/main, not '
                         'only against the tree that generated it.')
    ap.add_argument('--regenerate', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--wiring-only', action='store_true',
                    help='compare ONLY the .claude/settings.json wiring against '
                         'the manifest. Two JSON reads, no hashing, no git -- '
                         'cheap enough to run on every prompt, which is the '
                         'point: see the note above wiring_only().')
    ap.add_argument('--hook', action='store_true',
                    help='--wiring-only, emitted as UserPromptSubmit '
                         'additionalContext. ALWAYS exits 0 -- a non-zero exit '
                         'here blocks the prompt, and a check that blocks every '
                         'prompt gets switched off. Its mechanism is the message, '
                         'not the status.')
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)

    # ── THE HOOK PATH, BEFORE ANY BANNER ───────────────────────────────────
    # Prints nothing on a clean wiring. The SessionStart banner is useful to a
    # human running this by hand and is noise on every prompt; a hook that
    # chatters is one somebody unwires.
    if args.hook:
        try:
            findings, could_not = wiring_only(repo)
        except CouldNotRun as exc:
            # Said out loud, never folded into silence. "Could not check the
            # wiring" is the third state and it is the one that looks like a
            # pass if nothing prints.
            emit_hook_context(
                'HOOK WIRING CHECK -- COULD NOT RUN (this is NOT a pass): %s\n'
                'Run `python tools/hook_integrity_check.py` and say so in the '
                'session report.' % exc)
            return EXIT_CLEAN
        if not findings and not could_not:
            return EXIT_CLEAN
        lines = ['HOOK WIRING DRIFT in .claude/settings.json -- an unwired '
                 'control is on disk, correct, and never runs.']
        lines.extend('  ! %s' % f for f in findings)
        lines.extend('  ? %s' % c for c in could_not)
        lines.append('Restore it (`git restore .claude/settings.json` if the '
                     'removal is uncommitted), re-run `python '
                     'tools/hook_integrity_check.py`, and REPORT this -- the '
                     'session that ran without those hooks did so unguarded.')
        emit_hook_context('\n'.join(lines))
        return EXIT_CLEAN

    if args.wiring_only:
        print('HOOK WIRING ONLY -- settings.json against the manifest')
        print('  criteria : %s' % CRITERIA_VERSION)
        print('  repo     : %s' % repo)
        if intentionally_disarmed(repo):
            print('')
            _hk = wiring(repo)
            _n = sum(len(v) for v in _hk.values())
            print('INTENTIONALLY DISARMED -- %s, and'
                  % ('`hooks` is present and EMPTY' if not _n else
                     'the ONLY wired hook is the authorised '
                     'SessionStart/compact compaction brief'))
            print('%s records what was removed,' % DISARMED_REL)
            print('by whom and why. Michael cleared the hooks on 2026-10-11')
            print('because they were causing agent compaction; the decision is')
            print('standing and they are NOT to be restored.')
            print('')
            print('NOT a pass over an unchecked wiring -- there is no wiring to')
            print('check. A `hooks` key that is ABSENT, or one with some events')
            print('wired and others missing, is still drift and still reported.')
            return EXIT_CLEAN
        try:
            findings, could_not = wiring_only(repo)
        except CouldNotRun as exc:
            print()
            print('COULD NOT RUN: %s' % exc)
            return EXIT_COULD_NOT_RUN
        print()
        for c in could_not:
            print('  ? %s' % c)
        for f in findings:
            print('  ! %s' % f)
        if not findings and not could_not:
            print('  The wiring for %s matches the manifest.'
                  % ', '.join(WIRED_EVENTS))
        print()
        print('  THIS MODE CHECKS THE WIRING ONLY. It says nothing about the '
              'hook FILES, the tools they invoke, or core.hooksPath -- run '
              'without --wiring-only for those.')
        if could_not:
            return EXIT_COULD_NOT_RUN
        return EXIT_FINDING if findings else EXIT_CLEAN
    print('HOOK INTEGRITY -- an edited hook is trusted like a correct one')
    print('  criteria : %s' % CRITERIA_VERSION)
    print('  repo     : %s' % repo)

    try:
        obs = observe(repo)
        man = {} if args.regenerate and not os.path.isfile(
            os.path.join(repo, MANIFEST_REL)) else load_manifest(repo)
    except CouldNotRun as exc:
        print()
        print('COULD NOT RUN: %s' % exc)
        print('This is the THIRD STATE. "I could not check the hooks" is NOT '
              '"the hooks are fine", and the two look identical here.')
        return EXIT_COULD_NOT_RUN

    if args.regenerate:
        return regenerate(repo, obs, man)

    print('  hooks    : %d in .githooks/' % len(obs['hooks']))
    print('  tools    : %d invoked by a hook or by the wiring, DERIVED from the '
          'sources' % len(obs['tools']))
    print('  wiring   : %s' % ', '.join(
        '%s=%d' % (ev, len(obs['wiring_rows'].get(ev) or []))
        for ev in WIRED_EVENTS))
    print('  hooksPath: %r' % obs['hooks_path'])
    print('  covers itself: %s' % ('yes' if man.get('self') else 'NO'))

    compare.expected_under_disarm = []
    findings, could_not = compare(repo, obs, man)
    expected = getattr(compare, 'expected_under_disarm', [])

    print()
    if expected:
        print('EXPECTED UNDER THE HOOK-DISABLING DECISION (%d) -- not findings, '
              'not failures,' % len(expected))
        print('and not dropped either. See %s.' % DISARMED_REL)
        for e in expected:
            print('  = %s' % e)
        print()
    if could_not:
        print('COULD NOT CHECK (%d) -- NOT a pass:' % len(could_not))
        for c in could_not:
            print('  ? %s' % c)
        print()
    if findings:
        print('DRIFT (%d):' % len(findings))
        for f in findings:
            print('  ! %s' % f)
    else:
        print('Every hook, every tool a hook invokes, the settings wiring and '
              'core.hooksPath match the manifest in the working tree AND at HEAD.')

    print()
    print('  WHAT A CLEAN RUN DOES NOT SAY: that the hooks are CORRECT. It says')
    print('  they are UNCHANGED since somebody ran --regenerate. A hook that was')
    print('  wrong when the manifest was generated is still wrong and still')
    print('  clean here.')

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'repo': repo,
                          'observed': obs, 'findings': findings,
                          'could_not_check': could_not,
                          'expected_under_disarm': expected}, indent=2))

    if could_not:
        return EXIT_COULD_NOT_RUN
    return EXIT_FINDING if findings else EXIT_CLEAN


if __name__ == '__main__':
    try:
        sys.exit(main())
    except CouldNotRun as exc:
        print('COULD NOT RUN: %s' % exc)
        sys.exit(EXIT_COULD_NOT_RUN)
