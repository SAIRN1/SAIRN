#!/usr/bin/env python
"""The hover auditor's separation, enforced on the SERVER where it cannot be
switched off locally.

    python tools/hover_separation_ci.py --range <base>..<tip>
    python tools/hover_separation_ci.py --fixtures
    python tools/hover_separation_ci.py            # HEAD~1..HEAD

Exit 0 clean, 1 a finding, 2 COULD NOT RUN -- never folded into either of the
other two (PR 1.11).

── WHY A SERVER CHECK WHEN A LOCAL GATE ALREADY EXISTS ──────────────────────
`tools/hover_auditor_scope_gate.py` is the PREVENT half and it is good: it
refuses the commit before it exists. But it is a local hook, armed per clone by
a marker inside `.git/`, so every way it can be absent is a way it is silent:

  * the marker file is not there, or was removed;
  * `git commit --no-verify` / `git push --no-verify`;
  * a fresh clone nobody armed;
  * the hook script erroring, which a hook is written to survive.

None of those leave a trace that says "the gate did not run". This runs on
GitHub's side of the push, off the author's machine, and its verdict is a
required status rather than an honour system.

── IT REUSES BOTH EXISTING TOOLS AND OWNS ONLY THE JOIN ─────────────────────
Attribution comes from `hover_separation_audit.attribute()`; the scope comes
from `hover_auditor_scope_gate.ALLOWED`. Neither is re-implemented here. A
second copy of either would be a second answer to a question that already has
one, and this repo has paid for that shape repeatedly -- seven `strip_comments`
implementations, three of them destroying most of their input.

Both source modules define the scope separately and deliberately, for a reason
they each state. So this ASSERTS THEY STILL AGREE before using either, and
refuses if they have drifted. Two definitions that must match and nothing
comparing them is how they stop matching.

── WHAT THIS CAN AND CANNOT SAY, BEFORE ANY RESULT ─────────────────────────
It can say: **no commit in this push touches the auditor's own skill directory
AND anything outside its scope.**

That is a question about COMMIT SHAPE and needs no attribution, which matters
because all five roles commit through one git identity and there is no author
field to group by. See review() for why the alternative could not work.

It cannot say the auditor wrote no platform code. A commit touching ONLY
platform code, and nothing of the auditor's own, is indistinguishable from any
build agent's -- nothing here fires on it. **Git alone cannot prove the
negative, and a green check here is not that proof.**

── THIS PARAGRAPH SAID THE OPPOSITE UNTIL ITS FIRST ARTICLE INSPECTION ─────
It read: *"Attribution of a hover commit rests on the commit touching ONLY the
auditor's skill directory, so a commit in which the auditor also edited
api/sd-data.js fails that test and lands in UNATTRIBUTED rather than being
caught."* That described v1, which keyed on attribution and was replaced
precisely because it could never fire. After the rewrite the sentence was not
merely stale -- it was BACKWARDS: the mixed commit it says is missed is now the
one case the tool exists to refuse.

Nothing mechanical caught it. `review()` carried the correct account the whole
time, three screens below a header that contradicted it, and both compile.
Found by the FAI worksheet on 2026-09-16, reading the ten claims in this header
against the eleven arms in the suite -- which is the pass the item 47 document
insists must be done by a human, and this is what it is for. A reader trusting
the header would have believed the gate cannot catch the very thing it catches.

WHAT WOULD CLOSE IT is the auditor becoming positively identifiable on every
commit -- a bookkeeping file it always touches, the way each build agent touches
`.claude/claims/<session>.json`. MEASURED 2026-09-16: `.claude/claims/hover.json`
is named in CLAUDE.md's clone registry and **has never existed in this history**
(zero commits touch it), so the auditor takes no claims and there is nothing to
key on. That is a decision for whoever owns the role, not a gap this file may
quietly fill, and it is reported rather than worked around.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import hover_separation_audit as A                               # noqa: E402
import hover_auditor_scope_gate as G                             # noqa: E402

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2


def scope_definitions_agree():
    """The two modules' scope sets, and whether they still say the same thing.

    They are separate constants on purpose -- the gate must run inside a hook
    with no imports, and a shared module one of them silently stopped importing
    would be a failure neither reports. That reasoning is sound and it makes
    this comparison necessary rather than optional.
    """
    gate = set(p for p, _why in G.ALLOWED)
    audit = set(A.AUDITOR_SCOPE)
    return gate, audit, gate == audit


def target_repo():
    """The repository this run is judging: the one it was INVOKED IN.

    ── IT READ ITS OWN CLONE REGARDLESS OF WHERE IT RAN (2026-09-16) ────────
    This was `git -C REPO`, with REPO derived from the file's own location. In
    CI that is accidentally right, because the checkout is the repo. Everywhere
    else it is wrong in the worst way: pointed at another repository it would
    read THIS one's history, find the given SHAs missing, and report COULD NOT
    RUN -- or, with SHAs that happened to resolve, report a verdict about
    commits that were never the subject.

    Caught by tests/hover_separation_ci_probe.py, which builds a real
    repository and makes real commits in it precisely because the synthetic
    fixtures cannot see the range-reading half. Its own docstring predicted
    this failure before the run produced it.
    """
    r = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return REPO


def commits_in(rng):
    """[{sha, subject, files}] for a revision range. Returns (commits, error)."""
    r = subprocess.run(['git', '-C', target_repo(), 'log',
                        '--format=%x00%H%x00%s', '--name-only', rng],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    if r.returncode != 0:
        return None, 'git log %s failed: %s' % (rng, r.stderr.strip()[:200])
    out, cur = [], None
    for line in r.stdout.split('\n'):
        if line.startswith('\x00'):
            parts = line[1:].split('\x00', 1)
            if len(parts) < 2:
                return None, 'unparseable log header: %r' % line[:80]
            cur = {'sha': parts[0], 'subject': parts[1], 'files': []}
            out.append(cur)
        elif line.strip() and cur is not None:
            cur['files'].append(line.strip().replace('\\', '/'))
    return out, ''


def is_bookkeeping(path):
    """A coordination record, not platform code.

    `.claude/claims/<session>.json` and `SAIRN-ACTIVE-WORK-<session>.md` are how
    every session says what it is working on. They are not code, nothing is
    served from them, and the rule this gate enforces is about PLATFORM CODE --
    "Never write, edit, or push platform code."

    THIS CARVE-OUT WAS FORCED BY A FIXTURE, not chosen in advance. Without it a
    commit carrying the auditor's skill file AND the committer's own claim entry
    was refused, which would have made the one convention that could break this
    check's circularity -- the auditor recording a claim on every commit, so it
    becomes positively identifiable -- impossible to adopt without first
    changing the gate. A rule that forbids its own fix is worse than the gap.
    """
    return bool(A.CLAIM_RE.match(path) or A.WORKLOG_RE.match(path))


def offending(commit):
    """Paths this commit touched that are outside the auditor's scope.

    Bookkeeping is excluded -- see is_bookkeeping(). Everything else counts,
    including docs and sql: the rule is about what the role may WRITE, and a
    migration or a standing document is still platform work.
    """
    return sorted(p for p in commit['files']
                  if not A.in_auditor_scope(p) and not is_bookkeeping(p))


def review(commits):
    """(findings, touching_scope, unattributed).

    ── THE RULE IS ABOUT COMMIT SHAPE, NOT ABOUT WHO WROTE IT, AND THE FIRST
    ── VERSION OF THIS FILE COULD NEVER HAVE FIRED (2026-09-16)
    v1 asked "is this commit the auditor's, and did it leave scope". Its own
    blind lock refused it before it ran on anything real, and the reason is the
    circularity `hover_separation_audit.py` names in its header, now shown to
    be fatal rather than merely limiting:

        a commit is attributed to the auditor only when it touches ONLY the
        auditor's skill directory -- so a commit that ALSO touches
        api/sd-data.js is not attributed to the auditor, and the check that
        keys on attribution never looks at it.

    **The exact commit the gate exists to refuse is the one it cannot see.** A
    required status check built that way is green forever and reads as
    coverage: "a pattern that cannot fire is worse than no pattern."

    SO THE QUESTION CHANGED. Not "who committed this" -- unanswerable from git,
    because all five roles share one identity -- but:

        does this commit touch the auditor's scope AND something outside it?

    That is decidable from the diff alone, needs no attribution, and refuses
    precisely the mixed commit the separation rule forbids. It also catches the
    boundary running the OTHER way, which CLAUDE.md calls out in terms: a build
    agent reaching into the auditor's directory alongside platform work.

    WHAT IT STILL CANNOT SEE, and this is the honest residual: a commit that
    touches ONLY platform code and never the auditor's directory is
    indistinguishable from any build agent's. If the auditor wrote platform
    code and nothing of its own in the same commit, nothing here fires. Closing
    that needs the auditor to be positively identifiable on every commit -- see
    the header on `.claude/claims/hover.json`, which the registry names and
    which has never existed.
    """
    findings, touching, unattributed = [], [], []
    for c in commits:
        in_scope = [p for p in c['files'] if A.in_auditor_scope(p)]
        # SIGNATURE, not scope, decides whether this commit is about the
        # auditor at all. The register is IN SCOPE and is written by all five
        # roles, so keying on scope would make every register commit on the
        # platform a candidate -- the same conflation that once inflated the
        # auditor's commit count from 20 to 46.
        signature = [p for p in c['files'] if A.is_auditor_signature(p)]
        if signature:
            touching.append(c)
            bad = offending(c)
            if bad:
                findings.append((c, bad))
        elif A.attribute(c)[0] is None:
            unattributed.append((c, 'no bookkeeping file'))
    return findings, touching, unattributed


# ── THE BLIND LOCK ───────────────────────────────────────────────────────────
# A gate whose job is to refuse must be seen to refuse. These are synthetic
# commits, classified without touching git, in both directions.
def _c(sha, files, subject='fixture'):
    return {'sha': sha, 'subject': subject, 'files': list(files)}


SKILL = A.SKILL_DIR
FIXTURES = (
    ('auditor commit inside its own skill dir',
     _c('a' * 40, [SKILL + 'SKILL.md']), False),
    ('auditor commit touching PLATFORM CODE -- must be refused',
     _c('b' * 40, [SKILL + 'SKILL.md', 'api/sd-data.js']), True),
    ('auditor commit touching the app HTML -- must be refused',
     _c('c' * 40, [SKILL + 'notes.md', 'stonedesk.html']), True),
    # A build agent's commit is not this check's business, however large.
    ('a build agent commit touching platform code is NOT a finding',
     _c('d' * 40, ['.claude/claims/cody.json', 'api/sd-data.js']), False),
    ('an unattributed commit is NOT a finding -- it is the gap, not a verdict',
     _c('e' * 40, ['api/sd-data.js']), False),
    # The register is in SCOPE for the auditor and is written by everyone.
    ('the auditor writing the defect register is in scope',
     _c('f' * 40, [SKILL + 'SKILL.md', A.REGISTER]), False),
    # THE BOUNDARY RUNNING THE OTHER WAY, which CLAUDE.md calls out in terms:
    # "A build agent must not reach into that clone." A commit carrying a build
    # agent's own bookkeeping AND an edit to the auditor's skill is refused for
    # the same reason and by the same rule.
    ('a BUILD AGENT reaching into the auditor\'s skill dir -- also refused',
     _c('g' * 40, ['.claude/claims/cody.json', SKILL + 'SKILL.md',
                   'api/sd-data.js']), True),
    ('...and a build agent touching ONLY the auditor\'s skill dir is not',
     _c('h' * 40, ['.claude/claims/cody.json', SKILL + 'SKILL.md']), False),
)


def run_fixtures():
    wrong = []
    for label, commit, should_fire in FIXTURES:
        findings, _h, _u = review([commit])
        if bool(findings) != should_fire:
            wrong.append('%-62s expected %s, got %s'
                         % (label, 'REFUSED' if should_fire else 'clean',
                            'REFUSED' if findings else 'clean'))
    gate, audit, agree = scope_definitions_agree()
    if not agree:
        wrong.append('the two scope definitions have DRIFTED: gate=%s audit=%s'
                     % (sorted(gate), sorted(audit)))
    # AND THE AGREEMENT CHECK ITSELF MUST BE ABLE TO FAIL, or it is decoration.
    real = A.AUDITOR_SCOPE
    try:
        A.AUDITOR_SCOPE = ('.claude/skills/somewhere-else/',)
        if scope_definitions_agree()[2]:
            wrong.append('the drift check passed against a DIFFERENT scope set '
                         '-- it is not comparing anything')
    finally:
        A.AUDITOR_SCOPE = real
    if wrong:
        print('REFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  ' + w)
        return EXIT_COULD_NOT_RUN
    print('  %d/%d fixtures correct (%d must refuse, %d must not), plus the '
          'scope-drift check driven in both directions.'
          % (len(FIXTURES), len(FIXTURES),
             sum(1 for f in FIXTURES if f[2]),
             sum(1 for f in FIXTURES if not f[2])))
    return EXIT_CLEAN


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    gate, audit, agree = scope_definitions_agree()
    if not agree:
        print('COULD NOT RUN: the auditor scope is defined in two places and '
              'they no longer agree.')
        print('  hover_auditor_scope_gate.ALLOWED   : %s' % sorted(gate))
        print('  hover_separation_audit.AUDITOR_SCOPE: %s' % sorted(audit))
        print('  Nothing was checked. Reconcile them before trusting either.')
        return EXIT_COULD_NOT_RUN

    rng = 'HEAD~1..HEAD'
    if '--range' in argv:
        rng = argv[argv.index('--range') + 1]
    commits, err = commits_in(rng)
    if commits is None:
        print('COULD NOT RUN: %s' % err)
        print('  Nothing was checked, and that is NOT a pass.')
        return EXIT_COULD_NOT_RUN

    findings, hover, unattributed = review(commits)

    print('HOVER AUDITOR SEPARATION -- server-side, range %s' % rng)
    print('  %d commit(s) in range; %d touch the auditor\'s skill directory; '
          '%d carry no bookkeeping file.'
          % (len(commits), len(hover), len(unattributed)))
    print('')
    if findings:
        print('  REFUSED (%d) -- a commit touched the auditor\'s skill directory '
              'AND code outside its scope:' % len(findings))
        for c, bad in findings:
            print('    %s  %s' % (c['sha'][:12], c['subject'][:70]))
            for p in bad:
                print('        %s' % p)
        print('')
        print('  The fifth role audits the four build agents and is itself')
        print('  reviewed by nobody. That is only safe while it builds nothing,')
        print('  which is the sentence its own skill file carries: "Never')
        print('  write, edit, or push platform code."')
        return EXIT_FINDING

    print('  No commit touching the auditor\'s skill directory also touched')
    print('  anything outside its scope.')
    print('')
    print('  AND THAT IS THE NARROW CLAIM, NOT THE BROAD ONE. %d commit(s) in'
          % len(unattributed))
    print('  this range carry no bookkeeping file at all. A commit in which the')
    print('  auditor wrote ONLY platform code, touching nothing of its own,')
    print('  is indistinguishable from any build agent\'s and nothing here')
    print('  fires. This check cannot prove the negative and a green result is')
    print('  not that proof -- see the header for what would close it.')
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
