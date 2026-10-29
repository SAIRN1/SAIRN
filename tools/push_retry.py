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
        # exit 5: STOPPED on a deterministic refusal (the push gate, or text
        # nobody classified) -- see classify_refusal(); only remote races retry
    python tools/push_retry.py --selftest           # fixtures, both directions
"""
import contextlib
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

# ── ACCUMULATED STATE: files where a RECORD CAN GO MISSING AND NOTHING SAYS SO
#
# A GENERATED document is safe to resolve with `--ours` because it is
# re-derived from the repo one line later; whatever text survived the conflict
# is overwritten. These are the opposite. Each is an append-only ledger whose
# whole value is that nothing has been dropped from it, and a rebase can lose
# an entry three ways, all of them silent:
#
#   * `git checkout --ours` DURING A REBASE TAKES THE UPSTREAM SIDE, not
#     yours. The word means the opposite of what it reads like here, and the
#     advice this file prints for GENERATED documents is correct for them and
#     catastrophic for these.
#   * git can AUTO-MERGE two JSON edits without a conflict and still lose one,
#     when both sessions appended near the same line.
#   * `git rebase --skip`, or an abandoned commit, drops the entry with no
#     diff anyone reads.
#
# MEASURED 2026-10-05, not hypothetical: a Tier A review obligation recorded
# by `tier_a_review_gate.py --open` was written, committed, and then silently
# removed by an inline fetch/rebase/push loop resolving a conflict with
# `--ours`. The push gate then refused the push for a missing obligation that
# had in fact been created -- and the only reason it was noticed is that the
# refusal was read rather than retried.
#
# (path, key holding the list). The COUNT of that list must never fall across
# a rebase this tool performs.
ACCUMULATED = [
    ('docs/tier-a-reviews.json', 'records'),
    ('docs/defect-density-register.json', 'records'),
    ('docs/first-article-inspections.json', 'inspections'),
    ('docs/known-red-suites.json', 'entries'),
    ('docs/report-only-reachability.json', 'entries'),
    ('docs/out-of-service-controls.json', 'entries'),
    ('.claude/claims/cc.json', 'claims'),
    ('.claude/claims/cody.json', 'claims'),
    ('.claude/claims/fourth.json', 'claims'),
    ('.claude/claims/hank.json', 'claims'),
    ('.claude/claims/hover.json', 'claims'),
    ('.claude/claims/cloud.json', 'claims'),
]


def accumulated_counts():
    """{path: n} for every ACCUMULATED ledger that can be read RIGHT NOW.

    A file that cannot be read is OMITTED rather than recorded as 0 -- a
    missing key would otherwise look like a catastrophic drop on the next
    comparison and a real drop would be indistinguishable from a parse error.
    Unreadable is reported separately by the caller.
    """
    out, unreadable = {}, []
    for rel, key in ACCUMULATED:
        p = os.path.join(REPO, rel)
        if not os.path.isfile(p):
            continue
        try:
            d = json.load(io.open(p, encoding='utf-8'))
            v = d.get(key)
            if isinstance(v, list):
                out[rel] = len(v)
            else:
                unreadable.append(rel + ' (no list at key %r)' % key)
        except Exception as e:
            unreadable.append('%s (%s)' % (rel, str(e)[:60]))
    return out, unreadable


def accumulated_losses(before, after):
    """[(path, before, after)] for every ledger that SHRANK. Growth is fine --
    another clone appending is the normal case and is why this compares counts
    rather than requiring equality."""
    return [(p, before[p], after[p])
            for p in sorted(before)
            if p in after and after[p] < before[p]]

STATE_FILE = os.path.join(REPO, '.git', 'push_retry_safe_subjects.json')


def git(*args, timeout=120):
    """(exit, stdout, stderr). Never raises -- the caller decides what a
    failure means, and for this tool it usually means REFUSE.

    `timeout=None` for a PUSH (b61). The push gate writes mutants into tracked
    files and restores them in `finally`; 120 s killed a push whose gate runs
    for minutes, and a kill skips the restore. tools/push_timeout_guard.py
    --scan flags any push through this helper that does not pass None."""
    try:
        p = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                           timeout=timeout)
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


# ── THE PUSH GATE'S SCRUTINY WRITE-BACK, AND THE COMMIT PER LOST RACE (b31) ──
# The gate appends rows to docs/scrutiny-flags.json on EVERY push attempt and
# leaves the tree dirty. The hand-written loop committed whatever the tree held
# each round, so four lost races made four near-identical commits over one
# file (b30 squashed them by hand; b29 was refused by the duplicate-subject
# gate for the same loop).
#
# THE ONE-LINE CONCEPT: the write-back is bookkeeping ABOUT the commits being
# pushed, so it gets exactly one bookkeeping commit that every later round
# AMENDS -- never a new commit per round, and never folded into a work commit,
# because a work commit's sha IS the row key and amending it would orphan the
# row the gate just wrote.
SCRUTINY_FILE = 'docs/scrutiny-flags.json'
BOOKKEEPING_PREFIX = 'chore(gate-bookkeeping '
# The loop's own derived-docs commit (hank b64): regenerated documents go here,
# never into the author's commit, so the author's patch-ids survive a rebase.
REGEN_PREFIX = 'chore(derived-docs '


def scrutiny_append_only():
    """(True, '') if the working-tree change to the ledger only ADDS rows.

    Same discipline as reseat_only(): could-not-tell is (False, reason), never
    permission to stage somebody's unreviewed edit. Every row at HEAD must
    survive unchanged and every other top-level key must be equal.
    """
    rc, head, _ = git('show', 'HEAD:' + SCRUTINY_FILE)
    if rc != 0:
        return False, 'HEAD has no %s to compare against' % SCRUTINY_FILE
    try:
        old = json.loads(head)
        new = json.load(io.open(os.path.join(REPO, SCRUTINY_FILE),
                                encoding='utf-8'))
        old_rows, new_rows = old['flags'], new['flags']
    except Exception as exc:
        return False, '%s does not parse as a ledger: %s' % (SCRUTINY_FILE, exc)
    if {k: v for k, v in old.items() if k != 'flags'} != \
            {k: v for k, v in new.items() if k != 'flags'}:
        return False, 'a top-level key other than "flags" changed'
    key = lambda r: json.dumps(r, sort_keys=True)
    missing = set(map(key, old_rows)) - set(map(key, new_rows))
    if missing:
        return False, '%d row(s) at HEAD were changed or removed' % len(missing)
    return True, ''


def fold_scrutiny():
    """Fold the gate's write-back into the ONE bookkeeping commit.

    Returns (folded, reason). Never raises: this runs inside a retry loop.
    """
    rc, porc, _ = git('status', '--porcelain', '--', SCRUTINY_FILE)
    if rc != 0:
        return False, 'git status could not read %s' % SCRUTINY_FILE
    if not porc.strip():
        return False, 'nothing'
    ok, why = scrutiny_append_only()
    if not ok:
        return False, '%s NOT folded: %s' % (SCRUTINY_FILE, why)
    subj = head_subject() or ''
    # A bookkeeping commit that is ALREADY PUBLISHED (the previous push landed
    # it) is history, not this round's commit: amending it needs a force push,
    # so the rows written by the push that published it start a new one.
    _rc, _pub, _ = git('branch', '--remotes', '--contains', 'HEAD')
    if _rc != 0:
        return False, 'could not check whether HEAD is published'
    if subj.startswith(BOOKKEEPING_PREFIX) and not _pub.strip():
        safe, reasons = amend_safety()
        if not safe:
            return False, 'amend refused by the guard: ' + '; '.join(reasons)[:200]
        arc, _, aerr = git('commit', '--amend', '--no-edit', '--',
                           SCRUTINY_FILE)
        if arc != 0:
            return False, 'amend failed: %s' % (aerr or '')[:120]
        return True, 'amended the bookkeeping commit'
    ops, um = operation_in_progress(), unmerged_paths()
    if ops is None or um is None or ops or um:
        return False, 'an operation is in progress or the tree is unreadable'
    rc, tip, _ = git('rev-parse', '--short', 'HEAD')
    if rc != 0:
        return False, 'could not resolve HEAD'
    # THE TIP SHA IS IN THE SUBJECT so a later batch's bookkeeping commit never
    # collides with this one under the duplicate-subject gate.
    new_subj = ("%s%s): the push gate's own scrutiny rows"
                % (BOOKKEEPING_PREFIX, tip))
    crc, _, cerr = git('commit', '-m', new_subj, '-m',
                       'Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>',
                       '--', SCRUTINY_FILE)
    if crc != 0:
        return False, 'commit failed: %s' % (cerr or '')[:120]
    # Registered as yours, or the guard refuses every later amend of it.
    subs = captured_subjects() or []
    try:
        io.open(STATE_FILE, 'w', encoding='utf-8').write(
            json.dumps({'safe_subjects': subs + [new_subj]}, ensure_ascii=False))
    except Exception:
        return True, 'created the bookkeeping commit, but could not register ' \
                     'it as amendable'
    return True, 'created the bookkeeping commit'


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

    # ── b31: THE SCRUTINY WRITE-BACK IS AMENDED, NOT RECOMMITTED -- driven on a
    # real scratch repo, because the defect was a commit COUNT and a fixture of
    # the decision model cannot see a count.
    import shutil
    import tempfile
    global REPO, STATE_FILE
    saved = (REPO, STATE_FILE)
    tmp = tempfile.mkdtemp(prefix='push_retry_selftest_')
    try:
        REPO = tmp
        os.makedirs(os.path.join(tmp, 'docs'))
        STATE_FILE = os.path.join(tmp, '.git', 'push_retry_safe_subjects.json')
        sf = os.path.join(tmp, SCRUTINY_FILE)

        def put(rows, extra=None):
            d = {'merge_policy': 'x', 'flags': rows}
            d.update(extra or {})
            io.open(sf, 'w', encoding='utf-8').write(json.dumps(d, indent=1))

        def count():
            return int(git('rev-list', '--count', 'HEAD')[1] or '0')

        git('init', '-q')
        git('config', 'user.email', 'a@b.c')
        git('config', 'user.name', 'selftest')
        put([{'sha': 'a1', 'path': 'p'}])
        git('add', '-A')
        git('commit', '-q', '-m', 'work: mine')
        capture()
        base = count()

        put([{'sha': 'a1', 'path': 'p'}, {'sha': 'b2', 'path': 'p'}])
        f1, w1 = fold_scrutiny()
        arm('round 1 creates ONE bookkeeping commit',
            f1 and count() == base + 1
            and head_subject().startswith(BOOKKEEPING_PREFIX), w1)
        subj1 = head_subject()

        put([{'sha': 'a1', 'path': 'p'}, {'sha': 'b2', 'path': 'p'},
             {'sha': 'c3', 'path': 'p'}])
        f2, w2 = fold_scrutiny()
        arm('round 2 AMENDS it -- the commit count does not move',
            f2 and count() == base + 1 and head_subject() == subj1,
            'count %d -> %d: a lost race made a new commit, which is the '
            'defect b30 squashed by hand' % (base + 1, count()))
        rc_s, shown, _ = git('show', 'HEAD:' + SCRUTINY_FILE)
        arm('...and the amended commit carries all three rows',
            rc_s == 0 and len(json.loads(shown)['flags']) == 3)

        put([{'sha': 'b2', 'path': 'p'}])
        f3, w3 = fold_scrutiny()
        arm('a change that REMOVES a row is NOT folded, and says why',
            not f3 and 'changed or removed' in w3 and count() == base + 1, w3)
        put([{'sha': 'a1', 'path': 'p'}, {'sha': 'b2', 'path': 'p'},
             {'sha': 'c3', 'path': 'p'}], {'merge_policy': 'y'})
        f4, w4 = fold_scrutiny()
        arm('a change to another top-level key is NOT folded',
            not f4 and 'top-level' in w4, w4)
        io.open(sf, 'w', encoding='utf-8').write('<<<<<<< not json')
        f5, w5 = fold_scrutiny()
        arm('an unparseable file is NOT folded -- could-not-tell is not a pass',
            not f5 and 'parse' in w5, w5)
        git('checkout', '--', SCRUTINY_FILE)
        f6, w6 = fold_scrutiny()
        arm('CONTROL -- a clean ledger folds nothing',
            not f6 and w6 == 'nothing', w6)

        # A PUBLISHED bookkeeping commit is not amendable; the next push's rows
        # start a NEW one (count +1), and the subject differs (tip7 changes).
        git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        before, subj_pub = count(), head_subject()
        put([{'sha': 'a1', 'path': 'p'}, {'sha': 'b2', 'path': 'p'},
             {'sha': 'c3', 'path': 'p'}, {'sha': 'd4', 'path': 'p'}])
        f7, w7 = fold_scrutiny()
        arm('a PUBLISHED bookkeeping commit is not amended -- a new one starts',
            f7 and count() == before + 1 and head_subject() != subj_pub
            and head_subject().startswith(BOOKKEEPING_PREFIX), w7)
    finally:
        REPO, STATE_FILE = saved
        shutil.rmtree(tmp, ignore_errors=True)

    # ── THE REFUSAL CLASSIFIER (cc b32), on the texts the gate and git really
    # print -- copied from the b31 refusals, not composed for the test.
    tier_a = ('Blocked: this push changes code serving a Tier A resource and no\n'
              'error: failed to push some refs to \'https://github.com/SAIRN1/SAIRN.git\'')
    cnr = ('Blocked: the path-scope check could not be run, so this push is unchecked\n'
           '  FileNotFoundError: [WinError 206] The filename or extension is too long\n'
           '(blocked by .githooks/pre-push -> tools/sairn_push_gate_hook.py --pre-push)')
    esc = 'ESCALATING: this is refusal 3 for tip b2b02bbd07bd, and the cap is 2.'
    gen = ('Blocked: 1 generated document(s) are stale: docs/TOOLING-INVENTORY.md\n'
           'error: failed to push some refs')
    race = (' ! [rejected]          main -> main (fetch first)\n'
            'error: failed to push some refs')
    lock = (" ! [remote rejected]   main -> main (cannot lock ref 'refs/heads/main': "
            "is at 8eeabd1c but expected df8118c9)")
    net = 'fatal: unable to access \'https://github.com/SAIRN1/SAIRN.git/\': Could not resolve host: github.com'
    arm('a Tier A gate refusal is "gate" -- STOP, never retried',
        classify_refusal(tier_a) == 'gate', classify_refusal(tier_a))
    arm('a gate check that COULD NOT RUN is "gate" -- the same range fails the same way',
        classify_refusal(cnr) == 'gate', classify_refusal(cnr))
    arm('the gate\'s own ESCALATING line is "gate"',
        classify_refusal(esc) == 'gate', classify_refusal(esc))
    arm('a gate refusal naming a GENERATED document is "generated" -- the one it can fix',
        classify_refusal(gen) == 'generated', classify_refusal(gen))
    arm('git\'s fetch-first race is "transient"',
        classify_refusal(race) == 'transient', classify_refusal(race))
    arm('git\'s cannot-lock-ref race is "transient"',
        classify_refusal(lock) == 'transient', classify_refusal(lock))
    arm('a network failure is "transient"',
        classify_refusal(net) == 'transient', classify_refusal(net))
    arm('unclassified text is "unknown", and the loop STOPS on it',
        classify_refusal('error: something nobody has seen') == 'unknown'
        and classify_refusal('') == 'unknown',
        classify_refusal('error: something nobody has seen'))
    arm('gate text WINS over the generic git line every gate refusal ends with',
        classify_refusal(tier_a + '\n' + race) == 'gate',
        classify_refusal(tier_a + '\n' + race))
    # cody b47: a PASSING gate's notice names the gate file on a push that
    # edits it. Lines copied from the hook's real stderr on 8aee7e758.
    passing = ('    EXTRA SCRUTINY -- this push changes things that CHECK the work '
               '(criteria 2026-10-06.1)\n'
               '  [WEAKENING] tools/sairn_push_gate_hook.py                       '
               '       push-gate logic\n'
               'Gate-freshness (check 10) NOTICE: the push gate that just ran is NOT '
               'the one on origin/main. It is 1 commit(s) behind on '
               'tools/sairn_push_gate_hook.py.')
    arm('a PASSING gate notice that names the gate file, then a lock race, is '
        '"transient" -- the b46 stop',
        classify_refusal(passing + '\n' + lock) == 'transient',
        classify_refusal(passing + '\n' + lock))
    arm('...and with a fetch-first race too',
        classify_refusal(passing + '\n' + race) == 'transient',
        classify_refusal(passing + '\n' + race))
    arm('...but the same notice beside a real deny is still "gate"',
        classify_refusal(passing + '\n' + cnr) == 'gate',
        classify_refusal(passing + '\n' + cnr))

    # ── AND THE LOOP OBEYS IT: cmd_loop driven with git stubbed, counting
    # pushes. FAILING-FIRST: the pre-b32 loop pushed 4 times on the Tier A text.
    g = globals()
    names = ('git', 'capture', 'fold_scrutiny', '_outgoing_state',
             '_incoming_files', '_log_fast_retry')
    keep = tuple(g[n] for n in names)

    def _drive(blob, state=None, incoming=frozenset(), land_on=None):
        pushes, logged = [], []
        states = iter(state or [])

        def _git(*a, **_k):
            if a[0] == 'push':
                pushes.append('--no-verify' in a)
                if land_on is not None and len(pushes) == land_on:
                    return 0, '', ''
                return 1, '', blob
            if a[0] == 'rev-list':
                return 0, '0', ''
            return 0, '', ''
        g['git'], g['capture'] = _git, (lambda write=True: ['s'])
        g['fold_scrutiny'] = lambda: (False, 'nothing')
        g['_outgoing_state'] = lambda: next(states, (frozenset({'p1'}), {'a.py'}, 'B'))
        g['_incoming_files'] = lambda o, n: set(incoming)
        g['_log_fast_retry'] = lambda *a: logged.append(1)
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                rc = cmd_loop(4)
        finally:
            for n, v in zip(names, keep):
                g[n] = v
        return pushes, rc, len(logged)
    p_gate, rc_gate, _l = _drive(tier_a)
    p_race, rc_race, l_race = _drive(race)
    arm('the LOOP pushes ONCE on a gate refusal and stops (exit 5)',
        len(p_gate) == 1 and rc_gate == 5, 'pushes=%s rc=%s' % (p_gate, rc_gate))
    arm('CONTROL -- the loop still retries a fetch-first race every attempt',
        len(p_race) == 4 and rc_race == 1, 'pushes=%s rc=%s' % (p_race, rc_race))

    # ── C1 (hank b61): after a PASS lost to a race, an unchanged range retries
    # WITHOUT the gate, and every such skip is logged.
    arm('C1 -- full gate first, then 3 FAST retries on an unchanged range; a '
        'REFUSED skip logs nothing (b63: the row dirtied the tree and the next '
        'rebase stopped)', p_race == [False, True, True, True] and l_race == 0,
        'pushes=%s logged=%d' % (p_race, l_race))
    p_land, rc_land, l_land = _drive(race, land_on=2)
    arm('C1 -- a skip that LANDS is logged exactly once',
        p_land == [False, True] and rc_land == 0 and l_land == 1,
        'pushes=%s rc=%s logged=%d' % (p_land, rc_land, l_land))
    p_chg, _rc, l_chg = _drive(race, state=[
        (frozenset({'p%d' % k}), {'a.py'}, 'B') for k in range(4)])
    arm('C1 -- our commits changing between attempts means the FULL gate '
        'every time', p_chg == [False] * 4 and l_chg == 0,
        'pushes=%s logged=%d' % (p_chg, l_chg))
    p_ov, _rc, _l = _drive(race, incoming={'a.py'})
    arm('C1 -- incoming commits touching our file means the FULL gate',
        p_ov == [False] * 4, 'pushes=%s' % p_ov)
    p_gl, _rc, _l = _drive(lock, state=[None] * 4)
    arm('C1 -- an unreadable range is the FULL gate, never a skip',
        p_gl == [False] * 4, 'pushes=%s' % p_gl)
    p_g2, _rc, _l = _drive(tier_a)
    arm('C1 -- a gate refusal never arms a skip (one push, no --no-verify)',
        p_g2 == [False], 'pushes=%s' % p_g2)

    S = (frozenset({'x'}), {'a.py'}, 'B2')
    G = (frozenset({'x'}), 'B1')
    for name, args, want in (
            ('no pass yet', (None, S, set()), False),
            ('unchanged range, disjoint incoming', (G, S, {'b.py'}), True),
            ('our patch-ids changed', ((frozenset({'y'}), 'B1'), S, set()), False),
            ('incoming overlaps ours', (G, S, {'a.py'}), False),
            ('incoming changes the gate hook', (G, S, {'tools/sairn_push_gate_hook.py'}), False),
            ('incoming changes .githooks/', (G, S, {'.githooks/pre-push'}), False),
            ('incoming changes CRITICALITY-TIERS', (G, S, {'docs/CRITICALITY-TIERS.md'}), False),
            ('state unreadable', (G, None, set()), False),
            ('incoming unreadable', (G, S, None), False),
            ('nothing outgoing', ((frozenset(), 'B1'), (frozenset(), set(), 'B2'), set()), False)):
        got = fast_retry_decision(*args)[0]
        arm('C1 decision -- %s -> %s' % (name, 'skip' if want else 'full gate'),
            got == want, 'got %s' % got)

    arm('b65 -- append_only accepts appended rows (CRLF-insensitive)',
        append_only('a\nb\n', 'a\r\nb\r\nc\n'), 'refused an append')
    arm('b65 -- append_only REFUSES an edited or removed row',
        not append_only('a\nb\n', 'a\nX\n') and not append_only('a\nb\n', 'a\n'), 'accepted an edit')
    # ── C1a (hank b64): regenerated docs live in their OWN commit, excluded
    # from the patch-id set, so a pure base move can still take the fast path.
    log = ['a1\tfeat(x): the author\'s change',
           'b2\t' + REGEN_PREFIX + 'a1): regenerated after rebase',
           'c3\t' + BOOKKEEPING_PREFIX + 'a1): the push gate\'s own scrutiny rows',
           'd4\tfix(y): a second authored commit', '']
    arm('C1a -- authored_commits drops the derived-docs and gate-bookkeeping commits',
        authored_commits(log) == ['a1', 'd4'], 'got %s' % authored_commits(log))
    arm('C1a -- CONTROL: an authored subject that merely MENTIONS derived docs is kept',
        authored_commits(['e5\tdocs(z): chore(derived-docs is a phrase here']) == ['e5'],
        'got %s' % authored_commits(['e5\tdocs(z): chore(derived-docs is a phrase here']))
    arm('C1a -- the fold no longer amends the author\'s commit',
        "git('commit', '--amend', '--no-edit')\n        else:" in __import__('inspect').getsource(_regenerate_and_fold)
        or 'REGEN_PREFIX' in __import__('inspect').getsource(_regenerate_and_fold),
        'the regenerate step does not reference REGEN_PREFIX')
    # ── S6 (hank b68): untracked files alone make `status --porcelain`
    # non-empty; with nothing staged the fold must say so, not report a commit
    # failure with an empty error. Driven on a scratch repo, generators stubbed.
    g = globals()
    keep = (REPO, g['regenerate'], g['amend_safety'], g['reseat_only'])
    tmp2 = tempfile.mkdtemp(prefix='push_retry_selftest_s6_')
    try:
        REPO = tmp2
        git('init', '-q')
        git('config', 'user.email', 'a@b.c')
        git('config', 'user.name', 'selftest')
        io.open(os.path.join(tmp2, 'f.txt'), 'w', encoding='utf-8').write('x')
        git('add', '-A')
        git('commit', '-q', '-m', 'work: mine')
        io.open(os.path.join(tmp2, 'stray.txt'), 'w', encoding='utf-8').write('untracked')
        g['regenerate'] = lambda: []
        g['amend_safety'] = lambda: (True, [])
        g['reseat_only'] = lambda: (False, 'no change to fold')
        f7, w7 = _regenerate_and_fold()
        arm('S6 -- untracked files only, nothing staged: "nothing to fold", not an empty commit failure',
            not f7 and w7.startswith('nothing to fold'), w7)
    finally:
        REPO, g['regenerate'], g['amend_safety'], g['reseat_only'] = keep
        shutil.rmtree(tmp2, ignore_errors=True)
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
        # ── INTO ITS OWN COMMIT, NOT OURS (hank b64, Michael's C1a) ─────────
        # Amending the author's commit changed its patch-id on every rebase,
        # so the C1 fast retry (which compares patch-ids) could never fire
        # after a regenerate -- b63 pushes 3 and 4 both fell to the full gate
        # for exactly that. Regenerated documents now live in ONE derived-docs
        # commit on top, amended in place on later attempts, and excluded from
        # the patch-id set by subject (see _outgoing_state).
        # Untracked files alone make the porcelain above non-empty. With
        # nothing staged `git commit` fails with its reason on stdout, which
        # logged "derived-docs commit failed:" and an empty error (hank b67 S6).
        if git('diff', '--cached', '--quiet')[0] == 0:
            return False, 'nothing to fold -- the generated documents already match'
        subj = head_subject() or ''
        _rc, _pub, _ = git('branch', '--remotes', '--contains', 'HEAD')
        if subj.startswith(REGEN_PREFIX) and _rc == 0 and not _pub.strip():
            arc, _, aerr = git('commit', '--amend', '--no-edit')
        else:
            _trc, tip, _ = git('rev-parse', '--short', 'HEAD')
            new_subj = '%s%s): regenerated after rebase' % (REGEN_PREFIX, tip)
            arc, _, aerr = git('commit', '-m', new_subj, '-m',
                               'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
            if arc == 0:
                subs = captured_subjects() or []
                try:
                    io.open(STATE_FILE, 'w', encoding='utf-8').write(
                        json.dumps({'safe_subjects': subs + [new_subj]}, ensure_ascii=False))
                except Exception:                               # noqa: BLE001
                    pass
        if arc != 0:
            print('derived-docs commit failed: %s' % aerr, file=sys.stderr)
            return False, 'derived-docs commit failed: %s' % (aerr or '')[:120]
        return True, 'folded'
    return False, 'nothing to fold -- the generated documents already match'


# ── WHICH REFUSALS ARE WORTH ANOTHER ATTEMPT (cc b32) ─────────────────────
# The loop used to treat EVERY refused push as a lost race and try again. A
# gate refusal is not a race: the pre-push hook decides from the outgoing range,
# the range does not change between attempts, and the gate COUNTS refusals per
# tip -- on 2026-10-20 an inline loop of this shape sent the same Tier A
# refusal four times and the gate escalated at the third. Retrying a
# deterministic refusal changes nothing except the escalation count.
#
# So a refusal is classified by WHO SAID IT:
#   'transient' -- git's own remote-race and transport rejections. The remote
#                  moved or the network blinked; fetch, rebase and try again.
#   'generated' -- a gate refusal naming a GENERATED document. The one gate
#                  refusal this loop can fix itself (regenerate and fold), so
#                  it gets ONE more attempt, and only if the fold happened.
#   'gate'      -- anything else the pre-push gate printed. Deterministic for
#                  this tip: STOP and let a human read it.
#   'unknown'   -- text nobody classified. STOPS too: when retrying costs an
#                  escalation and stopping costs a re-run, unknown goes to stop.
# Gate text is checked BEFORE transient text, because a gate refusal also ends
# in git's generic "failed to push some refs".
#
# ONLY TEXT THE GATE PRINTS WHEN IT DENIES (cody b47). The bare file name
# `sairn_push_gate_hook.py` was a marker too, and a PASSING gate prints it:
# its EXTRA SCRUTINY notice lists `[WEAKENING] tools/sairn_push_gate_hook.py`
# on any push that edits the gate. cody b46 pushed a gate edit twice, the gate
# passed both times (no deny record for either tip in push-retries/), the
# remote moved during the ~85s hook run, and git's race rejection was read as
# "gate" -- STOP, where a fetch-rebase-retry was the remedy. A deny always
# carries `Blocked:` or the `(blocked by .githooks/pre-push ...)` trailer.
_GATE_MARKERS = ('Blocked:', 'blocked by .githooks/pre-push', 'ESCALATING:')
_TRANSIENT_MARKERS = ('(fetch first)', '(non-fast-forward)', 'cannot lock ref',
                      'Could not resolve host', 'Connection timed out',
                      'Connection reset', 'RPC failed', 'early EOF',
                      'The remote end hung up', 'Operation timed out',
                      'unable to access')


def classify_refusal(blob):
    text = blob or ''
    if any(m in text for m in _GATE_MARKERS):
        if any(d in text for d, _g in GENERATED):
            return 'generated'
        return 'gate'
    if any(m in text for m in _TRANSIENT_MARKERS):
        return 'transient'
    return 'unknown'


# ── A LOST RACE RE-PAID THE WHOLE GATE (hank b61, C1) ─────────────────────
# docs/recurring-bug-classes-2.md C1. The gate takes 75 s to ~4 min; other
# clones land every 1-7 min. Every 'transient' retry above rebased and ran the
# FULL gate again, so it landed only if the remote stood still for a whole gate
# run. hank b61 lost three in a row (`cannot lock ref`), each after a PASS.
# git's own compare-before-update-ref is what refused us; what was missing is a
# retry fast enough to win, i.e. one that does not re-run the gate on code it
# already passed.
#
# This is the durable form of cody b56's scratchpad push_fast.sh, Michael's
# rule. A retry skips the gate (`--no-verify`) ONLY when ALL of these hold:
#   1. the gate PASSED on this run -- a full push that reached the remote and
#      was refused as 'transient';
#   2. the `git patch-id --stable` set of origin/main..HEAD is exactly the set
#      it passed (no commit of ours changed: no conflict, re-seat, fold, new
#      commit);
#   3. the incoming commits (the base it passed -> the new origin/main) touch
#      none of the files ours change, and none of the gate's own inputs.
# Anything unreadable is a full gate, never a skip. Every skip is a row in
# docs/BYPASS-LOG.jsonl, under the same check name cody's rows use.
_REGATE_PATHS = ('docs/CRITICALITY-TIERS.md', 'tools/sairn_push_gate_hook.py',
                 '.githooks/')
_FAST_CHECK = 'pre-push gate (whole hook, git push --no-verify)'


def authored_commits(log_lines):
    """The (sha) of outgoing commits that carry AUTHORED changes. Pure.

    Bookkeeping that the loop or the gate regenerates after every rebase --
    the derived-docs commit and the gate's scrutiny-rows commit -- is excluded,
    because its content is re-derived from the new base each attempt and
    would otherwise change the patch-id set on every pure base move (b64)."""
    keep = []
    for ln in log_lines:
        sha, _t, subj = ln.partition('\t')
        if not sha.strip():
            continue
        if subj.startswith((REGEN_PREFIX, BOOKKEEPING_PREFIX)):
            continue
        keep.append(sha.strip())
    return keep


def _outgoing_state():
    """(patch-id set, files our commits change, origin/main sha), or None."""
    rc1, base, _ = git('rev-parse', 'origin/main')
    rc2, log, _ = git('log', '--format=%H%x09%s', 'origin/main..HEAD')
    if rc1 or rc2 or not base:
        return None
    shas = authored_commits(log.split('\n'))
    files = set()
    for sha in shas:
        rcf, fl, _ = git('show', '--name-only', '--format=', sha)
        if rcf:
            return None
        files |= set(fl.split('\n')) - {''}
    pids = set()
    for sha in shas:
        try:
            show = subprocess.run(['git', 'show', sha], cwd=REPO,
                                  capture_output=True, timeout=120)
            pid = subprocess.run(['git', 'patch-id', '--stable'], cwd=REPO,
                                 input=show.stdout, capture_output=True,
                                 timeout=120)
        except Exception:                                       # noqa: BLE001
            return None
        f = (pid.stdout or b'').decode('utf-8', 'replace').split()
        if show.returncode or pid.returncode or not f:
            return None
        pids.add(f[0])
    return frozenset(pids), files, base


def _incoming_files(old_base, new_base):
    rc, out, _ = git('diff', '--name-only', old_base, new_base)
    return None if rc else set(out.split('\n')) - {''}


def fast_retry_decision(gated, now, incoming):
    """(skip_gate, reason). Pure: `gated` is (patch-ids, base) the gate last
    passed, `now` is _outgoing_state(), `incoming` is _incoming_files()."""
    if gated is None:
        return False, 'the gate has not passed on this run'
    if now is None or incoming is None:
        return False, 'could not read the outgoing range -- full gate'
    if not now[0]:
        return False, 'nothing outgoing'
    if now[0] != gated[0]:
        return False, 'our commits changed since the gate passed'
    regate = sorted(p for p in incoming if p.startswith(_REGATE_PATHS))
    if regate:
        return False, 'incoming commits change the gate\'s inputs: %s' % ', '.join(regate)
    overlap = sorted(incoming & now[1])
    if overlap:
        return False, 'incoming commits touch our files: %s' % ', '.join(overlap)
    return True, ('pure base move: gate passed on these %d patch-id(s); %d '
                  'incoming file(s), none of ours' % (len(now[0]), len(incoming)))


BYPASS_FILE = 'docs/BYPASS-LOG.jsonl'


def append_only(head_text, work_text):
    """True when work_text only APPENDS lines to head_text. Pure (hank b65)."""
    h = (head_text or '').replace('\r\n', '\n')
    w = (work_text or '').replace('\r\n', '\n')
    return w.startswith(h) and len(w) >= len(h)


def _fold_bypass_rows():
    """Commit appended BYPASS-LOG rows as gate bookkeeping before a rebase.

    A LANDED fast retry writes its row after the push (b63), so the tree is
    dirty when the loop next starts and `git rebase` refused -- exit 3 on the
    b65 WY push. The row is real and must be committed, not discarded; a
    change that is not append-only is left alone and the rebase stops as
    before. Excluded from the patch-id set by its BOOKKEEPING_PREFIX subject."""
    rc, porc, _ = git('status', '--porcelain', '--', BYPASS_FILE)
    if rc != 0 or not porc.strip():
        return False, 'nothing'
    hrc, head_text, _ = git('show', 'HEAD:' + BYPASS_FILE)
    try:
        work = io.open(os.path.join(REPO, BYPASS_FILE), encoding='utf-8').read()
    except Exception as exc:                                    # noqa: BLE001
        return False, 'could not read %s: %s' % (BYPASS_FILE, exc)
    if hrc != 0 or not append_only(head_text, work):
        return False, '%s change is not append-only -- left for a human' % BYPASS_FILE
    _rc, tip, _ = git('rev-parse', '--short', 'HEAD')
    crc, _, cerr = git('commit', '-m', "%s%s): BYPASS-LOG row for a landed fast retry"
                       % (BOOKKEEPING_PREFIX, tip), '-m',
                       'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', '--', BYPASS_FILE)
    return (crc == 0), ('committed the BYPASS-LOG row' if crc == 0 else 'commit failed: %s' % (cerr or '')[:120])


def _log_fast_retry(gated, now, why, prc):
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import bypass_log
        _rc, tip, _ = git('rev-parse', '--short', 'HEAD')
        bypass_log.record(
            _FAST_CHECK,
            'PURE-BASE RETRY (push_retry --loop): %s; patch-ids [%s]; base %s '
            '-> %s; push exit %s' % (why, ' '.join(sorted(now[0])),
                                     gated[1][:9], now[2][:9], prc),
            command='git push --no-verify origin main', tip=tip)
    except Exception as exc:                                    # noqa: BLE001
        print('  NOTE: the skip was NOT logged to BYPASS-LOG: %s' % exc,
              file=sys.stderr)


def cmd_loop(attempts):
    cap = capture()
    if cap is None:
        print('COULD NOT CAPTURE the local-only subject set. Refusing to run '
              'the loop -- without it the amend guard cannot tell your commits '
              'from anybody else\'s.', file=sys.stderr)
        return 3
    print('captured %d local-only subject(s) as safe to amend' % len(cap))
    gated = None
    for i in range(1, attempts + 1):
        # The gate's write-back from the PREVIOUS attempt is a dirty tree that
        # would also block the rebase below; fold it into the one bookkeeping
        # commit before anything else (see fold_scrutiny).
        _bf, _bw = _fold_bypass_rows()
        if _bw != 'nothing':
            print('  bypass rows: %s' % _bw)
        _sf, _sw = fold_scrutiny()
        if _sf:
            print('  scrutiny rows: %s' % _sw)
        elif _sw != 'nothing':
            print('  scrutiny rows: %s' % _sw)
        git('fetch', '-q', 'origin')
        rc, behind, _ = git('rev-list', '--count', 'HEAD..origin/main')
        behind = int(behind or '0') if rc == 0 else -1
        print('attempt %d: behind %s' % (i, behind))
        if behind > 0:
            # COUNTED BEFORE THE REBASE, COMPARED AFTER. See ACCUMULATED.
            acc_before, acc_unreadable = accumulated_counts()
            if acc_unreadable:
                # NOT a refusal -- an unreadable ledger is somebody else's
                # problem and freezing every push on it would be worse. But it
                # is printed, because a ledger absent from the comparison is a
                # ledger this guard is NOT watching on this run.
                print('  NOTE: %d accumulated ledger(s) could not be read and '
                      'are NOT being watched this run: %s'
                      % (len(acc_unreadable), '; '.join(acc_unreadable)))
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
                acc = set(p for p, _k in ACCUMULATED)
                hit_acc = sorted(set(um) & acc)
                if hit_acc:
                    # SAID FIRST AND LOUDEST, because the advice printed for
                    # GENERATED documents directly below is `--ours`, and
                    # during a rebase that takes the UPSTREAM side. Applying
                    # it to one of these deletes your own appended record and
                    # leaves a tree that looks resolved.
                    print('  *** DO NOT RESOLVE THESE WITH --ours: %s'
                          % ', '.join(hit_acc), file=sys.stderr)
                    print('  They are APPEND-ONLY LEDGERS. During a rebase '
                          '`--ours` is the UPSTREAM side, so it discards the '
                          'record you just appended and nothing reports it.',
                          file=sys.stderr)
                    print('  Resolve by KEEPING BOTH SETS OF ENTRIES, then '
                          'check the count went UP and not down.',
                          file=sys.stderr)
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
            # ── THE REBASE SUCCEEDED. THAT IS NOT THE SAME AS NOTHING BEING
            # ── LOST. A clean rebase can still drop an appended ledger entry
            # when git auto-merges two edits near the same line, and a skipped
            # or abandoned commit takes its record with it. Compared here,
            # BEFORE the push, because after the push it is on main.
            acc_after, _unread_after = accumulated_counts()
            lost = accumulated_losses(acc_before, acc_after)
            if lost:
                print('REFUSING TO PUSH -- a rebase this tool just performed '
                      'SHRANK an append-only ledger:', file=sys.stderr)
                for p, b, a in lost:
                    print('    %-42s %d -> %d  (%d record(s) gone)'
                          % (p, b, a, b - a), file=sys.stderr)
                print('', file=sys.stderr)
                print('  Nothing was pushed and nothing was amended. Recover '
                      'the missing entries -- `git reflog` has the pre-rebase '
                      'tree -- or re-run whatever created them, then push '
                      'again.', file=sys.stderr)
                print('  A GROWING ledger is fine and is not reported: '
                      'another clone appending is the normal case, which is '
                      'why this compares counts rather than requiring them to '
                      'match.', file=sys.stderr)
                return 4
            _f, _why = _regenerate_and_fold()
            if _f:
                print('  regenerated documents folded into your own commit')
        now = _outgoing_state()
        skip = False
        if gated is not None:
            skip, why = fast_retry_decision(
                gated, now, _incoming_files(gated[1], now[2]) if now else None)
            print('  %s: %s' % ('FAST RETRY, gate not re-run' if skip
                                else 'full gate', why))
        if skip:
            prc, pout, perr = git('push', '--no-verify', 'origin', 'main',
                                  timeout=None)
            # LOGGED ONLY WHEN IT LANDED (hank b63). The row is a tracked
            # write; written after a REFUSED skip it dirtied the tree and the
            # next attempt's rebase stopped (exit 3). A refused push put
            # nothing on main, so there is no bypass to record. The row a
            # landed skip writes is left for the next commit to carry.
            if prc == 0:
                _log_fast_retry(gated, now, why, prc)
        else:
            prc, pout, perr = git('push', 'origin', 'main', timeout=None)
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
        # THE WHOLE TEXT IS KEPT (cody b47). The excerpt below is 14 lines plus
        # 8 remedy lines, and b46's two stops lost the one line that said what
        # happened. Overwritten per attempt; best-effort, never fatal.
        # Only into a directory that IS a git dir (it has HEAD): the selftest's
        # stubbed git answers rev-parse with '', which resolved to the repo
        # ROOT and left an untracked file there on the first run.
        try:
            _gd = git_dir()
            if _gd and os.path.isfile(os.path.join(_gd, 'HEAD')):
                _lp = os.path.join(_gd, 'push_retry_last_refusal.txt')
                io.open(_lp, 'w', encoding='utf-8', newline='\n').write(blob + '\n')
                print('    full text (%d lines): %s' % (len(lines), _lp))
        except Exception:                                       # noqa: BLE001
            pass
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
        # Only a refusal the loop can CHANGE is worth another attempt; see
        # classify_refusal() above for why a gate refusal stops the loop.
        kind = classify_refusal(blob)
        print('  refusal class: %s' % kind)
        if kind == 'generated':
            # A refusal naming a generated document is the exact failure
            # `regenerate()` fixes, and the loop used to be unable to reach it
            # unless something was behind.
            print('  the refusal names a GENERATED document -- regenerating '
                  'and folding in, which this loop could not do before '
                  '2026-10-05 unless it was also behind:')
            _f, _why = _regenerate_and_fold()
            if not _f:
                print('    not folded: %s -- STOPPING: the same push would be '
                      'refused the same way.' % _why, file=sys.stderr)
                return 5
            print('    folded; retrying')
        elif kind == 'transient':
            if not skip:
                # The full gate ran and let the push reach the remote.
                gated = (now[0], now[2]) if now else None
        else:
            print('STOPPING: this refusal is %s, not a lost race. The gate '
                  'decides from the outgoing range, which another attempt '
                  'does not change, and it counts refusals per tip. Read it, '
                  'fix the cause, then run the loop again. Nothing was '
                  'forced.' % ('the push gate\'s' if kind == 'gate'
                               else 'unclassified'), file=sys.stderr)
            return 5
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
        n = 5
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
