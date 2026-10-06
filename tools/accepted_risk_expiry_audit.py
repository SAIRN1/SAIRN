"""accepted_risk_expiry_audit.py -- does each accepted risk have an expiry that
can actually fire, or is it quietly becoming permanent?

    python tools/accepted_risk_expiry_audit.py
    python tools/accepted_risk_expiry_audit.py --json
    python tools/accepted_risk_expiry_audit.py --selftest

── NOT tools/accepted_risk_scan.py, AND THE DIFFERENCE IS THE WHOLE POINT ────
That tool asks whether an acceptance REACHED A REGISTER AT ALL -- it finds risks
weighed and accepted inside a source comment and recorded nowhere central, the
shape that got `api/sairncash/portal.js` read as an unrecognised gap twice in one
afternoon. It looks at code and asks about documentation.

This one starts where that one finishes. It reads the acceptances that ARE
centrally recorded and asks whether their EXPIRY can ever fire. The two are
complementary and the population barely overlaps: an acceptance this tool can see
is by definition one that tool would already call recorded.

Checked before writing, per Check 0e -- the near-miss was real, the name was
close enough that it should have been found by the first search and was not.

── THE QUESTION, WHICH IS NOT "IS THIS RISK REAL" ────────────────────────────
Every row this reads was a GOOD DECISION when it was made. Accepting a risk with
a named trigger is correct engineering and this tool does not second-guess one.

What it asks is narrower and entirely mechanical: **when the trigger fires, is
there anything that would notice?**

An accepted risk has three parts and only the first is ever written down
reliably:

  1. the decision            -- always present, that is what the row is
  2. the EXPIRY CONDITION    -- "re-check the moment X happens"
  3. something that EVALUATES that condition, on a cadence, without being asked

A risk with (1) and (2) but not (3) is not monitored. It is remembered, which is
a different thing and has a half-life. This platform has already written the
general version of that down, in `.claude/skills/sairn-guardian-v2/SKILL.md`:
*"A tool that exists is not a mechanism; a tool that RUNS is."* -- said about
`sairn_app_map_check.py`, which was built precisely so a seventh correction could
not happen, then never invoked again until the seventh correction happened.

── THE CASE THAT PROMPTED IT ─────────────────────────────────────────────────
`supabase_admin`'s default ACL grants `anon` and `authenticated` FULL CRUD on
tables it creates. Accepted 2026-08-26 as a monitored risk, on ownership
evidence: 100% of `public` was owned by `postgres` across 251 tables, so the
entry had never fired. That was a real measurement and the acceptance was sound.

It is also the best-instrumented item of its kind here, and even it shows the
gap. `tools/ownership_evidence_drift.py` was built 2026-09-14 and is RED: there
are 380 tables now, **129 created since anybody looked**, and the tool is careful
to say that is a LOWER BOUND and is NOT a claim the ACL has fired. But the
trigger the row actually names -- "the moment any object in `public` is created
by anything other than the SQL editor running as `postgres`" -- **cannot be
evaluated from any clone at all.** It needs one `SELECT` run by a human with
database access. So the monitor measures a PROXY for the trigger and reports that
nobody has looked; it can never report that the trigger fired.

That is the best case. This tool exists to find the rest.

── WHAT IT CLASSIFIES, AND THE HONEST DIRECTION OF ITS ERROR ─────────────────
  RUNNING      a trigger is stated, a named tool evaluates it, and something
               invokes that tool (report-only registry, push gate, or tests/)
  UNINVOKED    the tool exists and nothing runs it -- the app-map failure
  MANUAL       a trigger is stated, and no tool can evaluate it. It needs a
               person. This is not automatically wrong -- some conditions are
               genuinely outside a clone -- but it should be a KNOWN choice
  UNCONDITIONAL no expiry condition is stated at all. This is the finding

IT OVER-REPORTS ON PURPOSE. A row that names its trigger in prose this tool
cannot parse is reported as UNCONDITIONAL and costs one edit to correct. A row
that is genuinely unconditional and goes unreported costs an accepted risk
becoming permanent with nobody able to say when that happened. The error is
pushed in the cheap direction deliberately, and the counts below are a READ-LIST
rather than a defect count.

── WHAT IT CANNOT SEE, NAMED RATHER THAN IMPLIED ─────────────────────────────
  * It reads ROWS, not reality. A row saying a tool runs nightly is taken at its
    word for the trigger text; whether the tool is INVOKED is checked against
    real files, but whether it actually TESTS the trigger is not checkable here.
  * Accepted risks recorded anywhere other than the index and the PAUSED docs
    are invisible to it. A decision made only in a commit message is not here.
  * It cannot tell a well-chosen MANUAL from a lazy one. Naming it is the point.
  * REPORT ONLY, exit 0 on findings. It measures a documentation property, and
    refusing a push over somebody else's un-instrumented decision would be a gate
    nobody keeps.
"""
import io
import json
import os
import re
import subprocess
import sys

# ── THIS AUDIT DIED AFTER DOING ITS WORK (fixed 2026-10-05) ────────────────
# `main()` prints its per-verdict section headers with box-drawing rules
# (`print('── %s ────…')`, the same rules every tool in this repo uses). On a
# cp1252 console that raised UnicodeEncodeError and exited 1 -- and it raised
# it AT THE REPORTING STAGE, after the whole audit had run, so the exit status
# said "found something" and the findings were never printed. A tool that
# computes the right answer and cannot say it is indistinguishable from one
# that failed.
#
# Found by driving all 296 tools/*.py under forced PYTHONIOENCODING=cp1252 in
# a scratch copy of the tree: 1 crash, this one.
#
# THE STREAM IS RECONFIGURED, NOT THE OUTPUT TEXT -- the same fix and the same
# reason as `tools/register_feed_gate.py`'s: ASCII-ing this file would fix one
# file and leave the pattern in the other ~295. stderr too, because a tool
# whose ERROR cannot be encoded fails at the one moment it is trying to
# report.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')

# A row that DECIDES to live with something, rather than one that fixed it.
ACCEPTED = re.compile(
    r'accepted risk|deliberately not fixed|deliberately not closed|'
    r'not being fixed|held open on purpose|accept-and-monitor|monitored risk|'
    r'standing decision|permanently declined|PAUSED|paused as of|on hold|'
    r'deliberately deferred|deferred on purpose',
    re.I)

# ── ROWS THAT ARE ALREADY CLOSED ARE NOT OPEN ACCEPTED RISKS ────────────────
# Added after a hand-check of the first real run: `index:345` was reported as an
# un-expiring accepted risk and its status cell reads "CLOSED 2026-09-04". It
# matched only because the EVIDENCE cell discusses a tripwire and a deliberate
# non-fix -- the words survive the fix that closed them. Filtering on the STATUS
# cell rather than the whole row is the principled version of that, not a tune to
# the one example: a closed row's history is supposed to still describe what was
# accepted at the time.
CLOSED_STATUS = re.compile(
    r'^\s*(?:~~)?\s*(?:\*\*)?\s*(?:CLOSED|FIXED|BUILT|DONE|RESOLVED|CONFIRMED AND CLOSED)\b',
    re.I)

# An EXPIRY CONDITION: the row says what would make this stop being acceptable.
# Deliberately demanding -- a bare "revisit later" is not a condition.
TRIGGER = re.compile(
    r're-?check (?:this )?(?:the moment|when|if|as soon as)|'
    r'(?:named|with a) trigger|'
    r'the moment (?:any|anything|somebody|someone|a|the)|'
    r'reopen(?:ing)? (?:this )?(?:if|when)|'
    r'until (?:somebody|someone|a human|michael|the|a) \w+|'
    r'stops being (?:true|acceptable)|'
    r'the (?:whole )?alarm is|'
    r'precondition it must clear|'
    r'trigger(?:s)? (?:a )?re-?check',
    re.I)

# A tool the row names as the thing that would notice.
TOOL = re.compile(r'`(tools/[\w./-]+\.(?:py|js)|tests/[\w./-]+\.(?:py|js)|sql/[\w./-]+\.sql)`')


def _text(path):
    return io.open(path, encoding='utf-8', errors='replace').read()


def _invokers():
    """Everything that can cause a tool to run without being asked.

    Read from the real files rather than assumed, because "is it registered"
    is exactly the claim that went wrong for sairn_app_map_check.py.
    """
    blobs = []
    for rel in ('tools/report_only_checks.py', 'tools/sairn_push_gate_hook.py',
                '.claude/settings.json', 'tools/run_all_tests.py'):
        p = os.path.join(REPO, rel)
        if os.path.isfile(p):
            blobs.append(_text(p))
    return '\n'.join(blobs)


def _rows():
    """Index rows, or None for COULD-NOT-TELL.

    AN EMPTY ROW LIST IS None AND NOT []. The file existing is not the same as
    the file parsing: a changed table shape, a rewritten legend, a document
    moved to a different separator, and every line fails the `count('|') >= 6`
    test while `os.path.isfile` stays happily true. Measured 2026-09-27 with
    this function forced to []: the tool reported "population : 1", four
    verdict counts, and exit 0 -- against a real population of 19. A tool that
    lost the entire open-work index reported a normal-looking result.

    Same shape as `git log --not --remotes` with no positive rev, which walked
    nothing, exited 0, printed nothing, and made push_retry.py's guard refuse
    every amend forever (tools/push_retry.py:142). Exit 0 with empty output is
    a third state, never an answer.
    """
    if not os.path.isfile(INDEX):
        return None
    out = []
    for i, line in enumerate(_text(INDEX).split('\n'), 1):
        s = line.strip()
        if s.startswith('|') and s.count('|') >= 6:
            out.append((i, s))
    return out or None


def _paused_docs():
    """Files that declare themselves a pause, or None if git could not be asked.

    A paused mechanism is an accepted risk wearing a filename, and it is the
    shape most likely to be forgotten -- nothing in the index has to mention it
    at all.

    THE RETURN CODE WAS NOT CHECKED AT ALL, which is the worst version of the
    empty-walk shape rather than a milder one: a `git ls-files` that failed to
    launch left `ls.stdout` empty and this returned [], so "git is broken" and
    "there are no paused documents" were the same answer and the tool carried
    on and printed a population. Unlike a ZERO row count, ZERO PAUSED DOCS IS A
    LEGITIMATE STATE, so the two cases genuinely differ and are now separate:
    rc != 0 is None and refuses; an empty list is [] and is an answer.
    """
    ls = subprocess.run(['git', '-C', REPO, 'ls-files', 'docs/*PAUSED*',
                         'docs/*paused*'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if ls.returncode != 0:
        return None
    return [f for f in ls.stdout.split('\n') if f.strip()]


def classify(body, invokers):
    tools = TOOL.findall(body)
    has_trigger = bool(TRIGGER.search(body))
    if not has_trigger:
        return 'UNCONDITIONAL', tools
    if not tools:
        return 'MANUAL', tools
    # A tool is INVOKED if anything that runs on its own names it. tests/ files
    # are discovered by the runner, so being under tests/ is itself invocation.
    for t in tools:
        base = os.path.basename(t)
        if t.startswith('tests/') or base in invokers:
            return 'RUNNING', tools
    return 'UNINVOKED', tools


# ── EXTRACTED FROM audit() SO IT CAN BE ABLATED (2026-10-05) ───────────────
# `ACCEPTED` and `CLOSED_STATUS` were the only two of this tool's rules that
# dead_rule_sweep reported DEAD TO ITS OWN EVIDENCE, and the cause was not a
# weak criterion -- it was that the selftest below hands fixture strings
# straight to classify(), which never sees either rule. The row SELECTION was
# four lines inline in audit(), reachable only by reading the real open-work
# index, so neutralising either pattern left every fixture arm green.
#
# Reading the index is exactly what a fixture lock must not depend on (the
# eighth discipline: evidence that changes when anybody pushes is evidence
# nobody decided to change). So the decision is a function, and the lock drives
# the function.
def is_open_accepted_risk(row):
    """Does this index row DECIDE to live with something, and is it STILL open?

    Two independent conditions and both are load-bearing:
      ACCEPTED       -- the row decides rather than fixes
      CLOSED_STATUS  -- ...and its STATUS cell does not say it is closed

    The status cell, not the whole row: `index:345` was reported as an
    un-expiring accepted risk while its status read "CLOSED 2026-09-04",
    because the EVIDENCE cell still discusses the tripwire and the deliberate
    non-fix. The words survive the fix that closed them.
    """
    if not ACCEPTED.search(row):
        return False
    cells = row.split('|')
    status = cells[3] if len(cells) > 3 else ''
    return not CLOSED_STATUS.search(status)


def audit():
    rows = _rows()
    if rows is None:
        return None
    invokers = _invokers()
    found = []
    for lineno, row in rows:
        if not is_open_accepted_risk(row):
            continue
        cells = row.split('|')
        subject = cells[2].strip() if len(cells) > 2 else ''
        verdict, tools = classify(row, invokers)
        found.append({'where': 'index:%d' % lineno, 'subject': subject[:150],
                      'verdict': verdict, 'tools': tools})
    paused = _paused_docs()
    if paused is None:
        return None
    for doc in paused:
        p = os.path.join(REPO, doc)
        if not os.path.isfile(p):
            continue
        body = _text(p)
        verdict, tools = classify(body, invokers)
        found.append({'where': doc, 'subject': '(a PAUSED mechanism)',
                      'verdict': verdict, 'tools': tools})
    return found


def selftest():
    """Lock the criteria against synthetic fixtures before believing any real
    number. Built because a checker that has only ever returned a plausible
    answer on real data has not been shown to discriminate at all -- three tools
    on this platform were wrong in exactly that way and each was caught by a
    control built to make it fail on purpose."""
    inv = 'report_only_checks: ownership_evidence_drift.py\n'
    cases = [
        ('accepted risk. re-check this the moment anything changes. '
         '`tools/ownership_evidence_drift.py`', 'RUNNING'),
        ('accepted risk. re-check this the moment anything changes. '
         '`tools/no_such_tool_exists.py`', 'UNINVOKED'),
        ('accepted risk. re-check this the moment a human looks.', 'MANUAL'),
        ('accepted risk. we will get to it.', 'UNCONDITIONAL'),
        ('accepted risk, revisit later sometime', 'UNCONDITIONAL'),
        # Both directions on the trigger, so "it finds triggers" is not
        # satisfied by a classifier that says MANUAL to everything.
        ('deliberately not fixed. the whole alarm is a single non-postgres row.',
         'MANUAL'),
        ('PAUSED. the precondition it must clear is a quiet week. '
         '`tests/push_gate/check4_probe.py`', 'RUNNING'),
    ]
    bad = 0
    for body, want in cases:
        got, _ = classify(body, inv)
        mark = 'ok  ' if got == want else 'FAIL'
        if got != want:
            bad += 1
        print('  %s expected %-13s got %-13s | %s' % (mark, want, got, body[:58]))
    print('')

    # ── THE ROW SELECTION, WHICH NO ARM ABOVE TOUCHES (2026-10-05) ─────────
    # Every case above calls classify() directly, so ACCEPTED and
    # CLOSED_STATUS -- the two rules that decide WHICH rows are accepted risks
    # at all -- were dead to this tool's own evidence. These three arms drive
    # is_open_accepted_risk() on hand-built rows shaped like index rows, and
    # each is written so that neutralising ONE of the two patterns turns ONE
    # arm red.
    print('  the ROW SELECTION, on hand-built rows (not the real index):')
    OPEN_ROW = ('| **Platform** | a thing nobody fixed | **ACCEPTED RISK, '
                'MONITORED** | Michael | - | re-check this the moment anybody '
                'adds a second granting role | S |')
    CLOSED_ROW = ('| **Platform** | a thing somebody fixed | **CLOSED '
                  '2026-09-04** | Hank | - | it was an accepted risk and the '
                  'tripwire is still described here | S |')
    PLAIN_ROW = ('| **Platform** | an ordinary open item | **FOUND 2026-09-20, '
                 'NOT FIXED** | unassigned | - | nothing here decides to live '
                 'with anything | M |')
    sel = [
        ('ACCEPTED fires: a row that DECIDES, with an open status', OPEN_ROW,
         True),
        ('CLOSED_STATUS fires: the SAME decision, status cell says CLOSED',
         CLOSED_ROW, False),
        ('neither fires: an ordinary open row is not an accepted risk',
         PLAIN_ROW, False),
    ]
    for name, row, want in sel:
        got = is_open_accepted_risk(row)
        mark = 'ok  ' if got == want else 'FAIL'
        if got != want:
            bad += 1
        print('    %s expected %-5s got %-5s | %s' % (mark, want, got, name))
    print('')
    if bad:
        print('  %d of %d fixtures misclassified -- the real numbers below would '
              'be meaningless. Fix the criteria first.' % (bad, len(cases)))
    else:
        # THE COUNT NAMES BOTH GROUPS. It read `len(cases)` and printed "all 7"
        # after 10 arms had run, which understates the lock by exactly the
        # three arms added to cover the row selection -- and an understated
        # disclosure is how a gap stays invisible even when it is closed.
        print('  all %d fixtures classified correctly -- %d classifier arms '
              '(BOTH directions: a tool that is invoked and one that is not) '
              'and %d row-selection arms (one per rule, each way).'
              % (len(cases) + len(sel), len(cases), len(sel)))

    # ── AND THE INPUT, NOT JUST THE CLASSIFIER ─────────────────────────────
    # Every arm above hands a fixture string to classify(). They prove the
    # DECISION MODEL and nothing about the code that feeds it, and the two can
    # disagree completely. push_retry.py caught exactly that in itself: a
    # `git log --not --remotes` with no positive rev walked nothing, exited 0,
    # returned an empty safe-set, and its guard refused every amend forever
    # while every fixture arm still passed.
    #
    # THE SAME BLIND SPOT WAS LIVE HERE. Driven 2026-09-27 with _rows() forced
    # to []: the tool reported "population : 1" and exited 0, against a real
    # population of 19. Losing the entire open-work index looked like a result.
    print('')
    rows = _rows()
    if rows is None:
        print('  FAIL _rows() returned None on the real repo -- the open-work '
              'index is missing or no line in it parses as a table row.')
        bad += 1
    else:
        print('  ok   _rows() reads the real index: %d row(s)' % len(rows))
    paused = _paused_docs()
    if paused is None:
        print('  FAIL _paused_docs() returned None -- `git ls-files` failed.')
        bad += 1
    else:
        # ZERO IS A REAL ANSWER HERE and the arm says so rather than asserting
        # a count it cannot know. The claim is that git was ASKED.
        print('  ok   _paused_docs() asked git and got an answer: %d doc(s)'
              % len(paused))
    found = audit()
    if not found:
        print('  FAIL audit() found no accepted-risk rows at all against a real '
              'index, which is a matcher failure rather than a clean register.')
        bad += 1
    else:
        print('  ok   audit() finds %d accepted-risk decision(s) on real input'
              % len(found))

    # THE CONTROLS FOR THE FIX ITSELF. Without these, `out or None` and the
    # returncode check could both be deleted and every arm above would pass.
    g = globals()
    real_rows, g['_rows'] = _rows, lambda: None
    try:
        collapsed = audit()
    finally:
        g['_rows'] = real_rows
    if collapsed is None:
        print('  ok   CONTROL -- an unreadable index REFUSES rather than '
              'reporting a small population')
    else:
        print('  FAIL CONTROL -- an unreadable index produced %d row(s) instead '
              'of a refusal' % len(collapsed))
        bad += 1
    real_p, g['_paused_docs'] = _paused_docs, lambda: None
    try:
        collapsed = audit()
    finally:
        g['_paused_docs'] = real_p
    if collapsed is None:
        print('  ok   CONTROL -- a failed `git ls-files` REFUSES rather than '
              'reporting zero paused documents')
    else:
        print('  FAIL CONTROL -- a failed ls-files produced %d row(s) instead '
              'of a refusal' % len(collapsed))
        bad += 1
    return 2 if bad else 0


def main():
    if '--selftest' in sys.argv:
        return selftest()
    found = audit()
    if found is None:
        print('COULD NOT CHECK: docs/SAIRN-OPEN-WORK-INDEX.md is not readable, so')
        print('NOTHING WAS MEASURED. Zero findings here is not a clean result.')
        return 2
    if '--json' in sys.argv:
        print(json.dumps(found, indent=1))
        return 0

    order = ['UNCONDITIONAL', 'MANUAL', 'UNINVOKED', 'RUNNING']
    counts = dict((k, 0) for k in order)
    for f in found:
        counts[f['verdict']] = counts.get(f['verdict'], 0) + 1

    print('ACCEPTED RISKS AND WHETHER THEIR EXPIRY CAN FIRE -- report only')
    print('  population : %d accept/defer decisions found in the index and the '
          'PAUSED docs' % len(found))
    print('')
    print('  RUNNING       %2d  a trigger, a tool, and something that invokes it'
          % counts['RUNNING'])
    print('  UNINVOKED     %2d  the tool exists and NOTHING RUNS IT'
          % counts['UNINVOKED'])
    print('  MANUAL        %2d  a trigger no clone can evaluate -- needs a person'
          % counts['MANUAL'])
    print('  UNCONDITIONAL %2d  NO EXPIRY CONDITION IS STATED AT ALL'
          % counts['UNCONDITIONAL'])
    print('')
    for v in order:
        rows = [f for f in found if f['verdict'] == v]
        if not rows:
            continue
        print('── %s ─────────────────────────────────────────' % v)
        for f in rows:
            subj = re.sub(r'\*\*|`|&[a-z]+;|<br>', '', f['subject']).strip()
            print('  %-14s %s' % (f['where'], subj[:96]))
            if f['tools']:
                print('  %-14s   tool: %s' % ('', ', '.join(f['tools'][:3])))
        print('')

    print('THE COUNTS ARE A READ-LIST, NOT A DEFECT COUNT, and the tool')
    print('over-reports on purpose: a row whose trigger is phrased in prose this')
    print('cannot parse lands in UNCONDITIONAL and costs one edit. A genuinely')
    print('unconditional row going unreported costs an accepted risk becoming')
    print('permanent with nobody able to say when that happened.')
    print('')
    print('MANUAL IS NOT A FAILING GRADE. Some conditions are genuinely outside a')
    print('clone -- the supabase_admin ownership SELECT is the clearest one. What')
    print('matters is that it is a KNOWN choice rather than an assumption that')
    print('somebody is watching.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
