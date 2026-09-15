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
    if not os.path.isfile(INDEX):
        return None
    out = []
    for i, line in enumerate(_text(INDEX).split('\n'), 1):
        s = line.strip()
        if s.startswith('|') and s.count('|') >= 6:
            out.append((i, s))
    return out


def _paused_docs():
    """Files that declare themselves a pause. A paused mechanism is an accepted
    risk wearing a filename, and it is the shape most likely to be forgotten --
    nothing in the index has to mention it at all."""
    ls = subprocess.run(['git', '-C', REPO, 'ls-files', 'docs/*PAUSED*',
                         'docs/*paused*'], capture_output=True, text=True, encoding='utf-8', errors='replace')
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


def audit():
    rows = _rows()
    if rows is None:
        return None
    invokers = _invokers()
    found = []
    for lineno, row in rows:
        if not ACCEPTED.search(row):
            continue
        cells = row.split('|')
        status = cells[3] if len(cells) > 3 else ''
        if CLOSED_STATUS.search(status):
            continue
        subject = cells[2].strip() if len(cells) > 2 else ''
        verdict, tools = classify(row, invokers)
        found.append({'where': 'index:%d' % lineno, 'subject': subject[:150],
                      'verdict': verdict, 'tools': tools})
    for doc in _paused_docs():
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
    if bad:
        print('  %d of %d fixtures misclassified -- the real numbers below would '
              'be meaningless. Fix the criteria first.' % (bad, len(cases)))
    else:
        print('  all %d fixtures classified correctly, including BOTH directions '
              '(a tool that is invoked and one that is not).' % len(cases))
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
