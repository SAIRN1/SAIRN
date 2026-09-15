#!/usr/bin/env python
"""tools/hover_auditor_scope_gate.py -- make the hover auditor's core rule
STRUCTURAL instead of a thing it remembers.

THE RULE, quoted from the role's own skill file rather than paraphrased here:

    "Never write, edit, or push platform code. Find something that needs
     fixing -- report it, do not fix it yourself."
    -- .claude/skills/sairn-hover-auditor/SKILL.md, "The core rule,
       non-negotiable"

and the exception, also quoted, because a gate that refuses the auditor's OWN
tooling would stop it doing its job and would be switched off within the hour:

    "this role's own operational tooling -- the self-log, this skill file,
     anything that records or verifies the hover auditor's *own* actions
     rather than the platform's -- is not 'platform code' ... The test is
     simple: does it get audited by this role, or does it audit?"

WHY A GATE AND NOT A REMINDER. The auditor is the one role on this platform
with no second reader: the four build agents review each other, and nobody
reviews the auditor. Barings and Arthur Andersen are the skill file's own two
precedents for what that costs, and both are cases where the individual's
intentions were not the failing variable. A rule with no mechanism is a rule
that holds exactly as long as attention does.

WHAT THIS IS NOT. It cannot prove the auditor never edited platform code --
only that no such edit reached a COMMIT in a clone where this is installed.
The working-tree half is real and is `--worktree`; the history half is
tools/hover_separation_audit.py, which is a different mechanism reading a
different source, and is the one that notices this gate having silently gone
missing.

    python tools/hover_auditor_scope_gate.py --install     # mark THIS clone as the auditor's
    python tools/hover_auditor_scope_gate.py --uninstall
    python tools/hover_auditor_scope_gate.py --check       # is it armed here?
    python tools/hover_auditor_scope_gate.py --pre-commit  # hook entry: staged files
    python tools/hover_auditor_scope_gate.py --pre-push    # hook entry: outgoing commits
    python tools/hover_auditor_scope_gate.py --worktree    # every modified file, staged or not
    python tools/hover_auditor_scope_gate.py --explain     # print the scope and its source

WHICH DIRECTION IT FAILS, AND WHY IT IS NOT ONE ANSWER FOR BOTH CLONES.

  * Marker ABSENT -- this clone is not the auditor's, so there is nothing to
    protect. Exit 0 immediately. That is a SCOPE condition, not an inability
    to tell, and folding it into a refusal would break every build clone's
    commits for a rule that does not apply to them.

  * Marker PRESENT and anything at all cannot be determined -- the diff will
    not read, the skill file is missing, the scope sentence no longer appears
    in it -- REFUSE. In the auditor's own clone "could not tell" is the third
    state CLAUDE.md names, and it is never folded into "passed" (PR SS1.11).

THE SCOPE SENTENCE IS RE-READ FROM THE SKILL ON EVERY RUN, and its absence is
a refusal rather than a default. That is deliberate and it is the eighth
cross-domain discipline applied to this file: if somebody rewrites the core
rule, this gate must stop and be re-derived rather than keep enforcing a
sentence the role no longer holds. A stale gate enforcing a repealed rule is
worse than no gate, because it reads as coverage.
"""

import os
import re
import subprocess
import sys

SKILL_DIR = '.claude/skills/sairn-hover-auditor/'
REGISTER = 'docs/defect-density-register.json'

# ── THE ALLOWLIST, AND EVERY ENTRY CARRIES THE SENTENCE THAT PUT IT THERE ────
# Nothing is here because it seemed reasonable. If a future reader wants to add
# a path, the bar is a quotable sentence in the role's own skill file, not a
# judgement made at the gate.
ALLOWED = (
    (SKILL_DIR,
     'SKILL.md, core rule exception: "this skill file ... is not platform '
     'code and building it is genuinely this role\'s job"'),
    (REGISTER,
     'SKILL.md, "Where findings go": "Log real findings to '
     'docs/defect-density-register.json via tools/defect_register.py --add"'),
)

# Named explicitly so the reader does not have to infer it from the absence of
# an allowlist entry. The skill states this one directly.
EXPLICITLY_DENIED = (
    ('tools/defect_register.py',
     'SKILL.md, "Where findings go": adding the hover-audit enum value "is a '
     'code edit this role does not make itself ... route the enum fix to a '
     'build agent"'),
)

# Short, quoted, and load-bearing: if this phrase is gone from the skill, the
# rule this gate enforces may have been rewritten and the gate REFUSES rather
# than carrying on. Kept short on purpose -- a long anchor rots on a reflow.
SCOPE_ANCHOR = 'Never write, edit, or push platform code'

MARKER = 'sairn-hover-auditor-clone'   # lives in .git/, so it is per-clone


def git(*args, **kw):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', **kw)
    return r.returncode, r.stdout, r.stderr


def repo_root():
    code, out, _ = git('rev-parse', '--show-toplevel')
    if code != 0:
        return None
    return out.strip()


def git_dir():
    code, out, _ = git('rev-parse', '--git-dir')
    if code != 0:
        return None
    p = out.strip()
    return p if os.path.isabs(p) else os.path.join(os.getcwd(), p)


def marker_path():
    g = git_dir()
    return os.path.join(g, MARKER) if g else None


def is_auditor_clone():
    m = marker_path()
    return bool(m and os.path.isfile(m))


def violations(paths):
    """Split paths into (allowed, refused). Pure -- no git, no filesystem.

    Kept pure so the probe can drive it on invented paths without touching a
    repo, which is the only way to test the REFUSING direction without
    committing a violation to find out.
    """
    allowed, refused = [], []
    for p in paths:
        p = p.replace('\\', '/').strip()
        if not p:
            continue
        ok = False
        for prefix, _why in ALLOWED:
            if prefix.endswith('/'):
                if p.startswith(prefix):
                    ok = True
                    break
            elif p == prefix:
                ok = True
                break
        (allowed if ok else refused).append(p)
    return allowed, refused


def scope_is_still_the_rule(root):
    """Returns (ok, reason). NOT a boolean -- the caller must be able to say
    WHICH failure it hit, because 'skill file missing' and 'rule reworded' need
    different human responses and a bare False cannot tell them apart."""
    path = os.path.join(root, SKILL_DIR.replace('/', os.sep), 'SKILL.md')
    if not os.path.isfile(path):
        return False, 'the skill file is not at ' + path
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            src = fh.read()
    except OSError as exc:
        return False, 'the skill file could not be read: %s' % exc
    if SCOPE_ANCHOR not in src:
        return False, ('the core-rule sentence %r is no longer in the skill '
                       'file. The rule this gate enforces may have been '
                       'rewritten. Re-derive the scope from the skill and '
                       'update ALLOWED before re-arming.' % SCOPE_ANCHOR)
    return True, ''


def changed_staged():
    code, out, err = git('diff', '--cached', '--name-only')
    if code != 0:
        return None, 'git diff --cached failed: ' + err.strip()
    return [l for l in out.split('\n') if l.strip()], ''


def changed_worktree():
    # Both halves: tracked modifications AND untracked files. A mutation left
    # behind in an untracked scratch copy of a platform file is the shape that
    # actually happened here (self-log entry 0073, api/sv-witness.js patched in
    # place to drive a mutation control).
    code, out, err = git('status', '--porcelain', '--untracked-files=all')
    if code != 0:
        return None, 'git status failed: ' + err.strip()
    paths = []
    for line in out.split('\n'):
        if len(line) > 3:
            p = line[3:].strip()
            if ' -> ' in p:            # a rename reports both sides
                paths.extend(x.strip() for x in p.split(' -> '))
            else:
                paths.append(p)
    return paths, ''


def changed_outgoing(stdin_text):
    """Files in the commits this push would send.

    git hands a pre-push hook lines of `<local ref> <local sha> <remote ref>
    <remote sha>` on stdin. An all-zero remote sha means a new branch, where
    there is no range to diff against -- that is NOT 'nothing to check', and
    treating it as such is how a whole branch of violations would sail past.
    """
    ZERO = '0' * 40
    paths, notes = [], []
    lines = [l for l in (stdin_text or '').split('\n') if l.strip()]
    if not lines:
        return None, 'no ref lines on stdin -- cannot tell what is being pushed'
    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            return None, 'unparseable pre-push ref line: %r' % line
        _lref, lsha, _rref, rsha = parts[:4]
        if lsha == ZERO:               # a delete; sends no content
            continue
        rng = lsha if rsha == ZERO else '%s..%s' % (rsha, lsha)
        if rsha == ZERO:
            notes.append('new branch: checking every commit reachable from ' + lsha[:8])
            code, out, err = git('log', '--format=', '--name-only', lsha)
        else:
            code, out, err = git('diff', '--name-only', rng)
        if code != 0:
            return None, 'could not read the outgoing range %s: %s' % (rng, err.strip())
        paths.extend(l for l in out.split('\n') if l.strip())
    return sorted(set(paths)), '; '.join(notes)


def refuse(mode, refused, allowed):
    print('')
    print('  HOVER AUDITOR SCOPE GATE -- REFUSED (%s)' % mode)
    print('')
    print('  This clone is marked as the hover auditor\'s. The auditor does not')
    print('  write, edit or push platform code -- it reports what it finds and a')
    print('  build agent fixes it. %d path(s) are outside its scope:' % len(refused))
    print('')
    for p in refused[:40]:
        note = ''
        for d, why in EXPLICITLY_DENIED:
            if p == d:
                note = '   <-- named as out of scope: ' + why
        print('      %s%s' % (p, note))
    if len(refused) > 40:
        print('      ... and %d more' % (len(refused) - 40))
    print('')
    if allowed:
        print('  In scope and fine: %s' % ', '.join(allowed[:6]))
        print('')
    print('  WHAT TO DO INSTEAD -- report it. Log the finding to')
    print('  %s and hand the fix to a build agent.' % REGISTER)
    print('')
    print('  IF THIS IS WRONG, it is wrong in one of two ways and they need')
    print('  different answers. Either this clone is NOT the auditor\'s --')
    print('  then: python tools/hover_auditor_scope_gate.py --uninstall.')
    print('  Or the scope itself has changed -- then change the SKILL FILE')
    print('  first and ALLOWED to match it, in that order, so the rule and')
    print('  its enforcement cannot drift apart.')
    print('')
    return 1


def main(argv):
    args = argv[1:]
    if not args:
        args = ['--check']

    root = repo_root()
    if root is None:
        # Not a git repo at all. Nothing to gate, and nothing this gate is
        # responsible for -- it cannot be the auditor's clone either.
        print('hover_auditor_scope_gate: not a git repository; nothing to do')
        return 0

    if '--install' in args:
        m = marker_path()
        with open(m, 'w', encoding='utf-8') as fh:
            fh.write('This clone is the hover auditor\'s. '
                     'tools/hover_auditor_scope_gate.py refuses commits and '
                     'pushes that touch platform code here.\n')
        print('ARMED. %s' % m)
        print('The marker lives in .git/ and is per-clone, deliberately: it is')
        print('not committable, so no build clone can inherit it by pulling.')
        ok, why = scope_is_still_the_rule(root)
        print('scope sentence present in the skill: %s%s'
              % ('yes' if ok else 'NO', '' if ok else ' -- ' + why))
        print('Hooks still have to be pointed at .githooks/:')
        print('    python tools/install_git_hooks.py')
        return 0

    if '--uninstall' in args:
        m = marker_path()
        if m and os.path.isfile(m):
            os.remove(m)
            print('DISARMED. removed %s' % m)
        else:
            print('was not armed; nothing to remove')
        return 0

    if '--explain' in args:
        print('Hover auditor scope -- what this clone may change if armed:')
        for p, why in ALLOWED:
            print('  ALLOW  %s\n         %s' % (p, why))
        for p, why in EXPLICITLY_DENIED:
            print('  DENY   %s\n         %s' % (p, why))
        print('  DENY   everything else')
        ok, why = scope_is_still_the_rule(root)
        print('\nscope sentence still in the skill file: %s%s'
              % ('yes' if ok else 'NO', '' if ok else ' -- ' + why))
        print('armed in this clone: %s' % ('yes' if is_auditor_clone() else 'no'))
        return 0

    armed = is_auditor_clone()

    if '--check' in args:
        print('armed in this clone: %s' % ('YES' if armed else 'no'))
        if armed:
            ok, why = scope_is_still_the_rule(root)
            print('scope sentence present: %s%s'
                  % ('yes' if ok else 'NO', '' if ok else ' -- ' + why))
            return 0 if ok else 1
        return 0

    mode = ('--pre-commit' if '--pre-commit' in args else
            '--pre-push' if '--pre-push' in args else
            '--worktree' if '--worktree' in args else None)
    if mode is None:
        print(__doc__)
        return 2

    if not armed:
        # THE ONLY SILENT EXIT IN THIS FILE, and it is a scope condition rather
        # than a could-not-tell: this clone is not the auditor's, so the rule
        # does not apply. Printing here would put noise in front of every
        # commit in all four build clones.
        return 0

    ok, why = scope_is_still_the_rule(root)
    if not ok:
        print('')
        print('  HOVER AUDITOR SCOPE GATE -- CANNOT VERIFY ITS OWN SCOPE')
        print('  %s' % why)
        print('')
        print('  REFUSING rather than passing. A gate that cannot read the rule')
        print('  it enforces has not checked anything, and "could not tell" is')
        print('  not "passed".')
        print('')
        return 1

    if mode == '--pre-commit':
        paths, err = changed_staged()
    elif mode == '--worktree':
        paths, err = changed_worktree()
    else:
        paths, err = changed_outgoing(sys.stdin.read() if not sys.stdin.isatty() else '')

    if paths is None:
        print('')
        print('  HOVER AUDITOR SCOPE GATE -- COULD NOT READ THE CHANGE (%s)' % mode)
        print('  %s' % err)
        print('')
        print('  REFUSING. Not knowing what is in a change is not the same as')
        print('  knowing it is clean.')
        print('')
        return 1

    if err:
        print('  hover scope gate: %s' % err)

    allowed, refused = violations(paths)
    if refused:
        return refuse(mode, refused, allowed)

    if mode == '--worktree':
        print('hover scope gate: working tree clean of platform code (%d path(s) '
              'checked, all in scope)' % len(allowed))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
