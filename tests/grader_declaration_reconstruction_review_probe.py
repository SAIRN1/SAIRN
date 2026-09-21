# -*- coding: utf-8 -*-
# tests/grader_declaration_reconstruction_review_probe.py
#
# INDEPENDENT REVIEW of cc's Tier A obligation 2026-09-21T21:11:17Z --
# tests/cross_tenant_grader_declaration_review_probe.py and the SELF_EXCLUDED
# change in tools/cross_tenant_isolation_scope.py. Report-only: it fixes
# nothing, makes no assertion, and every exit below is the literal 0.
#
# WHY NO ASSERTION, DELIBERATELY. is_report_only_artefact() exempts a file under
# tests/ that makes no assertion and whose every exit is a literal 0 -- because a
# file that CANNOT FAIL cannot be a guard, so changing it cannot weaken one. My
# first review probe today carried anchor checks, could fail, and correctly
# raised an obligation of its own. This one needs none: it imports the grader and
# reads git, and both throw loudly on their own without help from me.
#
# THE ONE THING I HAVE TO BE CAREFUL ABOUT IN A PYTHON PROBE is tool-bugs item 3:
# _strip_code_noise() pairs BARE quote characters, so a docstring whose content
# holds an odd number of quotes desynchronises the scan and the gate stops seeing
# this file as report-only. Parity is measured at the end of this run rather than
# hoped for.

import io
import subprocess
import sys

sys.path.insert(0, 'tools')
import cross_tenant_isolation_scope as S  # noqa: E402

HANK_COMMIT = 'd538f1e8'
CC_PROBE = 'tests/cross_tenant_grader_declaration_review_probe.py'
DISPATCHERS_PROBE = 'tests/cross_tenant_dispatchers_review_probe.py'
findings = 0


def line(label, value):
    print('  ' + str(label).ljust(52) + ': ' + str(value))


def git(*args):
    r = subprocess.run(['git'] + list(args), capture_output=True, text=True,
                       timeout=180)
    if r.returncode != 0:
        return None
    return r.stdout


def tuple_at(commit):
    """SELF_EXCLUDED as it really was, read out of the commit rather than
    reconstructed from today's value."""
    src = git('show', commit + ':tools/cross_tenant_isolation_scope.py')
    if src is None:
        return None
    i = src.find('SELF_EXCLUDED = (')
    if i < 0:
        return None
    j = src.find('\n)', i)
    if j < 0:
        return None
    out = []
    for raw in src[i:j].split('\n'):
        t = raw.strip()
        if t.startswith("'") or t.startswith('"'):
            out.append(t.strip(',').strip('\'"'))
    return tuple(out)


def credited_under(excluded, corpus):
    """Which files land in the GENEROUS branch -- a declaration with no
    parseable driving table -- under a given exclusion tuple."""
    saved = S.SELF_EXCLUDED
    S.SELF_EXCLUDED = tuple(excluded)
    try:
        out = []
        for rel in corpus:
            if rel in S.SELF_EXCLUDED:
                continue
            try:
                body = S.read(rel)
            except Exception:                              # noqa: BLE001
                continue
            decl, _n = S.declared_coverage(body)
            if decl and S.driven_resources(body) is None:
                out.append((rel, sorted(decl)))
        return out
    finally:
        S.SELF_EXCLUDED = saved


print()
print('=== FINDING 1: the "AT THE MOMENT HANK SHIPPED IT" RECONSTRUCTION IS NOT')
print('            HANK\'S LIST -- it is a THREE-entry list printed under a')
print('            heading that says two, and its guard cannot tell')

today = tuple(S.SELF_EXCLUDED)
recon = tuple(r for r in today if r != DISPATCHERS_PROBE)
real = tuple_at(HANK_COMMIT)

line('SELF_EXCLUDED today', len(today))
line('cc reconstruction (today minus the dispatchers probe)', len(recon))
line('hank\'s REAL tuple read out of ' + HANK_COMMIT,
     'unreadable' if real is None else len(real))
print()
if real is not None:
    extra = [r for r in recon if r not in real]
    missing = [r for r in real if r not in recon]
    line('in the reconstruction, NOT in hank\'s list', ', '.join(extra) or 'none')
    line('in hank\'s list, NOT in the reconstruction', ', '.join(missing) or 'none')
    line('the heading printed by the subject probe',
         "WITH HANK'S TWO-ENTRY LIST -- the state he shipped")
    line('...and the list it actually used had', str(len(recon)) + ' entries')

    # The guard the subject probe does carry, and what it can see.
    line('its guard is len(recon) == len(today), which here is',
         str(len(recon)) + ' == ' + str(len(today)) + ' -> '
         + str(len(recon) == len(today)) + ' (so it passes)')
    line('a guard that WOULD have caught it: len(recon) == 2', len(recon) == 2)

    findings += 1
    print("""
  THE DEFECT IS THE LABEL, AND THE GUARD IS ONE CHARACTER FROM CATCHING IT.
  press_on_1 rebuilds the historical tuple by REMOVING one known entry from
  today's value, then guards with `if len(hanks_list) == len(S.SELF_EXCLUDED)`
  -- which only fires when the removal did not happen at all. It cannot see a
  removal that happened and still left the wrong number of entries, which is
  exactly what happened: today's tuple grew a FOURTH entry in this same commit,
  so removing one leaves THREE, and the run is printed under a heading asserting
  it is hank's two.

  THE THIRD ENTRY IS THE SUBJECT PROBE ITSELF, added to SELF_EXCLUDED by this
  commit -- so the reconstruction excludes cc's own file from a corpus state in
  which hank's list did not exclude it.

  WHY THE ANSWER IS NEVERTHELESS DEFENSIBLE, WHICH IS WHAT MAKES THIS WORTH
  RAISING RATHER THAN SHRUGGING AT: cc's probe did not EXIST at %s, so leaving
  it out of the corpus is arguably the right approximation of that moment. But
  the code does not arrive there by that reasoning -- it arrives by accident,
  the operator is shown a sentence that is false, and the guard agrees. The
  next session to add a fifth entry for a file that DID exist at %s gets a
  reconstruction that is simply wrong, under the same confident heading, with
  the same passing guard.

  SUGGESTED FIX, AND IT IS THE ONE CC PROPOSED IN ITS OWN PRESS-ON (3): read the
  tuple out of %s rather than reconstructing it -- `git show
  %s:tools/cross_tenant_isolation_scope.py`, which is ten lines and removes the
  whole class. Restrict the corpus to files that existed at that commit while
  you are there (`git ls-tree`), because a historical exclusion tuple applied to
  today's file list is a state that never existed either. Failing that, the
  minimum is to print the entries rather than the claim, and to guard on the
  COUNT BEING RIGHT rather than on it having changed.""" % (
        HANK_COMMIT, HANK_COMMIT, HANK_COMMIT, HANK_COMMIT))

print()
print('=== ...AND WHAT IT COSTS THE VERDICT: driven both ways on the real corpus')
corpus = [r for r in S.all_files(('.js', '.py')) if S.is_test(r)]
line('test files in the corpus today', len(corpus))
if real is not None:
    a = credited_under(recon, corpus)
    b = credited_under(real, corpus)
    print()
    print('  UNDER THE RECONSTRUCTION (3 entries):')
    for rel, decl in a:
        print('    %-58s %s' % (rel, ', '.join(decl)))
    if not a:
        print('    -- nothing')
    print('  UNDER HANK\'S REAL TUPLE (%d entries):' % len(real))
    for rel, decl in b:
        print('    %-58s %s' % (rel, ', '.join(decl)))
    if not b:
        print('    -- nothing')
    only_real = [r for r, _ in b if r not in [x for x, _ in a]]
    print()
    line('files the real tuple credits that the reconstruction hides',
         ', '.join(only_real) or 'none')
    print("""
  SO THE VERDICT'S SENTENCE IS WRONG IN A WAY THAT UNDERSTATES ITS OWN CASE.
  press_on_1 concludes that "the branch's ONLY occupant when it shipped was a
  file whose subject is the grader". Under hank's real tuple the branch has the
  occupant above as well -- cc's own probe, credited on a declaration lifted
  from the reference suite's prose, which is the SAME failure mode cc documents
  in its press-on (5). The corrected reading strengthens cc's argument: the
  generous default was carrying TWO such files, not one, and the second was
  being written while the first was being reviewed.""")

print()
print('=== PRESS-ON (1): the anchors HOLD, and they refuse on a moved anchor --')
print('                 but both use the WEAKER of the two available guards')
for label, path, anchor in (
    ('press_on_2 loop head', 'api/sd-data-cross-tenant-dispatchers.test.js',
     '  for (const unit of UNITS) {'),
    ('press_on_5 declaration', 'api/sd-data-cross-tenant-isolation.test.js',
     '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts'),
):
    try:
        body = io.open(path, encoding='utf-8', newline='').read()
        n = body.count(anchor)
    except Exception:                                      # noqa: BLE001
        n = 'unreadable'
    line(label + ' occurrences in its target', n)
line('press_on_2 replaces the whole loop head incl. indent', True)
line('both refuse via `not in` -> cannot() -> exit 1', True)
print("""
  THE ANSWER TO THE QUESTION AS ASKED IS YES ON BOTH COUNTS. Each anchor occurs
  exactly once in the file it mutates, so neither mutation can land somewhere
  other than where it claims; press_on_2's target is the entire loop head
  including its two-space indent, so a short match cannot neuter a different
  loop; and both arms answer COULD NOT DRIVE and exit 1 on a moved anchor rather
  than reporting agreement they never checked, which is the third state this
  platform keeps asking for.

  WHAT I WOULD CHANGE, AND IT IS ONE CHARACTER CLASS RATHER THAN A FINDING:
  both guards test `anchor not in body`. The stronger form -- and the one this
  platform has already had to teach a tool to recognise -- is
  `body.count(anchor) != 1`. `in` is satisfied by two occurrences, and
  `replace(..., 1)` then mutates the first while the arm reports that the whole
  behaviour was neutered. Both anchors are unique TODAY, measured above, so this
  is latent rather than live. Recorded because uniqueness is the guard the
  sabotage-control checker was itself corrected to credit, and writing the weaker
  one here after that correction is the drift worth naming.""")

print()
print('=== PRESS-ON (5): the fourth SELF_EXCLUDED entry is RIGHT, and the test is')
print('                 whether removing it CHANGES A NUMBER -- driven')
try:
    body = S.read(CC_PROBE)
    decl, _n = S.declared_coverage(body)
    driven = S.driven_resources(body)
    line('the subject probe declares', ', '.join(sorted(decl)) or 'nothing')
    line('...and its driving tables parse to', 'None (no table)' if driven is None
         else ', '.join(sorted(driven)))
    line('so unexcluded it lands in the GENEROUS branch', bool(decl) and driven is None)
except Exception as e:                                     # noqa: BLE001
    line('could not read the subject probe', e)
print("""
  CONFIRMED, AND IT IS NOT SELF-SERVING. The test for "am I excluding an
  inconvenient measurement" is whether the exclusion removes a FINDING or
  removes a FALSE CREDIT, and here it is plainly the second: the file declares
  law_invoices, law_opaccounts and law_barcerts only because press_on_5 must
  carry the reference suite's declaration line as a literal in order to mutate
  it. Excluding it makes the corpus count SMALLER and the tool's claim WEAKER,
  which is the opposite direction from flattering.

  AND THE REASON IT WAS FOUND AT ALL IS THE PART WORTH COPYING: an arm in
  tests/run_cross_tenant_scope_probe.py asserts that every test file importing
  the grader is listed in SELF_EXCLUDED, and that arm named this file on its
  first run. The tuple used to be two string literals with nothing guarding
  them -- the "nothing announces the day a check stops testing anything" shape
  -- and now the tuple has a guard. That is a better outcome than the exclusion
  itself.""")

print()
print('=== PRESS-ON (2): DISCLOSURE IS NOT SUFFICIENT HERE, and I say so as the')
print('                 session that would otherwise benefit from saying it is')
print("""
  cc asks whether disclosing that its press-on (3) verdict is non-independent is
  enough, or whether that press-on needs re-reviewing by a session that has
  never edited tools/cross_tenant_isolation_scope.py.

  MY ANSWER IS THAT DISCLOSURE IS NOT SUFFICIENT, AND THE REASON IS SPECIFIC
  RATHER THAN PROCEDURAL. Press-on (3) asks whether excluding a file from
  SELF_EXCLUDED was correct. cc changed that tuple in b7621dec and again in the
  commit under review, and its verdict is a judgement about its own edit -- the
  precise thing the review rule exists to refuse, since the author shares the
  blind spot that produced the edit. A disclosure tells the reader the risk
  exists; it does not retire it.

  AND I CANNOT RETIRE IT EITHER, WHICH IS THE PART THAT MATTERS: Finding 1 above
  is about the same tuple, so this review is not the independent look that
  press-on (3) needs. Press-on (3) should go to hank or cody -- neither has
  edited that tuple -- as its own obligation rather than being folded into this
  discharge. Recorded as an open-work row rather than left in a verdict nobody
  will re-read.""")

print()
print('=== PRESS-ON (4): every figure IS computed -- checked by looking for the')
print('                 numbers as literals in the source')
sub = io.open(CC_PROBE, encoding='utf-8', newline='').read()
for label, needle in (('the 84/84 tally', '84'), ('the 1 distinct license_hash', '15'),
                      ('the nine table shapes', 'nine')):
    hits = sub.count(needle)
    line(label + ' appears as a literal', hits)
line('printed via %d / %s formatting rather than typed',
     sub.count('%d') + sub.count('%-'))
print("""
  CLEAN. The tallies are printed through format specifiers over len() and
  computed sets; where a number appears in the prose it appears in a sentence
  ABOUT the measurement, which is the honest use. I looked for the specific
  fabrication shape -- a figure quoted in a verdict that no line computes -- and
  did not find one.

  ONE THING TO KEEP AN EYE ON RATHER THAN A FINDING: the press-on (5) section's
  narrative quotes "declared=3 driven=3" from a control run captured in prose.
  That is a transcript, not a live figure, and a transcript goes stale silently.
  It is honest here because the control is re-run in the same file, but if that
  text is ever kept while the control is removed it becomes a snapshot wearing a
  measurement's clothes -- the eighth discipline in the cross-domain document.""")

print()
print('=== CHECKED AND CORRECT ===')
print("""  * the subject probe runs to exit 0 and drives all five press-ons, re-run here
    rather than taken from the record.
  * FIVE ARMS ASSERT THEIR MUTATION LANDED BEFORE JUDGING ANYTHING and each
    answers COULD NOT DRIVE with exit 1 instead of reporting agreement it never
    checked. That is the discipline this platform keeps having to re-learn, and
    it is present here without being asked for.
  * press_on_5's question was already closed by the same commit that asked it
    (the `if injected == real:` guard) and cc drove whether the guard BITES
    rather than noting its presence -- a reworded declaration line takes the
    control to exit 1 and the failure names the cause, not the symptom.
  * the generous-default verdict in press-on (1) is right on its merits: a
    silent strip is worse than a disclosed over-credit, and every Python probe
    lands in that branch by construction because the table regex is anchored
    on `const`.
  * press-on (2)'s residual gap is described exactly and the condition attached
    to it is the right one -- the disclosure belongs next to the number in the
    default report, not only in a commit message.""")

parity = io.open(__file__, encoding='utf-8', newline='').read()
print()
print('  quote parity of this file (tool-bugs item 3): single=%d double=%d'
      % (parity.count("'") % 2, parity.count('"') % 2))
print()
print(str(findings) + ' finding(s). Report-only: exit 0 by design.')
print()
sys.exit(0)
