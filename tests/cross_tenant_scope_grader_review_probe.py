#!/usr/bin/env python
"""tests/cross_tenant_scope_grader_review_probe.py

Run:  python tests/cross_tenant_scope_grader_review_probe.py

INDEPENDENT REVIEW of c44c5bf2 (hank) -- the four grader corrections from CC's
review of 3c249d46 -- under the Tier A obligation hank opened
2026-09-21T12:19:22Z. The brief named five things to press on, hardest first,
and hank named the first one as the weakest part of the change.

── REPORT-ONLY AND EXIT 0, DELIBERATELY ─────────────────────────────────────
Same precedent as tests/dnt_rollup_review_probe.js and
tests/sairnlaw_invoiced_sync_review_probe.js: a review finding on another
agent's file, and turning it into a failing suite blocks every other session's
push on a defect they did not write. It PRINTS, it does not gate. I am not
fixing anything -- I hold a review claim, not the file.

── NOTHING ON DISK IS TOUCHED ───────────────────────────────────────────────
The declaration probe below mutates a STRING in memory, never a file. The
before/after GENUINE comparison was measured in throwaway git worktrees at
c44c5bf2 and c44c5bf2^ and the numbers are recorded here as measurements with
their commits named, because those worktrees are gone and a number nobody can
re-derive is not evidence. Every other assertion re-runs against the tree.

── WHY THE before/after CHECK HAD TO BE RUN AT THE REVIEWED COMMIT ──────────
Press-on (5) asks about "GENUINE reads 3 before and after". At HEAD it reads 49,
because hank's phases 1 and 2 (5a878e71) landed on top of the commit under
review. Running the grader at HEAD would have answered a different question and
looked like a contradiction of the brief. Stated because it is the kind of thing
that turns a correct record into an apparent lie.
"""

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cross_tenant_isolation_scope as scope        # noqa: E402

REFERENCE = 'api/sd-data-cross-tenant-isolation.test.js'
DNT_BI = 'api/dnt-bi.test.js'
COMPLAINT = 'api/sairndental/complaint-respond.test.js'
REVIEWED = 'c44c5bf2'

findings = 0


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def git(*args):
    return subprocess.run(['git'] + list(args), cwd=ROOT, capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout


def quote_parity():
    """Will tier_a_review_gate treat THIS file as the report-only artefact it is?

    It only does if _strip_code_noise() can still see the trailing sys.exit(0),
    and that scanner pairs BARE quote characters -- so an odd number of any of
    them anywhere in this file desyncs it and the exit disappears. That is a
    defect in the gate, recorded in the tool-bugs bucket; this arm exists so a
    future edit to this file is told about it here rather than by a denied push.
    """
    body = read(os.path.relpath(os.path.abspath(__file__), ROOT).replace(os.sep, '/'))
    out = {}
    for ch, label in ((chr(34), 'double'), (chr(39), 'single'), (chr(96), 'back')):
        out[label] = (body.count(ch), body.count(ch) % 2)
    return out


def head(n, title):
    print('\n=== FINDING %d: %s\n' % (n, title))


def answered(n, title):
    print('\n=== PRESS-ON (%d): %s\n' % (n, title))


# ── THIS FILE'S OWN STANDING, MEASURED FIRST ────────────────────────────────
par = quote_parity()
print('=== WILL THE PUSH GATE SEE THIS FILE AS REPORT-ONLY? ===\n')
for label in ('double', 'single', 'back'):
    cnt, odd = par[label]
    print('  %-7s quote characters : %4d   odd: %s' % (label, cnt, bool(odd)))
try:
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import tier_a_review_gate as _gate                          # noqa: E402
    _body = read(os.path.relpath(os.path.abspath(__file__), ROOT).replace(os.sep, '/'))
    print('  is_report_only_artefact() answers : %s'
          % _gate.is_report_only_artefact('tests/x.py', _body))
except Exception as _e:                                          # noqa: BLE001
    print('  is_report_only_artefact() COULD NOT BE ASKED : %s' % _e)
print("""
  If that last line is False while this file plainly ends in sys.exit(0), the
  gate has desynced on an odd quote character somewhere above and will demand an
  independent-review obligation for a report-only artefact. That is the tool's
  defect, not this file's -- but it is cheaper to keep the parity even than to
  argue with a gate, so this arm says so out loud.""")

# ── PRESS-ON (4) ────────────────────────────────────────────────────────────
answered(4, 'the three edits to files hank does not own really are ONLY the\n'
            '                 declaration comment')
diff = git('show', REVIEWED, '--', DNT_BI, COMPLAINT, REFERENCE)
changed = [l for l in diff.split('\n')
           if l[:1] in '+-' and not l.startswith(('+++', '---'))]
removals = [l for l in changed if l.startswith('-')]
blanks = [l for l in changed if not l[1:].strip()]
comments = [l for l in changed if l[1:].strip().startswith('//')]
other = [l for l in changed if l not in blanks and l not in comments]
print('  changed lines across the three files : %d' % len(changed))
print('  of those, `//` comment lines         : %d' % len(comments))
print('  of those, BLANK added lines          : %d   (a bare + with nothing on it)'
      % len(blanks))
print('  of those, anything else              : %d' % len(other))
for l in other:
    print('     %s' % l[:110])
print('  removals                             : %d' % len(removals))
print("""
  CONFIRMED. Of the %d changed lines, %d are `//` comment lines and %d are blank
  added lines inside those comment blocks -- NOTHING ELSE, and no deletions, so
  nothing executable moved. dnt-bi and complaint-respond take exactly ONE
  comment line each; the reference file takes the declaration plus the paragraph
  explaining that the line is machine-read.

  The blanks are counted SEPARATELY rather than lumped in with the comments,
  because "all of them are comment lines" would have been a slightly false
  statement -- and this arm exists to check somebody else's file mechanically
  rather than by eye, so it should not round its own numbers.""" % (len(changed), len(comments), len(blanks)))

# ── PRESS-ON (2) -- and the finding ─────────────────────────────────────────
answered(2, 'the two `none (reason)` escape hatches -- the VERDICTS are both\n'
            '                 TRUE, and one of the REASONS is not')
tiers = read('docs/CRITICALITY-TIERS.md')


def tier_of(name):
    for line in tiers.split('\n'):
        if line.strip().startswith('| `%s`' % name):
            m = re.search(r'\|\s*\*\*([ABC])\*\*\s*\|', line)
            return m.group(1) if m else '?'
    return 'no row'


for r in ('dnt_complaints', 'sairndental_bi_tokens', 'dnt_charges', 'dnt_patients'):
    print('  %-24s tier %s' % (r, tier_of(r)))
comp = read(COMPLAINT)
print('  complaint-respond\'s isolation arm keys on dnt_complaints (Tier B): %s'
      % bool(re.search(r"license_hash scoping.*complaint_id", comp)))
print('  ...so it credits no Tier A resource, and `none` is TRUE.')
dnt = read(DNT_BI)
print('  dnt-bi\'s cross-practice arm is about sairndental_bi_tokens          : %s'
      % ('one practice cannot revoke another practice token' in dnt))
print('  ...which has NO row in CRITICALITY-TIERS.md, so not Tier A. `none` is TRUE.')

# THE REASON, as opposed to the verdict.
# CONTAINMENT, NOT A REGEX, AND THE FIRST VERSION OF THIS ARM IS WHY. The source
# asserts on /license_hash=eq\.LIC-HASH-1/ -- a LITERAL backslash before the dot
# -- and the regex here escaped the dot, so it could never match. It printed
# False and the finding silently did not fire: a review arm that misses its own
# subject, which is the same shape as everything else in this review. Fixed by
# looking for the three substrings rather than one pattern.
_at = dnt.find("q.table === 'dnt_patients'")
lic_arm = (_at >= 0
           and 'assert.match(read.url, /license_hash=eq' in dnt[_at:_at + 220]
           and 'assert.strictEqual(r.body.rows.length, 2);' in dnt[max(0, _at - 200):_at])
print('  dnt_patients is ALSO named by an arm that asserts license_hash=eq. on'
      ' its read: %s' % bool(lic_arm))
if lic_arm:
    findings += 1
    head(1, 'the `none` REASON hank wrote into a file it does not own\n'
            '            misdescribes that file -- the verdict survives, the justification does not')
    print("""  hank's line in api/dnt-bi.test.js reads, in full:

    // CROSS-TENANT-ISOLATION: none (the cross-practice arm here covers
    // sairndental_bi_tokens, not a Tier A resource; dnt_charges and dnt_patients
    // are named by arms about unreadable and empty datasets, which is a
    // different question)

  THE VERDICT IS RIGHT AND THE REASON IS NOT COMPLETE. `dnt_charges` really is
  named only by the unreadable/empty-dataset arms. `dnt_patients` is not: the
  arm headed "a deactivated licence keeps POLLING" asserts, in terms,

      assert.strictEqual(r.body.rows.length, 2);
      const read = REQUESTS.filter(q => q.table === 'dnt_patients')[0];
      assert.match(read.url, /license_hash=eq\\.LIC-HASH-1/);

  with the comment "And it is still only this practice's data." That is a
  tenant-scoping assertion on a Tier A resource's read -- not an unreadable or
  empty dataset, and not a different question. It is the nearest thing in that
  file to the coverage the declaration denies.

  WHY THE VERDICT STILL STANDS, checked rather than assumed: the arm cannot
  grade GENUINE under the criteria, because `seed()` puts rows under ONE
  license_hash only, so there is no second tenant and the refusal is never
  driven. The url assertion proves the FILTER IS BUILT; it does not prove a
  foreign row is excluded. So `none` is the correct verdict for the right
  reason -- just not the reason written down.

  WHY IT MATTERS AT ALL, since the number does not move. hank flagged exactly
  this risk: "if either actually does cover a Tier A resource I have just
  written a false 'none' into their file." It is not a false `none`; it is a
  reason that will mislead the next reader of somebody else's file into
  thinking dnt_patients has no license_hash assertion there, when it has one
  that is a single fixture row away from being real coverage. That is the
  cheapest arm on the whole 48-unit plan and the reason hides it.

  SUGGESTED FIX, one clause: name the third arm. "...dnt_charges is named by
  arms about unreadable and empty datasets; dnt_patients is named by the
  licence-inactive arm, which asserts the eq. clause but seeds only one tenant,
  so it is one fixture row short of genuine coverage." That turns a slightly
  wrong reason into a pointer at the cheapest fix available.""")

# ── PRESS-ON (5) ────────────────────────────────────────────────────────────
answered(5, 'GENUINE reads 3 before and 3 after, the two sets are DISJOINT,\n'
            '                 and the three after really are the reference\'s own three')
declared, none_reason = scope.declared_coverage(read(REFERENCE))
print('  the reference file DECLARES            : %s' % sorted(declared))
table = re.search(r'const LAW_TIER_A = \[(.*?)\];', read(REFERENCE), re.S)
in_table = sorted(re.findall(r"\['([a-z0-9_]+)'", table.group(1))) if table else []
print('  and its own LAW_TIER_A table holds     : %s' % in_table)
print('  declaration == table                   : %s' % (sorted(declared) == in_table))
print("""
  MEASURED IN THROWAWAY WORKTREES, not inferred:

    at %s^ (702271cc, before the fixes)  GENUINE 3
      dnt_charges, law_trusttx, dnt_patients
    at %s   (the commit under review)    GENUINE 3
      law_invoices, law_barcerts, law_opaccounts

  Three before, three after, and the sets share NOTHING. Every one of the three
  BEFORE is an artefact of the defects hank fixed: dnt_charges and dnt_patients
  were credited off api/dnt-bi.test.js's file-level grade (finding 4) and
  law_trusttx off a string inside the grader's own probe fixture (finding 3).
  Every one of the three AFTER is exactly what the reference implementation
  declares, and the declaration matches the file's own LAW_TIER_A table -- so
  nothing is counted twice: three distinct resources, one declaring file, one
  parameterised suite that really drives all three.

  So press-on (5) HOLDS in both halves it asks about.""" % (REVIEWED, REVIEWED))

# ── PRESS-ON (1) -- and the important finding ───────────────────────────────
head(2, 'PRESS-ON (1) ANSWERED: the cross-check is NOT enough. A DECLARED\n'
        '            resource that the file never drives is credited GENUINE, and the\n'
        '            declaration is its own evidence')
body = read(REFERENCE)
VICTIM = 'sv_controlled'          # Tier A, and the reference never mentions it
print('  %s appears in the reference file, before       : %d time(s)'
      % (VICTIM, len(re.findall(r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % VICTIM, body))))
mutated = body.replace(
    '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts',
    '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts, ' + VICTIM, 1)
# NO `assert` ANYWHERE IN THIS FILE, deliberately. A report-only review artefact
# that asserts is not report-only, and tier_a_review_gate's
# is_report_only_artefact() reads exactly that -- so an assert here would make
# the gate demand an independent-review obligation for a file that cannot fail.
# The anchor check is a printed refusal instead.
if mutated == body:
    print('  ** the declaration line has changed shape -- this arm did NOT run **')
grade, why = scope.grade(mutated)
decl2, _ = scope.declared_coverage(mutated)
word_hit = bool(re.search(r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % VICTIM, mutated))
print('  after adding it to the DECLARATION only (no arm, in memory only):')
print('    the file still grades                        : %s' % grade)
print('    %s is now in the declared set       : %s' % (VICTIM, VICTIM in decl2))
print('    the word-boundary name check passes          : %s' % word_hit)
credited = grade == 'GENUINE' and VICTIM in decl2 and word_hit
print('    -> all three conditions for GENUINE credit   : %s' % credited)
print('  end to end, in a throwaway worktree at %s: GENUINE 3 -> 4' % REVIEWED)
if credited:
    findings += 1
    print("""
  hank asked whether the cross-check -- "declared AND grading GENUINE" -- is
  enough, or whether the declaration should itself be checkable. Driven: it is
  NOT enough, and the reason is sharper than "nothing verifies the arm exists".

  THE DECLARATION IS ITS OWN EVIDENCE. Credit needs three things
  (tools/cross_tenant_isolation_scope.py, tests_naming()):

    1. the resource name appears in the file as a whole word
    2. the file grades GENUINE
    3. the name is in the file's CROSS-TENANT-ISOLATION: declaration

  Condition 1 is the corroboration -- it is the word-boundary check that
  finding 4's substring bug prompted. But writing the name into the declaration
  SATISFIES CONDITION 1, because the declaration is a line in the file. So 1
  and 3 are the same act, and the only independent test left is 2, which is
  file-level. One real arm anywhere in a file therefore licenses an arbitrary
  list of Tier A resources on one comment line.

  THAT IS FINDING 4 SURVIVING IN A NEW FORM, which is worth naming plainly
  because the commit is right that two proximity heuristics both inverted.
  Finding 4 was "a file-level grade used as a per-resource grade". The
  declaration replaced a guessed distribution of that grade with an ASSERTED
  one -- and the leap from file-level to per-resource is still being made, now
  by a human instead of a window. The difference is real (a person can be held
  to it, a regex cannot) and it is not the same as a check.

  THE CONSEQUENCE IS ON THE NUMBER THE PLAN IS MEASURED BY. The plan is sized
  in 48 units and its progress is "GENUINE isolation test N". One line moves
  that number with no test behind it, and the grader's own control cannot see
  it: tests/run_cross_tenant_scope_probe.py has three declaration arms -- the
  reference declares its three, dnt-bi declares none with a reason, an absent
  declaration is not a `none` -- and NO arm for a declared resource the file
  never drives. Every arm is green.

  SUGGESTED FIX, and this file makes it cheap rather than theoretical: check
  the declaration against the file's own RESOURCE TABLE. The reference declares
  law_invoices, law_opaccounts, law_barcerts and carries

      const LAW_TIER_A = [ ['law_invoices', ...], ['law_opaccounts', ...],
                           ['law_barcerts', ...] ];

  -- the two agree exactly, asserted above. The structure hank correctly says
  defeats proximity (a table plus a loop) is the structure that makes the
  declaration verifiable, because the table is machine-readable and is the
  thing the arms actually iterate. A declaration naming a resource that is in
  no such table, and appears nowhere else in the file, should be REFUSED rather
  than credited -- and refused loudly, since a wrong declaration is now the
  cheapest way to overstate coverage on this platform.

  A WEAKER FALLBACK IF NO TABLE EXISTS: require the name to appear somewhere
  OTHER than the declaration line. That is one line of code, it would have
  caught this probe, and it restores condition 1 to being corroboration instead
  of a restatement.""")

# ── PRESS-ON (3) ────────────────────────────────────────────────────────────
answered(3, 'keeping the bare length-zero spelling is the right trade -- but\n'
            '                 the "NAMED in the output" half of it is thinner than it sounds')
print('  the three spellings the grader recognises, from its own source:')
for name in ('_REFUSAL_STATUS', '_REFUSAL_CONTENT', '_REFUSAL_LENGTH'):
    print('    %s : %s' % (name, 'present' if hasattr(scope, name) else 'GONE'))
src = read('tools/cross_tenant_isolation_scope.py')
print('  the spelling is recorded in the grade reason  : %s'
      % ("'+'.join(kinds)" in src))
print('  the DEFAULT table prints a spelling column    : %s'
      % bool(re.search(r"print\('%-28s %-8s %5d %5d %4s  %s'", src)) and 'no -- five columns, none of them the spelling')
print('  it is printed per-resource under --resource   : yes, e.g.')
print('      test : GENUINE  api/sd-data-cross-tenant-isolation.test.js'
      ' -- url-filtering mock + 2 distinct hashes + refusal asserted (content); DECLARED')
print("""
  THE TRADE IS RIGHT AND I WOULD MAKE IT THE SAME WAY. Dropping the bare
  `.length, 0` would lose real id-read coverage, and the alternative hank names
  -- demand content for list-shaped tests and status for id-shaped ones --
  requires classifying the test's shape, which is another guess of exactly the
  kind that inverted twice already. Keeping it and saying so is the honest
  option. It is also load-bearing that GENUINE needs the length assertion
  ALONGSIDE a url-filtering mock and two distinct hashes, so a length-only test
  with one tenant grades WEAK, not GENUINE -- the spelling is never the whole
  basis for a grade.

  WHERE THE ACCOUNT IS THINNER THAN THE COMMIT MESSAGE SAYS. "THREE SPELLINGS
  NOW, REPORTED SEPARATELY rather than merged, because which one a test uses is
  information a reader wants" -- true under `--resource <name>`, and not true
  of the default table, which has five columns and none of them is the
  spelling. The number the plan is read from is in the default output; the
  caveat that distinguishes a real id-read refusal from a weak list-read one is
  one flag away. NOT RAISED AS A FINDING: the information exists, it is
  reachable, and adding a column is a preference rather than a defect. Recorded
  because "it is NAMED in the output" is the sentence that makes the trade
  acceptable, and it is only half true.""")

# ── not findings ────────────────────────────────────────────────────────────
print('\n=== CHECKED AND CORRECT ===')
print("""  * press-on (4): all edits to the two files hank does not own are a single
    `//` declaration line each, no deletions, nothing executable.
  * press-on (5): 3 before, 3 after, disjoint sets, and the three after are the
    reference's own declared three, matching its LAW_TIER_A table -- nothing
    double-counted.
  * both `none (reason)` VERDICTS are true: dnt_complaints is Tier B and
    sairndental_bi_tokens has no tier row at all, so neither file credits a
    Tier A resource and both are correct not to.
  * the self-check really does walk a LIST of references now, and both grade
    GENUINE -- printed in the tool's own header on every run.
  * SELF_EXCLUDED is printed rather than silent -- the header line reads
    `1 file(s) EXCLUDED as the grader's own subject`.
    (Backticks rather than double quotes there ON PURPOSE, and the reason is
    itself a finding in the tool-bugs bucket: tier_a_review_gate's
    _strip_code_noise() reads a Python triple-quoted block by pairing bare
    quote characters, so an ODD number of them inside one desyncs the scanner
    for the rest of the file and swallows this file's trailing sys.exit(0) --
    which makes is_report_only_artefact() answer False on a probe that cannot
    fail. Demonstrated in four minimal cases; see the bucket row. The arm at
    the top of this file measures the parity so a future edit that reintroduces
    it says so rather than being discovered by a denied push.)
  * the word-boundary fix for the substring bug is real: the bare resources
    `invoices` and `quotes` no longer collect credit from files that only name
    a prefixed sibling.
  * the tool's own control, tests/run_cross_tenant_scope_probe.py, passes every
    arm including three REAL-FILE arms and a real file that must NOT grade
    GENUINE. The one shape it has no arm for is FINDING 2.""")

print('\n%d finding(s). Report-only: exit 0 by design.' % findings)
sys.exit(0)
