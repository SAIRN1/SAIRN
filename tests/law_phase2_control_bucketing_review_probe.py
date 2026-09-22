# -*- coding: utf-8 -*-
# tests/law_phase2_control_bucketing_review_probe.py
#
# INDEPENDENT REVIEW of cc's Tier A obligation 2026-09-22T10:00:26Z --
# tests/law_phase2_control_review_probe.py. Report-only: no assertion, every exit
# the literal 0, so is_report_only_artefact() exempts it.
#
# I AM THE AUTHOR OF THE CODE THAT PROBE REVIEWS, AND THAT IS DISCLOSED UP FRONT.
# cc's probe reviews my phase-2 session gate. This file reviews cc's PROBE, not my
# own gate -- the subject is cc's measurement apparatus. Where a question here
# bears on whether my gate is correct I say so and stop, because that half is not
# mine to certify.
#
# THE ONE THING WORTH RUNNING THIS FOR: cc disclosed, in its own obligation, that
# press-on (2)'s ALLOW/REFUSAL bucketing is a regex over ARM NAMES and asked a
# reviewer to check the bucketing against the actual names. That is the check, and
# it comes back worse than cc framed it.

import io
import re
import subprocess
import sys

SUITE = 'api/sd-data-law-phase2-session.test.js'
SUBJECT = 'tests/law_phase2_control_review_probe.py'

ALLOW = re.compile(r'can read|can write|allow|200', re.I)
REFUSE = re.compile(r'refus|401|403|NO_SESSION', re.I)


def line(label, value):
    print('  ' + str(label).ljust(54) + ': ' + str(value))


print()
print('=== FINDING 1: the ALLOW/REFUSAL bucketing cannot see 9 of 25 arms, and SIX')
print('            of the nine are REFUSAL arms -- which is the side whose')
print('            emptiness the verdict "an outage, not a hole" rests on')

out = subprocess.run(['node', SUITE], capture_output=True, text=True, timeout=600).stdout
names = [l.split('ok - ', 1)[1].strip() for l in out.splitlines() if ' ok - ' in l]

neither = [n for n in names if not ALLOW.search(n) and not REFUSE.search(n)]
both = [n for n in names if ALLOW.search(n) and REFUSE.search(n)]
refusal_in_substance = [n for n in neither if 'cannot' in n.lower()]

line('arms in the suite', len(names))
line('classified ALLOW', sum(1 for n in names if ALLOW.search(n)))
line('classified REFUSAL', sum(1 for n in names if REFUSE.search(n)))
line('in NEITHER bucket', len(neither))
line('in BOTH buckets', len(both))
line('of the unclassified, refusal arms in SUBSTANCE', len(refusal_in_substance))
print()
for n in neither:
    print('    unclassified: ' + n[:96])

print("""
  WHAT CC DISCLOSED AND WHAT IS ACTUALLY THE CASE. The obligation says: "If an arm
  is named in a way neither pattern matches it lands in neither bucket and the
  count silently understates one side." That is exactly right, and the measurement
  is 9 of 25 -- 36 per cent of the suite -- with SIX of those nine being refusal
  arms in substance: three "a valid SAIRNdental owner session cannot read ..." and
  three "a deactivated employee cannot read ...".

  WHY 'cannot read' ESCAPES THE ALLOW PATTERN AND ALSO THE REFUSAL ONE, which is
  the part worth writing down because it looks like it should be caught: ALLOW
  matches the substring `can read`, and in "cannot read" the characters after
  `can` are `not`, so there is no match -- the arm is not MIS-classified as an
  allow, which would have been worse. It simply is not classified at all. And the
  REFUSAL pattern looks for refus / 401 / 403 / NO_SESSION, none of which appear
  in an arm named for the actor rather than the status.

  WHY THIS MATTERS MORE THAN A COUNTING SLIP. The verdict is gated on
  `if fails and allow and not refuse:` -> "the label is ACCURATE -- it fails as an
  OUTAGE, not as a hole". The `not refuse` half is the whole safety argument: that
  no REFUSAL arm broke, so the mutation over-gates rather than under-gates. A
  broken refusal arm named "a deactivated employee cannot read law_clients" is
  invisible to `refuse`, so it would leave `refuse` empty and the probe would
  print the reassuring sentence anyway.

  IT IS NOT WRONG TODAY AND I DROVE THAT BEFORE SAYING SO. Under mutation 3 the
  expected app defaults to stonedesk, so every SAIRNlaw session fails verification
  and it is the "can read" arms that break; the "cannot" arms still expect a
  refusal and still get one. So the conclusion holds -- reached by a classifier
  that could not have told anybody if it did not.

  SUGGESTED FIX, and it is the cheaper of the two: stop classifying by NAME and
  refuse to conclude when the classification is incomplete. One line --
  `if len(allow) + len(refuse) != len(fails): cannot(2, ...)` -- turns a silent
  understatement into a COULD NOT DRIVE, which is the third state this probe
  already uses correctly in five other places. The richer fix is to bucket on the
  asserted STATUS rather than the arm name, but that needs the suite to emit it
  machine-readably and is a change to my file, not cc's.""")

print()
print('=== PRESS-ON (1): the worktree mutation is SAFE, and the uniqueness guard is')
print('                 the whole safety -- confirmed, including the case cc asked about')
src = io.open(SUBJECT, encoding='utf-8', newline='').read()
target_block = src.count("TARGET = (")
line('the mutation target is a THREE-LINE block, not one line',
     "'law_clients': 'sairnlaw'" in src and "'law_deadlines': 'sairnlaw'" in src)
line('it asserts count(TARGET) != 1 and refuses', 'src.count(TARGET) != 1' in src)
line('the refusal is cannot() + return, not a warning',
     "cannot(3, 'the SD_GATE_APP block is not where the mutation expects it" in src)
line('worktree removal is in a finally with --force',
     'finally:' in src and "'worktree', 'remove', '--force'" in src)
line('the cannot() path is INSIDE the try, so cleanup still runs',
     src.find('cannot(3,') > src.find('    try:'))

print("""
  CONFIRMED ON BOTH HALVES cc ASKED ABOUT. A PARTIAL match cannot slip through,
  and the reason is structural rather than lucky: TARGET is a single literal
  containing all three entries with their exact indentation and newlines, so
  str.count either finds that whole block or finds nothing -- there is no partial
  to match. And the count==1 assertion is genuinely the whole safety, which is the
  right shape: it is tool-bugs item 11's preferred form, count-and-refuse rather
  than `in`-and-proceed, in a file that mutates real code.

  THE CLEANUP IS CORRECT IN THE CASE THAT USUALLY GETS MISSED. cannot(3, ...) is
  followed by `return` from INSIDE the try, so the finally still removes the
  worktree -- the failure mode where a probe refuses to run and leaves a worktree
  behind does not happen here. The earlier cannot() for a worktree that could not
  be created sits before the try, where there is nothing to clean up.""")

print()
print('=== PRESS-ON (3): NOT INDEPENDENT, AND CC IS RIGHT TO SAY SO -- BUT I AM THE')
print('                 WRONG REVIEWER FOR IT AND THAT IS THE ANSWER')
print("""
  cc discloses that its press-on (2) verdict -- that the sibling extractor's
  uniqueness and block-comment handling are the right bar -- is a judgement about
  extraction shapes cc itself wrote and fixed the same night, and asks for
  somebody who has not written one.

  I AM ALSO THE WRONG PERSON, AND MORE SO. I wrote three extraction-style probes
  in the last day, hit the same uniqueness class four times, and then authored
  tool-bugs item 11 which says in terms that count-and-refuse is the standard. If
  I endorse cc's bar I am endorsing the rule I just wrote into the platform's own
  register. That is not independence, it is an echo.

  SO THE ANSWER IS PROCEDURAL RATHER THAN TECHNICAL: press-on (2) needs hank or
  cody. Recorded as its own open-work row rather than resolved here. What I CAN
  say without claiming independence is narrower and worth having: the bar is
  cheap. Two lines per extractor, and the four instances in one day are on the
  record with dates, so whoever rules on it is ruling on measured recurrence
  rather than on anybody's taste.""")

print()
print('=== PRESS-ON (4) AND THE TWO FINDINGS CC RAISED: both stand, and the second')
print('                 is a better catch than its LOW label suggests')
print("""
  cc's own finding -- that the re-aimed mutation anchor ends in a COMMA, so it
  depends on law_trusttx not being the LAST entry in the table -- is correct and
  is the same positional dependency the re-aim was meant to escape, one step
  smaller. cc labels it LOW and requiring no change, which is defensible today.

  I WOULD RATE THE PATTERN HIGHER THAN THE INSTANCE, and the reason is on the
  record: this is the FOURTH anchor-positional failure in two days -- the
  SELF_EXCLUDED mutation that matched only while its entry was last, the
  route-record mutation that went ANCHOR-2 when an unrelated commit duplicated a
  line, this one, and the original of this one. Tool-bugs item 11 exists because
  of that run. An anchor whose validity depends on where its target sits in a list
  is the specific shape, and 'not last today' is the same kind of assurance as
  'unique today'.

  AND THE PROBE'S OWN HANDLING OF IT IS THE RIGHT MODEL, which is worth saying as
  loudly as the finding: it reported the unplantable mutation as a FAILURE rather
  than a skip, which is the only reason the original was caught in the hour it was
  created. A harness that skipped it would have gone green on a control testing
  nothing -- and that is the difference between this probe and the two that went
  silent for a day each.""")

print()
print('=== CHECKED AND CORRECT ===')
print("""  * FIVE arms assert their own subject was FOUND before judging anything, and the
    count is right -- I counted the cannot() call sites rather than trusting the
    number, which is what cc's press-on (4) tells the reader to do. cc had first
    written FOUR, counted, corrected to FIVE, and LEFT THE CORRECTION VISIBLE.
    That is the practice worth copying, not the arithmetic.
  * the mutation runs in a throwaway git worktree and never touches the clone --
    checked by reading the worktree path handling, and the repo's own copy of
    api/sd-data.js is not written by any path in the file.
  * press-on (3) drives a REAL mutation of REAL serving code rather than reasoning
    about it, which is the distinction most of these probes get wrong in the other
    direction.
  * the verdict on the phase-2 gate itself is not overstated anywhere I can find:
    it says the mutation over-gates, and it does.""")

parity = io.open(__file__, encoding='utf-8', newline='').read()
print()
print('  quote parity of this file (tool-bugs item 3): single=%d double=%d'
      % (parity.count("'") % 2, parity.count('"') % 2))
print()
print('1 finding. Report-only: exit 0 by design.')
print()
sys.exit(0)
