#!/usr/bin/env python
r"""hover_claim_precheck.py -- item 4 of the 2026-09-21 setup queue: "a cheap
deterministic pre-check on command shape before it runs, catching malformed
invocations rather than letting them silently do the wrong thing," scoped to
tools/sairn_claim.py.

WHAT THIS IS NOT. tools/sairn_claim.py is platform code, shared across every
clone -- editing it, or adding a new file under tools/, is exactly the "build"
half of the platform this role does not do (CLAUDE.md's core rule; enforced
mechanically by tools/hover_auditor_scope_gate.py). This file is NOT a patch
to sairn_claim.py and does not touch it. It is a READ-ONLY wrapper this role
runs BEFORE a real claim/check/release call, living in hover-audit-log/ (not
tools/) for the same reason hover_coverage_ledger.py and its siblings do --
self-tooling for this role's own process, not platform code.

TWO REAL, LIVE-VERIFIED GAPS MOTIVATE THIS, NOT A HYPOTHETICAL ONE. sairn_claim.py
itself is already heavily hardened (PR §4.3's overlap-matcher history, the
retyped-task-string guard, the self-overlap guard -- see cmd_claim()'s own
inline incident notes) so most SHAPE errors (bad subcommand, missing subject)
already fail loud via argparse. What is left, found by driving the real tool,
not by reading it:

  (1) `release <subject>` on a subject/id that matches NONE of the caller's
      own active claims prints 'No active claim of yours matches ...' and
      EXITS 0 -- the same exit code as an actual release. Verified live,
      2026-09-22, against this real repo (harmless: a non-matching release
      mutates nothing, confirmed via `git status` before/after):

          $ python tools/sairn_claim.py release definitely-not-a-real-xyz --no-push
          No active claim of yours matches 'definitely-not-a-real-xyz'.
          $ echo $?
          0

      Any caller or script that checks the exit code alone (not the printed
      text) cannot tell "released" from "nothing matched" -- a silent-wrong-
      thing shape in the same family this whole session's fail-open audit has
      been hunting (hover-audit-log #428/#429), just in platform code this
      role cannot itself patch. Flagged, not fixed -- see the queue-item-4
      entry for the flag to Michael/a build agent.

  (2) THE REVIEW/DISCHARGE FALSE-POSITIVE SHAPE, hit twice today by two
      different sessions. This role's own attempt to claim "fail-open audit:
      hover_coverage_ledger.py ..." was BLOCKED against fourth's unrelated
      "hover-audit-git-branch" claim on the shared phrase "audit hover" --
      confirmed a false positive by reading fourth's actual task (different
      file, different subject). The shared status registry shows fourth
      ALSO blocked right now, discharging hank's own 12:02:38Z review
      obligation -- structurally the same shape: a review/discharge claim
      for session X's work necessarily reuses X's own vocabulary (their
      name, their subject words), so the lexical matcher trips on exactly
      the claims MOST likely to be legitimate. PR §4.3 already names the
      fix ("say so out loud and proceed, do not reword to dodge it") but
      does not name the PATTERN, so every session re-derives "is this a
      false positive" from scratch instead of recognising the shape.

WHAT THIS TOOL DOES, MECHANICALLY: runs the REAL `check`/`list` subcommands
(read-only per .claude/claims/README.md -- "reads with `git show` and writes
nothing") and post-processes their ALREADY-TRUSTED output; it does not
reimplement or second-guess the matcher's own verdict.

  --precheck claim <subject> [task words...]
      1. Shape: refuses (before shelling out) if subject is empty or looks
         like an accidentally-swallowed flag (starts with '-'); WARNS (does
         not refuse) if no task words are given, since an empty task record
         is legal but nearly useless to the next reader.
      2. Runs the real `check` and relays CLEAR / BLOCKED / STALE verbatim.
      3. On BLOCKED, additionally flags the review/discharge shape when the
         blocking session's own name, or a word in {review, discharge,
         verify}, appears in the subject/task being claimed -- a mechanical
         signature match against the two real incidents above, not a claim
         that the block IS a false positive (only a human reading the other
         session's actual task can say that, per PR §4.3).

  --precheck release <subject>
      Runs the real `list` (read-only) and checks whether subject/id
      actually names one of the caller's own ACTIVE claims BEFORE the real
      release call would run. If not, says so plainly and explains that
      running release anyway will exit 0 having done nothing -- the gap
      documented above.

  --selftest   fixture-based self-check, driven against a disposable git
               fixture, never the real claims tree.

Run:
  python hover_claim_precheck.py --precheck claim hover "task words here"
  python hover_claim_precheck.py --precheck release some-subject
  python hover_claim_precheck.py --selftest
"""
import os
import re
import subprocess
import sys
import tempfile

_KNOWN_CLONES = (
    'C:/Users/marsh/Documents/SAIRN-hover',
    'C:/Users/marsh/Documents/SAIRN-hover2',
)

REVIEW_WORDS = ('review', 'discharge', 'verify', 'verification')


class CouldNotTell(Exception):
    pass


def discover_repo(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    env = os.environ.get('HOVER_LEDGER_REPO')
    if env:
        return env
    for candidate in _KNOWN_CLONES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


def shape_errors(cmd, subject, task_words):
    """[str] -- hard shape problems that make the intended call malformed
    BEFORE it is ever run. Empty list means shape is fine (task may still
    be empty for claim -- that is a warning, not a shape error)."""
    errs = []
    if subject is None or not subject.strip():
        errs.append('subject is empty -- sairn_claim.py requires a non-empty '
                     'subject positional')
    elif subject.startswith('-'):
        errs.append("subject %r starts with '-' -- argparse will read this "
                     'as an option, not the subject positional, and the '
                     'real call will fail (or worse, silently bind to the '
                     'wrong flag) rather than claiming what you intended'
                     % subject)
    if cmd == 'release' and task_words:
        errs.append('release takes only a subject/id -- these extra words '
                     'will be rejected by argparse as unrecognized arguments: %r'
                     % (task_words,))
    return errs


def shape_warnings(cmd, subject, task_words):
    warns = []
    if cmd == 'claim' and not task_words:
        warns.append('no task words given -- the claim will be recorded with '
                      'an empty task, which tells the next reader nothing '
                      'about what you actually claimed')
    return warns


def run_real(repo, argv):
    """Run the REAL tools/sairn_claim.py with argv, capturing output.
    Read-only for check/list per .claude/claims/README.md; for claim/release
    this function is only ever called on the caller's own EXPLICIT request
    (never invoked by --precheck itself, which only ever runs check/list)."""
    cmd = [sys.executable, os.path.join(repo, 'tools', 'sairn_claim.py')] + argv
    try:
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                            encoding='utf-8', timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CouldNotTell('could not run sairn_claim.py %s: %s' % (' '.join(argv), e))
    return r.returncode, r.stdout, r.stderr


def classify_check_output(rc, stdout, me_subject_task_text, stderr=''):
    """Deterministic post-processing of the REAL check output -- never a
    re-implementation of the matcher. Returns a dict with verdict
    (CLEAR/BLOCKED/COULD_NOT_TELL) and, on BLOCKED, the blocking session
    name(s) pulled from the ALREADY-PRINTED 'session   : X' lines, plus
    whether the review/discharge signature matches."""
    if 'BLOCKED' in stdout and rc == 1:
        sessions = re.findall(r'^\s*session\s*:\s*(\S+)', stdout, re.M)
        review_shaped = any(w in me_subject_task_text.lower() for w in REVIEW_WORDS)
        name_shaped = any(s.lower() in me_subject_task_text.lower() for s in sessions)
        return {
            'verdict': 'BLOCKED',
            'blocking_sessions': sessions,
            'review_discharge_signature': review_shaped or name_shaped,
            'raw': stdout,
        }
    if 'CLEAR' in stdout and rc == 0:
        return {'verdict': 'CLEAR', 'raw': stdout}
    return {'verdict': 'COULD_NOT_TELL', 'raw': stdout,
            'rc': rc, 'stderr_hint': stderr[-400:] if stderr else '(no stderr)'}


def precheck_claim(repo, subject, task_words):
    task_text = ' '.join(task_words)
    errs = shape_errors('claim', subject, task_words)
    if errs:
        return {'ok': False, 'shape_errors': errs}
    warns = shape_warnings('claim', subject, task_words)
    argv = ['check', subject] + task_words
    rc, out, err = run_real(repo, argv)
    verdict = classify_check_output(rc, out, subject + ' ' + task_text, err)
    verdict['shape_warnings'] = warns
    verdict['ok'] = True
    return verdict


def precheck_release(repo, subject):
    errs = shape_errors('release', subject, [])
    if errs:
        return {'ok': False, 'shape_errors': errs}
    rc, out, err = run_real(repo, ['list'])
    if rc not in (0, 2):
        # 2 is STALE_RC (fetch failed but the local listing still printed --
        # see cmd_list's own `return 0 if fetched else STALE_RC`); any other
        # nonzero means list itself did not produce a trustworthy listing.
        raise CouldNotTell('real `list` failed (rc=%d): %s' % (rc, err or out))
    # `list` has no --json output in this tool (confirmed by reading its
    # argparse setup: only --all/--no-fetch); its real format is
    # '[%-8s] %-6s %-16s %s  (%s)' (state, session, subject, task, age) --
    # matched by field position via this regex, not a raw substring test,
    # so a subject that happens to be a substring of a DIFFERENT row's task
    # cannot produce a false "this matches" verdict.
    row_re = re.compile(r'^\[(?P<state>\S+)\s*\]\s+(?P<session>\S+)\s+'
                         r'(?P<subject>\S+)\s+(?P<rest>.*)$')
    matches = []
    for ln in out.splitlines():
        m = row_re.match(ln)
        if not m:
            continue
        if m.group('state').strip() != 'active':
            continue
        if m.group('subject') == subject:
            matches.append(ln)
    would_noop = not matches
    return {
        'ok': True,
        'would_release_something': not would_noop,
        'warning': (
            'no active claim with SUBJECT %r found in `list` -- running '
            'release for real will print "No active claim of yours matches" '
            'and EXIT 0, identical to a successful release (verified live, '
            'see module docstring). Check the subject spelling against '
            '`list` before running it for real. CAVEAT: `list`\'s own output '
            'has no id column, so this check is by SUBJECT ONLY -- if you '
            'meant to release by claim id rather than subject, this warning '
            'may be a false alarm; this tool cannot tell the two apart from '
            '`list` alone.' % subject
        ) if would_noop else None,
        'raw_list': out,
    }


def _print_claim_report(subject, task_words, result):
    print('HOVER CLAIM PRECHECK -- claim %s %s' % (subject, ' '.join(task_words)))
    if not result['ok']:
        print('SHAPE ERROR -- refusing before running anything for real:')
        for e in result['shape_errors']:
            print('  - %s' % e)
        return
    for w in result.get('shape_warnings', []):
        print('WARNING: %s' % w)
    print('check verdict: %s' % result['verdict'])
    if result['verdict'] == 'BLOCKED':
        print('blocking session(s): %s' % ', '.join(result['blocking_sessions']))
        if result['review_discharge_signature']:
            print('')
            print('REVIEW/DISCHARGE FALSE-POSITIVE SIGNATURE MATCHED -- this claim '
                  'shares the blocking session\'s own name or a review/discharge/'
                  'verify word, the same shape that produced two confirmed false '
                  'positives today (this role vs fourth\'s hover-audit-git-branch; '
                  'fourth vs hank\'s 12:02:38Z obligation). This does NOT mean the '
                  'block is wrong -- read the blocking session\'s actual task '
                  '(printed above) and confirm. PR §4.3: if lexical-only, say so '
                  'out loud and proceed; never reword the task string to dodge it.')
    elif result['verdict'] == 'COULD_NOT_TELL':
        print('rc=%s, stderr: %s' % (result.get('rc'), result.get('stderr_hint')))
    print()
    print('--- real check output ---')
    print(result['raw'])


def _print_release_report(subject, result):
    print('HOVER CLAIM PRECHECK -- release %s' % subject)
    if not result['ok']:
        print('SHAPE ERROR -- refusing before running anything for real:')
        for e in result['shape_errors']:
            print('  - %s' % e)
        return
    if result['warning']:
        print('WARNING: %s' % result['warning'])
    else:
        print('OK -- %r matches an active claim; release will do real work.' % subject)


def run_fixtures():
    ok_count = [0]
    fail_count = [0]

    def ck(name, cond):
        if cond:
            ok_count[0] += 1
            print('  ok   ' + name)
        else:
            fail_count[0] += 1
            print('  FAIL ' + name)

    # --- shape_errors() ---
    ck('empty subject is a shape error',
       any('empty' in e for e in shape_errors('claim', '', ['x'])))
    ck('subject starting with - is a shape error',
       any('starts with' in e for e in shape_errors('claim', '-fix', ['x'])))
    ck('a normal subject+task has no shape errors',
       shape_errors('claim', 'stonedesk', ['fix', 'the', 'thing']) == [])
    ck('release with extra task words is a shape error',
       any('unrecognized' in e for e in shape_errors('release', 'stonedesk', ['extra'])))
    ck('release with no extra words has no shape errors',
       shape_errors('release', 'stonedesk', []) == [])

    # --- shape_warnings() ---
    ck('claim with no task words WARNS, does not refuse',
       shape_warnings('claim', 'stonedesk', []) != []
       and shape_errors('claim', 'stonedesk', []) == [])

    # --- classify_check_output(): synthetic text shaped exactly like the
    # real tool's own printed format, driven against both real incidents.
    blocked_text = (
        "BLOCKED -- another session already claimed overlapping work:\n\n"
        "  session   : fourth\n"
        "  subject   : hover-audit-git-branch\n"
        "  task      : the git-side violation branch ...\n"
        "  blocked by: shared phrase: \"audit hover\"\n"
        "  also share: audit, hover\n"
    )
    c1 = classify_check_output(1, blocked_text, 'audit self hover_coverage_ledger.py')
    ck('BLOCKED text with rc=1 classifies as BLOCKED', c1['verdict'] == 'BLOCKED')
    ck('blocking session name is extracted from the real output shape',
       c1['blocking_sessions'] == ['fourth'])
    ck('review/discharge signature fires when the CALLER task shares the '
       'blocking session name or a review-word -- the fourth-vs-hank real shape',
       classify_check_output(1, blocked_text.replace('fourth', 'hank'),
                              "discharge hank's 12:02:38Z obligation")
       ['review_discharge_signature'] is True)
    ck('review/discharge signature does NOT fire on an unrelated genuine '
       'collision with no shared name/word',
       classify_check_output(
           1, blocked_text, 'unrelated feature build on a totally different app'
       )['review_discharge_signature'] is False)

    clear_text = 'CLEAR -- no active overlapping claim from another session.\n'
    c2 = classify_check_output(0, clear_text, 'anything')
    ck('CLEAR text with rc=0 classifies as CLEAR', c2['verdict'] == 'CLEAR')

    c3 = classify_check_output(2, 'some unexpected output', 'anything')
    ck('neither BLOCKED nor CLEAR shape -> COULD_NOT_TELL, never guessed as '
       'either', c3['verdict'] == 'COULD_NOT_TELL')

    # --- end-to-end against a REAL disposable fixture repo, never the real
    # claims tree, proving precheck_claim()/precheck_release() actually
    # drive the real sairn_claim.py subprocess, not a mock of it.
    tmpdir = tempfile.mkdtemp()
    work_repo = os.path.join(tmpdir, 'work')
    os.makedirs(os.path.join(work_repo, 'tools'))
    os.makedirs(os.path.join(work_repo, '.claude', 'claims'))
    # A tiny stand-in sairn_claim.py: enough surface to prove the wrapper
    # shells out and parses real subprocess output, not a synthetic string
    # built in-process. Not the real tool -- the real tool is exercised
    # directly, live, elsewhere in this session's own claim/check/release
    # calls; this fixture isolates THIS wrapper's own subprocess+parsing
    # logic from network/git state.
    stub = (
        "import sys\n"
        "if sys.argv[1] == 'check':\n"
        "    print('BLOCKED -- another session already claimed overlapping work:')\n"
        "    print()\n"
        "    print('  session   : stubsession')\n"
        "    print('  subject   : stubsubject')\n"
        "    sys.exit(1)\n"
        "if sys.argv[1] == 'list':\n"
        "    print('[active  ] someone real-subject      some task here  (1.0h ago)')\n"
        "    sys.exit(0)\n"
    )
    with open(os.path.join(work_repo, 'tools', 'sairn_claim.py'), 'w', encoding='utf-8') as f:
        f.write(stub)

    result = precheck_claim(work_repo, 'my-subject', ['stubsession', 'task'])
    ck('end-to-end claim precheck: real subprocess runs the stub check, '
       'BLOCKED verdict and stubsession name come back through real stdout, '
       'not a mock', result['verdict'] == 'BLOCKED'
       and result['blocking_sessions'] == ['stubsession']
       and result['review_discharge_signature'] is True)

    r_match = precheck_release(work_repo, 'real-subject')
    ck('end-to-end release precheck: a subject present in the real `list` '
       'output is NOT flagged as a would-be no-op',
       r_match['would_release_something'] is True and r_match['warning'] is None)

    r_nomatch = precheck_release(work_repo, 'not-a-real-subject')
    ck('end-to-end release precheck: a subject absent from `list` IS flagged, '
       'warning names the real exit-0-noop gap', r_nomatch['would_release_something'] is False
       and 'EXIT 0' in r_nomatch['warning'])

    # --- REGRESSION for the bug found live in THIS tool's own CLI parsing:
    # --repo trailing after the task text must not leak into task_words.
    leaked = _strip_repo_flag(['claim', 'hover', 'some', 'task', 'words',
                                '--repo', 'C:/some/path'])
    ck('--repo trailing after task words is stripped from rest, not left '
       'to leak into task_words (the real bug hit live against stonedesk.html)',
       leaked == ['claim', 'hover', 'some', 'task', 'words'])
    ck('--repo with nothing after it (no task words at all) still strips cleanly',
       _strip_repo_flag(['release', 'subj', '--repo', 'C:/x']) == ['release', 'subj'])
    ck('no --repo present is a no-op',
       _strip_repo_flag(['claim', 'hover', 'task']) == ['claim', 'hover', 'task'])

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def _strip_repo_flag(rest):
    """Remove a trailing/embedded '--repo <value>' pair from the
    post-'--precheck' argument list before it is treated as subject/task
    words. Pulled into its own function so the real bug found live (--repo
    placed AFTER the task text leaking into task_words) has a direct,
    isolated regression test rather than only an end-to-end one."""
    if '--repo' in rest:
        ri = rest.index('--repo')
        rest = rest[:ri] + rest[ri + 2:]
    return rest


def main(argv):
    if '--selftest' in argv:
        ok = run_fixtures()
        sys.exit(0 if ok else 1)
    if '--precheck' not in argv:
        print('usage: --precheck claim <subject> [task...] | --precheck release <subject>',
              file=sys.stderr)
        return 2
    i = argv.index('--precheck')
    rest = argv[i + 1:]
    # Strip --repo <value> out of `rest` BEFORE treating it as subject/task
    # words -- found live: a real invocation with --repo trailing after the
    # task text (`--precheck claim hover "task" --repo C:\...`) silently
    # leaked '--repo' and the path into task_words, which the real `check`
    # subcommand does not accept (it has no --repo flag), producing an
    # argparse error whose stderr was not even shown, so this precheck
    # itself would have reported a bare, unexplained COULD_NOT_TELL -- the
    # exact "malformed invocation, silently doing the wrong thing" shape
    # this tool exists to catch, this time in its own argument handling.
    rest = _strip_repo_flag(rest)
    if not rest or rest[0] not in ('claim', 'release'):
        print("--precheck must be followed by 'claim' or 'release'", file=sys.stderr)
        return 2
    cmd = rest[0]
    repo = discover_repo(argv)
    if not repo:
        print('COULD NOT RUN: no readable clone found (checked --repo, '
              '$HOVER_LEDGER_REPO, and %s)' % ', '.join(_KNOWN_CLONES))
        return 2
    try:
        if cmd == 'claim':
            if len(rest) < 2:
                print('missing subject', file=sys.stderr)
                return 2
            subject, task_words = rest[1], rest[2:]
            result = precheck_claim(repo, subject, task_words)
            _print_claim_report(subject, task_words, result)
        else:
            if len(rest) < 2:
                print('missing subject', file=sys.stderr)
                return 2
            subject = rest[1]
            result = precheck_release(repo, subject)
            _print_release_report(subject, result)
    except CouldNotTell as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
