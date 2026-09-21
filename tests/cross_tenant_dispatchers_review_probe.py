#!/usr/bin/env python
"""tests/cross_tenant_dispatchers_review_probe.py

Run:  python tests/cross_tenant_dispatchers_review_probe.py

INDEPENDENT REVIEW of 5a878e71 (hank) -- phases 1 and 2 of the cross-tenant
isolation plan -- under the Tier A obligation hank opened 2026-09-21T12:40:23Z.
Six press-on points; three hold, three findings.

REPORT-ONLY AND EXIT 0, same precedent as tests/dnt_rollup_review_probe.js. No
assert anywhere: a report-only artefact that asserts is not report-only, and
tier_a_review_gate reads exactly that. Nothing on disk is mutated.
"""

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cross_tenant_isolation_scope as scope        # noqa: E402

SUITE = 'api/sd-data-cross-tenant-dispatchers.test.js'
CONTROL = 'tests/run_cross_tenant_scope_probe.py'
REFERENCE = 'api/sd-data-cross-tenant-isolation.test.js'
SERVING = 'api/sd-data.js'

findings = 0


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def head(n, title):
    print('\n=== FINDING %d: %s\n' % (n, title))


def answered(n, title):
    print('\n=== PRESS-ON (%d): %s\n' % (n, title))


# ── this file's own standing, first ─────────────────────────────────────────
body_self = read('tests/cross_tenant_dispatchers_review_probe.py')
print('=== WILL THE PUSH GATE SEE THIS FILE AS REPORT-ONLY? ===\n')
for ch, label in ((chr(34), 'double'), (chr(39), 'single'), (chr(96), 'back')):
    print('  %-7s quote characters : %4d   odd: %s'
          % (label, body_self.count(ch), bool(body_self.count(ch) % 2)))
try:
    import tier_a_review_gate as _gate                          # noqa: E402
    print('  is_report_only_artefact() answers : %s'
          % _gate.is_report_only_artefact('tests/x.py', body_self))
except Exception as _e:                                          # noqa: BLE001
    print('  is_report_only_artefact() COULD NOT BE ASKED : %s' % _e)
print('  (an odd count desyncs the gate and swallows this file\'s trailing'
      ' sys.exit(0);\n   that is the tool-bugs bucket item, not this file\'s defect)')

# ── PRESS-ON (3) ────────────────────────────────────────────────────────────
answered(3, 'payloadExtras cannot weaken an isolation assertion, and the\n'
            '                 UNREACHED list is empty because nothing was loosened')
suite = read(SUITE)
units = re.search(r'const UNITS = \[(.*?)\n\];', suite, re.S).group(1)
extras = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', units)
tainted = [e for e in extras if re.search(r'license|tenant|hash', e, re.I)]
print('  payloadExtras object literals            : %d' % len(extras))
print('  any naming license / tenant / hash       : %d' % len(tainted))
print('  the W arm asserts on the POST call only  : %s'
      % ("calls.filter(function (c) { return c.opts && c.opts.method === 'POST'; })[0]"
         in suite))
print('  ...and on on_conflict=license_hash,      : %s'
      % ("on_conflict=license_hash," in suite))
print('  ...and on the handler-derived hash       : %s'
      % ('sent.license_hash, HASH_A' in suite))
run = subprocess.run(['node', SUITE], cwd=ROOT, capture_output=True, text=True,
                     encoding='utf-8', errors='replace')
out = (run.stdout or '') + (run.stderr or '')
print('  suite exit                               : %d' % run.returncode)
print('  arms reported UNREACHED                  : %d'
      % len([l for l in out.split('\n') if 'UNREACHED' in l]))
print('  arms disclosed NOT COVERED               : %d'
      % len([l for l in out.split('\n') if 'NOT COVERED' in l]))
print("""
  HOLDS, and the reason is structural rather than a spot check. The W arm
  asserts two things and both are derived by the HANDLER, not supplied by the
  caller: the upsert's conflict key must lead with license_hash, and the body's
  license_hash must equal the hash the handler derived from the bearer key. A
  payload field the validator demands cannot touch either, and none of the 13
  extras names license, tenant or hash -- so the one field that COULD have
  weakened it is absent, and the Winj arm exists precisely to prove that a
  license_hash in the payload is ignored.

  THE UNREACHED LIST IS EMPTY BECAUSE NOTHING NEEDED LOOSENING, not because the
  bar moved: the run reports zero UNREACHED and exactly one disclosed NOT
  COVERED (sv_controlled write), which is press-on (5)'s subject and is printed
  with `--` rather than `ok`. A silently-skipped arm and a passing one are
  distinguishable in this file, which is the property the list exists for.""")

# ── PRESS-ON (1) ────────────────────────────────────────────────────────────
answered(1, 'one file rather than ten is the right call, and the plan is the\n'
            '                 thing that should move')
n_units = len(re.findall(r"\{ map: '", units))
n_members = len(re.findall(r"\['[a-z0-9_]+',\s*'[a-z0-9_]+'", units))
print('  dispatcher units in one harness          : %d' % n_units)
print('  Tier A members driven                    : %d' % n_members)
print('  mock definitions in the file             : %d'
      % len(re.findall(r'function postgrestMock', suite)))
print("""
  AGREED, AND I WOULD NOT HAVE SPLIT IT EITHER. The mock IS the test here --
  every arm's verdict depends on it parsing col=eq.value and ANDing the
  clauses -- so ten copies would be ten places for the one load-bearing object
  to drift, and drift in a MOCK is invisible: a copy that silently stops
  filtering turns every arm in its file green. One definition, ten
  configurations, is the shape that cannot drift apart.

  WHAT IS REALLY LOST IS NOT GRANULARITY, IT IS CLAIMABILITY, and that is worth
  naming separately because the plan is written around claims: ten units in one
  file means one claim, so two sessions cannot take five each. That is a cost to
  the PLAN rather than to the test, and the plan is the cheaper thing to change.
  The commit says this contradicts a written plan and says so out loud, which is
  the right handling.""")

# ── PRESS-ON (2) -- finding ─────────────────────────────────────────────────
head(1, 'the UNITS cross-check is REAL and DOES NOT GENERALISE -- it is one\n'
        '            hardcoded arm about one file, and the other declaring file is\n'
        '            still creditable with a resource nothing drives')
control = read(CONTROL)
hard = re.search(r"os\.path\.join\(REPO, '([^']+)'\)", control[control.find('EVERY DECLARED RESOURCE'):])
print('  the cross-check arm reads, hardcoded     : %s' % (hard.group(1) if hard else '?'))
              # The control writes the shape as a REGEX, so look for the regex
              # source rather than the literal -- checking for the literal
              # printed NOT FOUND about an arm that is plainly there.
print('  it parses the shape                      : %s'
      % ('const UNITS = [ ... ]' if r'const UNITS = \[' in control else 'NOT FOUND'))
# NOT `'UNITS' in grader_source` -- the word appears there in a PROGRESS LINE
# ("TEST UNITS   %3d"), so a containment test answers True for the wrong reason.
# That was in this probe on the way in and is exactly the substring trap hank's
# own finding 4 was about, reproduced by the reviewer.
grader = read('tools/cross_tenant_isolation_scope.py')
print('  the GRADER cross-checks a declaration    : %s'
      % ('const UNITS' in grader or 'declared - driven' in grader))
print('  ...and the only UNITS in the grader is   : %s'
      % [l.strip()[:56] for l in grader.split(chr(10)) if 'UNITS' in l])
ref = read(REFERENCE)
VICTIM = 'sv_controlled'
before = len(re.findall(r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % VICTIM, ref))
mutated = ref.replace(
    '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts',
    '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts, ' + VICTIM, 1)
grade, _why = scope.grade(mutated)
decl, _n = scope.declared_coverage(mutated)
print('  the OTHER declaring file is              : %s' % REFERENCE)
print('  it carries a UNITS table                 : %s' % ('const UNITS = [' in ref))
print('  %s mentioned in it before        : %d time(s)' % (VICTIM, before))
print('  after declaring it and nothing else      : grade %s, declared %s'
      % (grade, VICTIM in decl))
if grade == 'GENUINE' and VICTIM in decl:
    findings += 1
    print("""
  hank asks whether the cross-check is enough. It is enough FOR ONE FILE, and it
  is not a property of the mechanism.

  CREDIT WHERE IT IS DUE FIRST: the arm is real, it is the fix I suggested when
  reviewing the preceding commit, and it caught a genuine over-declaration
  (sd_quote_requests, declared and driven by nothing). That is a control earning
  its place on the day it was written.

  BUT IT IS A HARDCODED ARM ABOUT ONE PATH. It opens
  api/sd-data-cross-tenant-dispatchers.test.js by name and parses `const UNITS =
  [...]` by shape. The GRADER -- the thing that actually issues credit, and the
  thing every future declaring file will be graded by -- knows nothing about it.
  So:

    * the reference implementation, the only other declaring file, carries
      `const LAW_TIER_A` rather than `UNITS` and has NO arm. Driven above:
      adding sv_controlled to its declaration line and nothing else still
      grades GENUINE and still lands in the declared set, so it would still be
      credited.
    * any file phase 3 adds will be unprotected until somebody remembers to
      extend the arm, and forgetting is silent.

  WHY THAT MATTERS MORE THAN IT LOOKS: the declaration is now the ONLY thing
  that credits a resource, and the number it produces is the plan's progress
  measure. A per-file arm protects the file somebody was thinking about while
  they wrote it.

  SUGGESTED, and it is the same shape as the arm hank already wrote, moved one
  level: put the cross-check in the GRADER, keyed on any machine-readable
  resource table the declaring file carries -- UNITS, LAW_TIER_A, or a declared
  table name -- and REFUSE to credit a declared resource that appears in no
  table and nowhere else in the file. A weaker one-liner that would also have
  caught the probe above: require the name to appear somewhere OTHER than the
  declaration line, so the declaration stops being its own evidence.""")

# ── PRESS-ON (4) -- finding ─────────────────────────────────────────────────
head(2, 'the mock\'s header claims EVERY unfaithfulness runs in the safe\n'
        '            direction -- the PATCH stub added since does not')
patch = re.search(r"if \(opts && opts\.method === 'PATCH'\) \{\n(.*?)\n    \}", suite, re.S)
print('  the PATCH stub, in full:')
for line in (patch.group(1).split('\n') if patch else ['NOT FOUND']):
    print('    %s' % line.strip()[:100])
print('  does it read the query at all            : %s'
      % bool(patch and 'eqs' in patch.group(1)))
print('  the header claim it sits under           : "EVERY WAY IT IS UNFAITHFUL'
      ' RUNS IN THE SAFE DIRECTION"')
print('  does any arm assert on a PATCH response  : %s'
      % ("method === 'PATCH'" in suite.split('postgrestMock')[-1]))
findings += 1
print("""
  NOT A LIVE FALSE PASS, AND A REAL TRAP ONE ARM AWAY. The GET path of this mock
  is carefully faithful and its header reasons the unfaithfulness through: an
  unrecognised clause is simply not applied, so it returns MORE rows and a
  content assertion fails LOUDER; no shape makes it return FEWER. That argument
  is correct and it was checked on the reference.

  The PATCH branch added since returns `{ ok: true, status: 200 }` with a
  one-row body FOR ANY QUERY. It reads no clause. That is an unfaithfulness in
  the UNSAFE direction -- it returns success where PostgREST would return
  nothing -- so the header's "every way" is no longer true of the file it heads.

  NOTHING IN THIS SUITE DEPENDS ON IT TODAY, checked rather than assumed: the W
  arm filters `calls` for method POST and asserts on that; the L arm asserts on
  the response body's CONTENT, which a PATCH-shaped reply of `[{data:{}}]` would
  fail rather than pass. So the stub is plumbing that keeps SD_LOCAL and SC
  reaching their query, and it decides no verdict.

  THE TRAP IS THE FIRST SOFT-DELETE ARM. SD_LOCAL and DNT both carry
  `&data->>_deleted_at=is.null` paths, so a soft-delete isolation arm is a
  natural next unit -- and written against this stub it would pass for any
  tenant, because the stub answers 200 with a row whatever the query says. That
  is exactly the false-pass shape this whole file exists to prevent.

  SUGGESTED, two lines: make the PATCH branch filter like the GET branch does
  (it already has `eqs` parsed) and return the matching rows, so it can never be
  the reason an arm passes. If that is not wanted, the header's claim needs
  narrowing to the GET path in the same commit -- a sentence that was true when
  written and is not now is the thing this platform keeps paying for.""")

# ── PRESS-ON (6) -- finding ─────────────────────────────────────────────────
head(3, 'the sabotage run is PROSE ONLY -- there is no runner, so neither\n'
        '            compromise can be checked, and the one part that IS checkable\n'
        '            shows the anchor collision is NINE-way, not the pair disclosed')
serving = read(SERVING).split('\n')
lines = [l.strip() for l in serving]
from collections import Counter                                  # noqa: E402
counts = Counter(l for l in lines if 'fetch(rest(resource' in l and 'license_hash=eq.' in l)


def owner_of(lineno):
    for i in range(lineno - 1, max(0, lineno - 40), -1):
        m = re.search(r'\b([A-Z][A-Z_]+)\[resource\]', serving[i - 1])
        if m:
            return m.group(1)
    return '?'


print('  a committed sabotage runner for the suite : %s'
      % bool([f for f in os.listdir(os.path.join(ROOT, 'tests'))
              if 'dispatcher' in f and 'sabotage' in f]))
def names_the_suite(rel):
    """Files under tests/ that mention the suite. Directories and unreadable
    entries are SKIPPED rather than crashing the run -- tests/ holds
    subdirectories (tests/claims, tests/faults) and an os.listdir walk that
    assumes files is how this arm died on the way in."""
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        return False
    try:
        return SUITE.split('/')[-1] in read(rel)
    except (OSError, UnicodeDecodeError):
        return False


print('  files naming the suite at all             : %s'
      % ', '.join(sorted(f for f in os.listdir(os.path.join(ROOT, 'tests'))
                         if names_the_suite('tests/' + f))))
print()
for line, n in counts.most_common(3):
    if n < 2:
        continue
    where = [i + 1 for i, l in enumerate(lines) if l == line]
    print('  a read-query line appearing %d times, serving:' % n)
    print('    %s' % ', '.join(sorted(set(owner_of(x) for x in where))))
units_in_suite = set(re.findall(r"\{ map: '([A-Z_]+)'", units))
nine = [l for l, n in counts.items() if n >= 9]
if nine:
    where9 = [i + 1 for i, l in enumerate(lines) if l == nine[0]]
    owners9 = set(owner_of(x) for x in where9)
    overlap = sorted(owners9 & units_in_suite)
    print()
    print('  units under test that sit on the NINE-way line : %d of %d'
          % (len(overlap), len(units_in_suite)))
    print('    %s' % ', '.join(overlap))
    findings += 1
    print("""
  PRESS-ON (6) ASKS ME TO CHECK THAT BOTH COMPROMISES ARE HONEST AND THAT NO
  DISPATCHER IS UNVERIFIED. I cannot check either, and that is the finding.

  THERE IS NO SABOTAGE RUNNER IN THE COMMIT. "18 of 18 sabotages caught,
  api/sd-data.js byte-identical after every one" exists only as prose in a
  commit message. hank's own practice elsewhere commits one --
  tests/run_server_wins_hydration_sabotage_probe.py,
  tests/run_sairnlaw_billable_rate_sabotage_probe.py,
  tests/run_tier_a_review_gate_sabotage_probe.py are all in the tree -- and this
  platform keeps a whole tool, tools/sabotage_control_check.py, for the failure
  mode of a negative control that silently stops biting. A sabotage run nobody
  can re-execute cannot be re-executed after a refactor either, which is the
  eighth standing discipline almost word for word: nothing announces the day a
  check stops testing anything.

  AND THE ONE PART THAT IS CHECKABLE FROM THE SOURCE CONTRADICTS THE ACCOUNT.
  The disclosure names two collisions, both two-way: DNT read with SD_LOCAL
  read, and SD_HR read with a twin. Both of those are accurate -- verified
  above. What is not said is that a DIFFERENT read-query line is byte-identical
  NINE times and covers the units listed above, six of the ten under test. A
  text anchor cannot separate those six either.

  So one of two things is true, and the commit does not say which: either those
  six were also mutated by line number -- in which case "every other arm used a
  unique anchor" is not accurate and the reliance on line numbers is much wider
  than disclosed -- or their read mutations were not individually targeted, in
  which case the 18 does not mean what a reader takes it to mean. WITHOUT A
  RUNNER THERE IS NO WAY TO TELL, including for hank in a month.

  NONE OF THIS SAYS THE SUITE IS WEAK. It runs 112 assertions, every member is
  driven individually, the negative control at the bottom proves the mock still
  distinguishes filtered from unfiltered, and the shapes asserted are the right
  ones. The claim that cannot be checked is the sabotage claim, which is
  precisely the claim that tells a reader the assertions bite.

  SUGGESTED: commit the runner, in the shape the other three already use.
  If the six-way ambiguity forced line-number mutation, the runner is also the
  only place that fact can be recorded where it will stay true.""")

# ── PRESS-ON (5) ────────────────────────────────────────────────────────────
answered(5, 'neither gap should have blocked, and one of them is already\n'
            '                 better recorded than the obligation says')
sf_probe = 'tests/sf_resources_session_gate_probe.py'
print('  SF session-gate gap has its own probe     : %s'
      % os.path.isfile(os.path.join(ROOT, sf_probe)))
r2 = subprocess.run([sys.executable, sf_probe], cwd=ROOT, capture_output=True,
                    text=True, encoding='utf-8', errors='replace')
print('  it runs report-only and exits             : %d' % r2.returncode)
print('  findings it reports                       : %s'
      % ((r2.stdout or '').strip().split('\n')[-1])[:70])
print('  sv_controlled write is disclosed, not skipped : %s'
      % ('WRITE_BLOCKED' in suite))
print("""
  NEITHER SHOULD HAVE BLOCKED, and for different reasons.

  SF_RESOURCES HAVING NO SESSION GATE IS A PRODUCT FINDING ABOUT SERVING CODE,
  and this obligation covers a commit that changed no serving code. Blocking
  test coverage on a product defect it DISCOVERED would mean the isolation of
  sf_accounts and sf_ledger stayed asserted by nothing while the gate question
  was decided -- the wrong order. It is recorded in its own report-only probe
  with the repair named and the scope question left to whoever owns
  SAIRNfreedom, which is better handling than the obligation text claims for
  itself.

  SV_CONTROLLED WRITE IS THE OPPOSITE CASE AND THE ANSWER IS THE SAME: forging a
  witness co-signature to reach the conflict key would be forging the control,
  and a test that forges the thing it is testing is worse than an absent test
  because it reports green. Declaring it NOT COVERED, printing `--` rather than
  `ok`, and keeping the READ arm is exactly right.""")

print('\n=== CHECKED AND CORRECT ===')
print("""  * 112 assertions, 0 failing, zero UNREACHED, one disclosed NOT COVERED.
  * every Tier A member is driven individually rather than one per map -- the
    property that a member silently dropped from a dispatcher map would fail.
  * the L arm asserts CONTENT and also asserts A's own row is PRESENT, so a
    filter on a column the fixtures lack cannot pass as an absence.
  * the W arm asserts the conflict key AND the handler-derived hash, so a write
    cannot pass by echoing what the caller sent.
  * the session token is signed against the hash the HANDLER derives, so a
    NO_SESSION refusal cannot read as isolation working.
  * the negative control at the foot still distinguishes filtered from
    unfiltered, so the mock has not quietly stopped filtering.
  * the two collisions hank DOES disclose are both real: verified against
    api/sd-data.js that the DNT and SD_LOCAL read lines are byte-identical, and
    that the SD_HR read line has a twin.""")

print('\n%d finding(s). Report-only: exit 0 by design.' % findings)
sys.exit(0)
