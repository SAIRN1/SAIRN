"""
REFUSES TO AMEND A COMMIT THAT IS NOT SAFE TO AMEND, and runs the
fetch -> rebase -> regenerate -> push retry loop on top of that refusal.

── THE NEAR-MISS THIS EXISTS FOR (2026-09-26) ──────────────────────────────
This repo has five clones pushing to one branch, so a push often loses a race
and the honest response is fetch, rebase, re-derive the generated documents,
amend, push again. That loop was being written inline, as a shell one-liner,
per session. One of those loops did this:

    git rebase origin/main || { ...resolve... }
    python tools/master_plan.py ; python tools/traceability_matrix.py
    if [ -n "$(git status --porcelain)" ]; then git add -A; git commit --amend; fi

The rebase STOPPED MID-CONFLICT. `git rebase` returned non-zero, the shell
`||` branch did not cover every path, and execution reached the amend while
HEAD was a REWRITTEN COPY OF ANOTHER SESSION'S COMMIT -- the last commit the
rebase had successfully applied. `git commit --amend` therefore folded this
session's work into a copy of cody's commit, with cody's message and
authorship.

NOTHING CAUGHT THAT. It was noticed because a human happened to read the
`git log` output in the next step and saw someone else's subject line at HEAD.
Had the loop pushed, cody's commit would have been rewritten on a shared
branch, carrying changes its message does not describe -- and the message is
the only record anyone reads.

THE FIX IS NOT "BE CAREFUL IN THE LOOP". A mid-rebase tree is a state a tool
can detect in four file checks, and an amend is exactly the operation that must
not run in it. This refuses, by name, with the reason.

── THE FOUR REFUSALS ───────────────────────────────────────────────────────
1. AN OPERATION IS IN PROGRESS -- rebase (interactive or apply), merge,
   cherry-pick, revert, or bisect. In every one of these HEAD is not where the
   author thinks it is.
2. THERE ARE UNMERGED PATHS. A conflicted tree can be staged with `git add -A`
   and committed, which writes conflict markers into a file and calls it a fix.
3. HEAD IS NOT THIS SESSION'S COMMIT. Checked by SUBJECT against the set of
   local-only subjects captured BEFORE the loop started, because a rebase
   rewrites shas and a sha comparison alone fails open the moment the rebase it
   is guarding does its job.
4. HEAD IS ALREADY ON A REMOTE BRANCH. Amending a published commit is a forced
   push waiting to happen.

Any one of these and the amend is refused, loudly, exit 3. "Could not tell" is
not folded into "safe": if git itself cannot be read, that is refusal 0.

CLI:
    python tools/push_retry.py --check              # is an amend safe NOW?
    python tools/push_retry.py --capture            # print the safe-subject set
    python tools/push_retry.py --amend-guard        # exit 0 only if safe
    python tools/push_retry.py --loop [--attempts N]  # the whole retry loop
    python tools/push_retry.py --selftest           # fixtures, both directions
"""
import io
import json
import os
import subprocess
import sys

# ── THIS TOOL CRASHED PRINTING ITS OWN USAGE (found 2026-10-05) ────────────
# `python tools/push_retry.py` with no arguments falls through to
# `print(__doc__.strip())`, and the docstring above carries U+2500 box-drawing
# characters. On Windows the console encoding is cp1252, which has no mapping
# for them, so the usage path raised:
#
#     UnicodeEncodeError: 'charmap' codec can't encode characters in
#     position 143-144: character maps to <undefined>
#
# WHY THAT MATTERED MORE THAN A COSMETIC CRASH. This is the tool that exists to
# stop a lost push race from amending one session's work onto another session's
# commit -- the near-miss its own docstring describes. The first thing a session
# reaching for it does is run it to see how, and it answered with a traceback.
# The only way past was reading the source for `--loop --attempts`.
#
# RECONFIGURED RATHER THAN ASCII-ING THE DOCSTRING, deliberately: every tool in
# this repo uses those box rules, so stripping them here would fix one file and
# leave the pattern, and the next tool with a docstring would do it again.
# tools/gh_token.py has carried exactly these three lines since it was written;
# this is the same guard, not a new idea. `errors='replace'` is NOT used -- a
# mangled character is better than a crash, but a correct one is better still,
# and utf-8 can encode the whole docstring.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    # stderr too: amend_safety() prints its refusal reasons there, and a guard
    # whose REFUSAL cannot be printed is a guard that fails open at the moment
    # it is trying to stop something.
    sys.stderr.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── EVERY FILE GIT USES TO MARK AN OPERATION IN PROGRESS ──────────────────
# Named individually rather than globbed, so a reader can see what is covered
# and what is not. `rebase-apply` is the non-interactive form and was the one
# the near-miss actually hit; a check for `rebase-merge` alone would have
# passed straight through it.
IN_PROGRESS_MARKERS = [
    ('rebase-merge', 'an interactive rebase is in progress'),
    ('rebase-apply', 'a rebase (am/apply form) is in progress'),
    ('MERGE_HEAD', 'a merge is in progress'),
    ('CHERRY_PICK_HEAD', 'a cherry-pick is in progress'),
    ('REVERT_HEAD', 'a revert is in progress'),
    ('BISECT_LOG', 'a bisect is in progress'),
]

# The generated documents a rebase conflict must be resolved by RE-DERIVING
# rather than by merging text (PR 2.5). Listed because the loop regenerates
# them; a conflict in anything else is a human's problem and the loop stops.
GENERATED = [
    ('docs/MASTER-PLAN.md', 'tools/master_plan.py'),
    ('docs/traceability-matrix.md', 'tools/traceability_matrix.py'),
    ('docs/TOOLING-INVENTORY.md', 'tools/tooling_inventory.py'),
]

STATE_FILE = os.path.join(REPO, '.git', 'push_retry_safe_subjects.json')


def git(*args):
    """(exit, stdout, stderr). Never raises -- the caller decides what a
    failure means, and for this tool it usually means REFUSE."""
    try:
        p = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                           timeout=120)
        return (p.returncode,
                (p.stdout or b'').decode('utf-8', 'replace').strip(),
                (p.stderr or b'').decode('utf-8', 'replace').strip())
    except Exception as exc:
        return (-1, '', 'could not run git: %s' % exc)


def git_dir():
    rc, out, _ = git('rev-parse', '--git-dir')
    if rc != 0:
        return None
    return out if os.path.isabs(out) else os.path.join(REPO, out)


def operation_in_progress():
    """[(marker, why)] for every in-progress operation. None if unreadable."""
    gd = git_dir()
    if gd is None:
        return None
    found = []
    for marker, why in IN_PROGRESS_MARKERS:
        if os.path.exists(os.path.join(gd, marker)):
            found.append((marker, why))
    return found


def unmerged_paths():
    rc, out, err = git('diff', '--name-only', '--diff-filter=U')
    if rc != 0:
        return None
    return [l for l in out.split('\n') if l.strip()]


def head_subject():
    rc, out, _ = git('log', '-1', '--format=%s')
    return out if rc == 0 else None


def local_only_subjects():
    """Subjects of commits on HEAD and not on any remote branch.

    SUBJECTS, NOT SHAS, and that is the load-bearing choice. A rebase rewrites
    every sha it touches, so a sha captured before the loop matches nothing
    after it and the guard would fail OPEN at exactly the moment it is needed.
    The subject survives a rebase; it is also what a human reads to notice the
    problem, which is how this near-miss was actually caught.
    """
    # `HEAD` IS EXPLICIT AND THAT IS NOT COSMETIC. `git log --not --remotes`
    # with no positive rev has nothing to walk FROM and lists nothing -- it
    # exits 0 with empty output, so the first version of this returned an empty
    # safe-set and the guard refused every amend forever. It failed in the safe
    # direction, which is why the fixture arms never noticed: they were
    # checking the decision model while the live function was broken. Found by
    # running the tool against a real local commit instead of a fixture.
    rc, out, err = git('log', 'HEAD', '--format=%s', '--not', '--remotes')
    if rc != 0:
        return None
    return [l for l in out.split('\n') if l.strip()]


def capture(write=True):
    subs = local_only_subjects()
    if subs is None:
        return None
    if write:
        try:
            io.open(STATE_FILE, 'w', encoding='utf-8').write(
                json.dumps({'safe_subjects': subs}, ensure_ascii=False))
        except Exception:
            return None
    return subs


def captured_subjects():
    """The set recorded by --capture, or None if there is none.

    None means NO CAPTURE WAS TAKEN, which is refusal 3 -- not permission. An
    empty list would mean "captured, and nothing was local", which is a
    different answer and also refuses.
    """
    if not os.path.isfile(STATE_FILE):
        return None
    try:
        return json.load(io.open(STATE_FILE, encoding='utf-8')).get('safe_subjects')
    except Exception:
        return None


def amend_safety():
    """(safe, reasons). `safe` is True only if every check could be RUN and
    every one passed. A check that could not run is a refusal with its own
    reason, never a silent pass (PR 1.11)."""
    reasons = []

    ops = operation_in_progress()
    if ops is None:
        reasons.append('COULD NOT READ the git directory, so whether an '
                       'operation is in progress is UNKNOWN. Refusing.')
    else:
        for marker, why in ops:
            reasons.append('%s (.git/%s exists). HEAD is the last commit the '
                           'operation applied, which may be ANOTHER SESSION\'S '
                           'commit -- amending it rewrites their work with your '
                           'changes and their message.' % (why.upper(), marker))

    um = unmerged_paths()
    if um is None:
        reasons.append('COULD NOT LIST unmerged paths. Refusing.')
    elif um:
        reasons.append('%d UNMERGED PATH(S): %s. `git add -A` would stage the '
                       'conflict markers and the amend would commit them as a '
                       'fix.' % (len(um), ', '.join(um[:6])))

    subj = head_subject()
    captured = captured_subjects()
    if subj is None:
        reasons.append('COULD NOT READ the HEAD subject. Refusing.')
    elif captured is None:
        reasons.append('NO CAPTURE WAS TAKEN. Run `--capture` before the loop '
                       'so this tool knows which commits are yours to amend. '
                       'An uncaptured state is not permission.')
    elif subj not in captured:
        reasons.append('HEAD IS NOT ONE OF YOUR COMMITS. Its subject is %r, '
                       'which was not local-only when --capture ran. This is '
                       'the exact near-miss: a rebase left another session\'s '
                       'rewritten commit at HEAD.' % subj[:90])

    rc, out, _ = git('branch', '--remotes', '--contains', 'HEAD')
    if rc != 0:
        reasons.append('COULD NOT CHECK whether HEAD is published. Refusing.')
    elif out.strip():
        reasons.append('HEAD IS ALREADY ON A REMOTE BRANCH (%s). Amending a '
                       'published commit needs a force push, which this repo '
                       'denies.' % out.strip().replace('\n', ', ')[:90])

    return (not reasons), reasons


def regenerate():
    """Re-derive the generated documents. PR 2.5: a conflict in a DERIVED
    document is resolved by re-deriving it, never by merging text."""
    done = []
    for doc, gen in GENERATED:
        if not os.path.isfile(os.path.join(REPO, gen)):
            done.append((gen, 'MISSING -- not run'))
            continue
        p = subprocess.run([sys.executable, gen], cwd=REPO, capture_output=True)
        done.append((gen, 'ok' if p.returncode == 0 else 'exit %d' % p.returncode))
    return done


# ── THE REGISTER RE-SEAT, AND THE LIVELOCK IT CAUSED ──────────────────────
# ROOT CAUSE, found 2026-09-29 after NINE consecutive commits in one branch did
# nothing but this:
#
#   1. this loop rebases;
#   2. .githooks/post-rewrite re-seats the register's cited shas onto the ones
#      the rebase just rewrote, writes the file, and CORRECTLY refuses to commit
#      on anybody's behalf -- leaving the tree dirty;
#   3. the regenerate step below stages only GENERATED, so the register stays
#      dirty, and amend_safety() is right to refuse a dirty tree;
#   4. the push loses the race, the loop rebases again, and step 2 repeats.
#
# NOTHING IN THE CHAIN IS WRONG ON ITS OWN. The hook is right not to commit, the
# allowlist is right not to sweep, and the amend guard is right to refuse. What
# was missing is that a re-seat is an EXPECTED, SELF-CONTAINED artefact of the
# rebase this loop just performed -- so this loop is the thing that has to fold
# it in, and until it did there was no fixed point.
#
# FOLDED IN ONLY WHEN IT IS PROVABLY A RE-SEAT. Two independent conditions, and
# both must hold: the file still parses and passes its own --check, AND every
# changed line in the diff is a `"commit":` line. Anything else -- a new record,
# an edited summary, a merge artefact -- is left exactly where it is and named,
# because folding an unknown change into somebody's amended commit is the
# `git add -A` failure this tool exists to prevent, arriving by a different door.
LEDGER = 'docs/defect-density-register.json'


def reseat_only():
    """(True, '') if the ledger's working-tree change is nothing but shas.

    Returns (False, reason) otherwise -- including when it cannot tell, because
    could-not-tell is not permission to stage somebody's unreviewed edit.
    """
    rc, porc, _ = git('status', '--porcelain', '--', LEDGER)
    if rc != 0:
        return False, 'git status could not read %s' % LEDGER
    if not porc.strip():
        return False, 'no change to fold'
    rc2, diff, _ = git('diff', '--unified=0', '--', LEDGER)
    if rc2 != 0 or not diff.strip():
        return False, 'the change is staged or unreadable as a diff, not a '                      'plain working-tree edit'
    for line in diff.split(chr(10)):
        if not line or line[0] not in '+-':
            continue
        if line[:3] in ('+++', '---'):
            continue
        if '"commit"' not in line:
            return False, ('a changed line is not a commit citation, so this is '
                           'not a re-seat: ' + line.strip()[:90])
    chk = subprocess.run([sys.executable,
                          os.path.join(REPO, 'tools', 'defect_register.py'),
                          '--check'], cwd=REPO, capture_output=True)
    if chk.returncode != 0:
        return False, 'defect_register.py --check does not pass on the edited file'
    return True, ''


def selftest():
    out, bad = [], 0

    def arm(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + detail))
        if not ok:
            bad += 1

    # ── FIXTURES FOR THE REFUSAL LOGIC, so the arms mean the same thing in a
    # clean tree as in a broken one. The real tree is ALSO checked below, but a
    # suite that only ever runs on a clean checkout can never see the refusal
    # fire, which is the only behaviour that matters here.
    def decide(ops, unmerged, subject, captured, remotes):
        """The same decision amend_safety() makes, from injected inputs."""
        r = []
        if ops is None:
            r.append('ops unknown')
        else:
            r += ['op:' + m for m, _ in ops]
        if unmerged is None:
            r.append('unmerged unknown')
        elif unmerged:
            r.append('unmerged')
        if subject is None:
            r.append('subject unknown')
        elif captured is None:
            r.append('no capture')
        elif subject not in captured:
            r.append('not mine')
        if remotes is None:
            r.append('remotes unknown')
        elif remotes:
            r.append('published')
        return (not r), r

    arm('a clean tree with a captured local commit is SAFE',
        decide([], [], 'fix(x): mine', ['fix(x): mine'], '')[0],
        'the guard refuses a state it should allow, which means the loop can '
        'never amend and every race ends in a manual fix')

    arm('a MID-REBASE tree is refused -- the near-miss itself',
        not decide([('rebase-merge', 'x')], [], 'fix(x): mine',
                   ['fix(x): mine'], '')[0],
        'THIS IS THE ONE. An interactive rebase in progress must refuse.')
    arm('...and the APPLY form too, which is what actually fired',
        not decide([('rebase-apply', 'x')], [], 'fix(x): mine',
                   ['fix(x): mine'], '')[0],
        'a guard that checks only rebase-merge walks straight through a '
        'non-interactive rebase')
    for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'BISECT_LOG'):
        arm('a tree with ' + marker + ' is refused',
            not decide([(marker, 'x')], [], 'm', ['m'], '')[0])

    arm('a CONFLICTED tree is refused even with no operation marker',
        not decide([], ['docs/X.md'], 'm', ['m'], '')[0],
        '`git add -A` on a conflicted tree stages the conflict markers')

    arm('ANOTHER SESSION\'S commit at HEAD is refused',
        not decide([], [], 'docs(active-work): cody -- q13',
                   ['fix(x): mine'], '')[0],
        'the subject at HEAD is not one this session created and the amend '
        'would rewrite it')
    arm('NO CAPTURE is refused -- an uncaptured state is not permission',
        not decide([], [], 'fix(x): mine', None, '')[0])
    arm('an EMPTY capture is refused, and is not the same as no capture',
        not decide([], [], 'fix(x): mine', [], '')[0],
        'an empty safe-set means nothing was local when capture ran, so '
        'nothing at HEAD can be yours')
    arm('a PUBLISHED commit at HEAD is refused',
        not decide([], [], 'fix(x): mine', ['fix(x): mine'], 'origin/main')[0])

    # COULD-NOT-TELL IS REFUSAL, not a pass (PR 1.11).
    arm('an unreadable git dir is REFUSED, not treated as clean',
        not decide(None, [], 'm', ['m'], '')[0])
    arm('an unreadable unmerged list is REFUSED',
        not decide([], None, 'm', ['m'], '')[0])
    arm('an unreadable remote-contains check is REFUSED',
        not decide([], [], 'm', ['m'], None)[0])

    # ── THE CONTROL. Without it every `not decide(...)` above is satisfied by
    # a decide() that refuses everything, including the clean case -- which
    # would make this a guard that never lets the loop run and passes its own
    # suite while doing it.
    arm('CONTROL -- decide() discriminates rather than always refusing',
        decide([], [], 'm', ['m'], '')[0] and not decide([], [], 'm', ['m'], 'o')[0],
        'decide() returns the same verdict for a safe and an unsafe state')

    # ── AND THE REAL IMPLEMENTATION IS EXERCISED, not just the model of it.
    # A fixture-only suite proves the LOGIC and nothing about the code that
    # ships -- the two could disagree completely.
    live_safe, live_reasons = amend_safety()
    arm('amend_safety() runs against the real tree and returns a reason for '
        'every refusal',
        isinstance(live_safe, bool) and (live_safe or len(live_reasons) > 0),
        'amend_safety() refused with NO reason given, which is a refusal '
        'nobody can act on')
    ops = operation_in_progress()
    arm('operation_in_progress() reads the real .git directory',
        ops is not None,
        'it returned None -- the git directory could not be read, so the '
        'first refusal cannot be evaluated at all')

    # ── THE ARM THAT THE FIXTURES COULD NOT PROVIDE, AND THE BUG IT FOUND ──
    # local_only_subjects() was `git log --format=%s --not --remotes` with no
    # positive rev -- which has nothing to walk from, exits 0, and prints
    # nothing. The safe-set came back EMPTY, so the guard refused every amend
    # forever. Every fixture arm above still passed, because they exercise the
    # decision model and this is the input to it. A guard that always refuses
    # passes a suite built out of refusals.
    subs = local_only_subjects()
    arm('local_only_subjects() can be READ at all',
        subs is not None,
        'it returned None -- git log failed, so the safe-set is unknown')
    rc_h, head_sha, _ = git('rev-parse', 'HEAD')
    rc_r, on_remote, _ = git('branch', '--remotes', '--contains', 'HEAD')
    if subs is not None and rc_h == 0 and rc_r == 0:
        if on_remote.strip():
            # HEAD is published: local-only is legitimately empty and the arm
            # would be asserting the wrong thing. Say so rather than pass
            # silently -- a skipped arm that prints "ok" is the shape this
            # whole file is about.
            out.append('  --   local_only_subjects() non-empty: NOT CHECKED, '
                       'HEAD is published so an empty set is correct here. Run '
                       'this selftest with an unpushed commit to exercise it.')
        else:
            arm('...and it FINDS the unpublished commit at HEAD',
                head_subject() in (subs or []),
                'HEAD is not on any remote branch, so its subject %r must be in '
                'the local-only set -- it came back as %r. An empty or wrong set '
                'makes the guard refuse every amend, which looks like caution '
                'and is a broken tool.' % (head_subject(), subs))
    return out, bad


# ── THE LOOP COULD NOT FIX THE ONE FAILURE IT IS NAMED FOR ─────────────────
# Found 2026-10-05 by using it. This whole block used to live INSIDE
# `if behind > 0:`, so it only ran when the rebase half had something to do.
# Observed both ways in one session:
#
#   behind 1 -> regenerated, amended, PUSHED.
#   behind 0 -> six consecutive attempts, NO regeneration, six identical
#               "error: failed to push some refs" lines.
#
# The push had been refused for three STALE GENERATED DOCUMENTS -- exactly
# what `regenerate()` fixes -- and the loop never called it, because nothing
# was behind. A retry loop whose remedy is gated on an unrelated condition is
# a loop that retries the same failure until it runs out of attempts.
#
# Extracted here so it can be called from BOTH paths: after a successful
# rebase, and after a push refusal that names a generated document.
def _regenerate_and_fold():
    """Regenerate the derived documents and fold them into your own commit.

    Returns (folded, reason). `folded` is True only when an amend happened.
    Every refusal path returns False with a reason rather than raising: this
    is called from inside a retry loop and a crash here strands a push.
    """
    for gen_name, status in regenerate():
        if status != 'ok':
            print('  %s: %s' % (gen_name, status))
    rc2, porc, _ = git('status', '--porcelain')
    if rc2 == 0 and porc.strip():
        safe, reasons = amend_safety()
        if not safe:
            print('REFUSING TO AMEND:', file=sys.stderr)
            for r in reasons:
                print('  - %s' % r, file=sys.stderr)
            return False, 'amend refused by the guard'
        # ── THE ALLOWLIST, BECAUSE THIS LINE WAS `git add -A` ────────
        # This tool exists to replace the hand-written loop whose own
        # header, forty lines up, records `git add -A` staging conflict
        # markers on a conflicted tree. It then did the same thing here.
        # The regenerate step has NO business staging anything except
        # the documents it just regenerated, and it already knows their
        # names: GENERATED is right there.
        #
        # `git add -A` at this moment folds whatever happens to be in
        # the tree into somebody's amended commit. On 2026-09-28 that
        # shape swept a GitHub PAT into a commit in this repo; the push
        # gate caught it, which is luck rather than design. Conflict
        # markers twice and a credential once, all from the same
        # one-liner.
        #
        # ANYTHING ELSE IS NAMED AND NOT STAGED, rather than refused.
        # A refusal here strands a push mid-rebase, and the whole point
        # of an allowlist is that the unexpected file simply does not
        # get committed -- saying nothing about it is the part that
        # would make this a silent narrowing.
        for _doc, _gen in GENERATED:
            git('add', '--', _doc)
        # THE RE-SEAT, FOLDED IN -- see reseat_only() above for why this
        # is the step that has to do it and why it is conditional.
        _rs, _why = reseat_only()
        if _rs:
            git('add', '--', LEDGER)
            print('  re-seated register citations folded in '
                  '(commit fields only, --check passes)')
        elif _why not in ('no change to fold',):
            print('  %s NOT folded in: %s' % (LEDGER, _why))
        rc3, porc3, _ = git('status', '--porcelain')
        _left = [ln for ln in (porc3 or '').split('\n')
                 if ln.strip() and ln[:2] != '  '
                 and not any(ln.endswith(_d) for _d, _g in GENERATED)]
        # Only report paths that are still UNSTAGED or UNTRACKED. A file
        # already in the index is the caller's deliberate act -- often
        # tools/sairn_rebase_resolve.py's merged ledger -- and belongs in
        # the commit being amended.
        _unstaged = [ln for ln in _left
                     if ln[1:2] in ('M', 'D', '?') or ln[:2] == '??']
        if _unstaged:
            print('  NOT STAGED by the regenerate step -- this step '
                  'stages only the documents it regenerates:')
            for ln in _unstaged:
                print('    %s' % ln)
        arc, _, aerr = git('commit', '--amend', '--no-edit')
        if arc != 0:
            print('amend failed: %s' % aerr, file=sys.stderr)
            return False, 'amend failed: %s' % (aerr or '')[:120]
        return True, 'folded'
    return False, 'nothing to fold -- the generated documents already match'


def cmd_loop(attempts):
    cap = capture()
    if cap is None:
        print('COULD NOT CAPTURE the local-only subject set. Refusing to run '
              'the loop -- without it the amend guard cannot tell your commits '
              'from anybody else\'s.', file=sys.stderr)
        return 3
    print('captured %d local-only subject(s) as safe to amend' % len(cap))
    for i in range(1, attempts + 1):
        git('fetch', '-q', 'origin')
        rc, behind, _ = git('rev-list', '--count', 'HEAD..origin/main')
        behind = int(behind or '0') if rc == 0 else -1
        print('attempt %d: behind %s' % (i, behind))
        if behind > 0:
            rrc, _, rerr = git('rebase', 'origin/main')
            if rrc != 0:
                # STOP. Do not resolve, do not amend. The tree is exactly the
                # state the guard exists for, and a loop that tries to fix it
                # is how the near-miss happened.
                um = unmerged_paths() or []
                print('REBASE STOPPED. %d unmerged path(s): %s'
                      % (len(um), ', '.join(um) or '(none listed)'),
                      file=sys.stderr)
                gen = set(d for d, _ in GENERATED)
                if um and set(um) <= gen:
                    print('  Every conflict is in a GENERATED document. '
                          'Resolve by RE-DERIVING (PR 2.5), not by merging '
                          'text:', file=sys.stderr)
                    for d, g in GENERATED:
                        if d in um:
                            print('    git checkout --ours -- %s && python %s'
                                  % (d, g), file=sys.stderr)
                    # BY NAME, NOT `git add -A`. This tool refuses to run a
                    # loop that stages everything and then printed an
                    # instruction to do exactly that -- to a human, mid-rebase,
                    # which is the one moment the tree holds things nobody
                    # meant to commit.
                    print('  then, staging ONLY those documents by name:',
                          file=sys.stderr)
                    print('    git add -- %s'
                          % ' '.join(d for d, _ in GENERATED if d in um),
                          file=sys.stderr)
                    print('    git rebase --continue', file=sys.stderr)
                else:
                    print('  At least one conflict is NOT a generated '
                          'document. That is a human read, not a loop.',
                          file=sys.stderr)
                print('  NOTHING WAS AMENDED. HEAD is mid-rebase and may be '
                      'another session\'s commit.', file=sys.stderr)
                return 3
            _f, _why = _regenerate_and_fold()
            if _f:
                print('  regenerated documents folded into your own commit')
        prc, pout, perr = git('push', 'origin', 'main')
        if prc == 0:
            print('PUSHED')
            return 0
        # ── THE REFUSAL WAS PRINTED FROM THE WRONG END ─────────────────────
        # This was `tail[-6:]`. The push gate writes its explanation at the
        # TOP -- the `Blocked:` header, then the named documents and the
        # command that fixes each -- and git's generic
        # `error: failed to push some refs` at the BOTTOM. So the last six
        # lines are reliably the least informative six, and six attempts
        # produced six identical useless lines while the real reason sat in
        # the part that was discarded. Observed 2026-10-05: the three stale
        # generated documents were visible only on a bare `git push`.
        blob = (perr or '') + ('\n' + pout if pout else '')
        lines = [l for l in blob.split('\n') if l.strip()]
        print('  push refused:')
        if not lines:
            print('    (git said nothing on either stream -- that is itself '
                  'the finding; a refusal with no text is not diagnosable)')
        # HEAD-ANCHORED, and the lines that carry a remedy are never dropped.
        _keep = [l for l in lines
                 if l.lstrip().startswith(('Blocked:', 'fix:', 'FAIL', '!'))
                 or ' -- ' in l or l.lstrip().startswith('python ')]
        for l in lines[:14]:
            print('    %s' % l)
        if len(lines) > 14:
            print('    ... %d more line(s); the ones carrying a remedy:'
                  % (len(lines) - 14))
            for l in _keep[:8]:
                if l not in lines[:14]:
                    print('    %s' % l)

        # ── AND NOW ACT ON IT, which is the half that was missing ──────────
        # A refusal naming a generated document is the exact failure
        # `regenerate()` fixes, and the loop used to be unable to reach it
        # unless something was behind. Try once per attempt.
        if any(_d in blob for _d, _g in GENERATED):
            print('  the refusal names a GENERATED document -- regenerating '
                  'and folding in, which this loop could not do before '
                  '2026-10-05 unless it was also behind:')
            _f, _why = _regenerate_and_fold()
            print('    %s' % ('folded; retrying' if _f
                              else 'not folded: %s' % _why))
    print('gave up after %d attempt(s). Nothing was forced.' % attempts,
          file=sys.stderr)
    return 1


def main(argv):
    if '--selftest' in argv:
        print('PUSH RETRY GUARD -- selftest')
        out, bad = selftest()
        for l in out:
            print(l)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    if '--capture' in argv:
        subs = capture()
        if subs is None:
            print('COULD NOT CAPTURE.', file=sys.stderr)
            return 3
        print('captured %d local-only subject(s):' % len(subs))
        for s in subs:
            print('  %s' % s[:100])
        return 0

    if '--check' in argv or '--amend-guard' in argv:
        safe, reasons = amend_safety()
        if safe:
            print('AMEND IS SAFE: no operation in progress, no unmerged paths, '
                  'HEAD is one of your captured local-only commits, and it is '
                  'not published.')
            return 0
        print('AMEND IS REFUSED -- %d reason(s):' % len(reasons), file=sys.stderr)
        for r in reasons:
            print('  - %s' % r, file=sys.stderr)
        return 3

    if '--loop' in argv:
        n = 3
        if '--attempts' in argv:
            try:
                n = int(argv[argv.index('--attempts') + 1])
            except Exception:
                pass
        return cmd_loop(n)

    print(__doc__.strip())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
