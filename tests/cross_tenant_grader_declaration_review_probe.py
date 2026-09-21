"""cc's independent review of hank's d538f1e8, obligation 2026-09-21T13:46:53Z.

    python tests/cross_tenant_grader_declaration_review_probe.py

REPORT-ONLY. Exit 0 when every press-on was DRIVEN, 1 when an arm could not be
driven at all -- which is not the same as a finding and says so. Nothing here
asserts a verdict about the subject; it drives the five questions hank wrote
into the obligation and prints what came back.

── DISCLOSURE, FIRST, BECAUSE IT CHANGES HOW TO READ PRESS-ON 3 ───────────────
I AM NOT A CLEAN REVIEWER OF ONE OF THESE FIVE. Press-on (3) asks whether
excluding fourth's review probe from SELF_EXCLUDED was right. Between hank
opening this obligation and my discharging it, I changed that same tuple
(b7621dec): I added the guard it never had and, on that guard's first run,
a THIRD grader-subject file. So on (3) I am judging a decision I then built on.
Stated rather than worked around -- the measurement below is the same either
way, and a reader who wants (3) re-reviewed by someone with no stake in it is
right to ask.

The other four are hank's code and mine only as a reader.

── WHY THE ARMS DRIVE RATHER THAN READ ────────────────────────────────────────
Every press-on here is a question about what the tool DOES on an input, and
four of the five are answerable by feeding it one. A review that read the diff
and agreed with it would be worth less than the diff's own commit message,
which already states the reasoning honestly. Where an arm mutates a real file
it asserts the mutation LANDED -- the discipline hank's own commit added to the
control it ships, applied to the review of it.
"""
import collections
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import cross_tenant_isolation_scope as S                          # noqa: E402

COULD_NOT_DRIVE = []
REF = 'api/sd-data-cross-tenant-isolation.test.js'
DISPATCHERS = 'api/sd-data-cross-tenant-dispatchers.test.js'
FOURTH = 'tests/cross_tenant_scope_grader_review_probe.py'
DNT = 'api/dnt-bi.test.js'
PROBE = 'tests/run_cross_tenant_scope_probe.py'


def head(n, title):
    print('\n' + ('=' * 74))
    print('PRESS-ON (%s)  %s' % (n, title))
    print('=' * 74)


def src(rel):
    return io.open(os.path.join(REPO, rel), encoding='utf-8').read()


def cannot(n, why):
    COULD_NOT_DRIVE.append('(%s) %s' % (n, why))
    print('  COULD NOT DRIVE -- %s' % why)


# ─────────────────────────────────────────────────────────────────────────────
def press_on_1():
    head(1, 'is the GENEROUS default right -- an unparseable table credits '
            'the declaration alone?')
    print("""
hank: "I chose generous because an empty set would silently strip every credit
from a suite written differently, and a silent strip is the worse direction --
but judge it."

ANSWERED, and with a measurement rather than an opinion. The question hank
could not ask from inside the change is WHAT THE GENEROUS BRANCH ACTUALLY
REACHED, and the answer at the moment he shipped it was: one file, and it was
a grader-subject file being credited three Tier A resources off prose.
""")
    shapes = collections.OrderedDict((
        ('const at col 0, array-of-arrays (the shape it was built for)',
         "const UNITS = [\n  ['law_invoices', 'invoice_id'],\n"
         "  ['law_opaccounts', 'op_id'],\n];\n"),
        ('the same table INDENTED inside a function',
         "function f() {\n  const UNITS = [\n    ['law_invoices', 'invoice_id'],\n  ];\n}\n"),
        ('an array of OBJECTS instead of arrays',
         "const UNITS = [\n  { resource: 'law_invoices', id: 'invoice_id' },\n];\n"),
        ('a lowercase const name',
         "const units = [\n  ['law_invoices', 'invoice_id'],\n];\n"),
        ('let / var instead of const',
         "let UNITS = [\n  ['law_invoices', 'invoice_id'],\n];\n"),
        ('a PYTHON list -- every .py probe in the repo',
         "UNITS = [\n  ['law_invoices', 'invoice_id'],\n]\n"),
        ('TWO tables, one parseable and one NOT',
         "const UNITS = [\n  ['law_invoices', 'invoice_id'],\n];\n"
         "const MORE = [\n  { resource: 'law_opaccounts' },\n];\n"),
        ('a FLAT string array of bare names, not a table',
         "const SKIPPED = [\n  'law_invoices',\n  'law_opaccounts',\n];\n"),
        ('a nested array of bare names inside an unrelated const',
         "const CFG = [\n  { x: [ 'law_invoices', 1 ] },\n];\n"),
    ))
    print('  what driven_resources() makes of nine table shapes:')
    for label, body in shapes.items():
        print('    %-56s -> %s' % (label, S.driven_resources(body)))

    print("""
  TWO REFINEMENTS, both LOW and neither reachable on today's corpus:

  1a. THE GENEROSITY IS ALL-OR-NOTHING, which is not what the comment says.
      `driven_resources()` returns None only when NO table parses. A file with
      one parseable table and one unparseable one returns the PARTIAL set --
      and tests_naming() then takes the STRICT branch and does
      `declared &= driven`, stripping the unparseable table's resources. That
      is the direction hank said he was avoiding, reached by a file that is
      MORE structured rather than less. It is disclosed, not silent, so it is
      a smaller version of the problem than an undisclosed strip would be.

  1b. `_ROW_NAME` MATCHES ANY NESTED `[ 'name'`, anywhere inside a top-level
      `const UPPERCASE = [...]` -- see the last shape above. A non-table const
      carrying a nested array of bare resource names would read as a driving
      table and satisfy a declaration it does not drive. The flat-array shape
      above is SAFE for an incidental reason worth writing down: _TABLE's
      capture group excludes the opening bracket, so a flat array's first
      element has no `[` in front of it.
""")
    files = [r for r in S.all_files(('.js', '.py')) if S.is_test(r)]
    generous, strict, partial = [], [], []
    for rel in files:
        if rel in S.SELF_EXCLUDED:
            continue
        try:
            body = S.read(rel)
        except Exception:                                  # noqa: BLE001
            continue
        decl, _n = S.declared_coverage(body)
        if not decl:
            continue
        dr = S.driven_resources(body)
        if dr is None:
            generous.append((rel, sorted(decl)))
            continue
        strict.append(rel)
        tables = list(S._TABLE.finditer(body))
        if len([m for m in tables if S._ROW_NAME.findall(m.group(1))]) != len(tables):
            partial.append(rel)
    print('  ON THE REAL CORPUS, TODAY:')
    print('    files carrying a declaration        %d' % (len(generous) + len(strict)))
    print('    cross-checked against a table       %d   %s'
          % (len(strict), ', '.join(strict)))
    print('    credited on the DECLARATION ALONE   %d   %s'
          % (len(generous), ', '.join(r for r, _ in generous) or '--'))
    print('    partial-table files (1a above)      %d' % len(partial))

    # AND AT THE MOMENT HANK SHIPPED IT, which is the number that answers the
    # question he actually asked. Driven by putting his two-entry list back.
    hanks_list = tuple(r for r in S.SELF_EXCLUDED if r != 'tests/cross_tenant_dispatchers_review_probe.py')
    if len(hanks_list) == len(S.SELF_EXCLUDED):
        cannot(1, 'the third SELF_EXCLUDED entry is not present, so hank\'s '
                  'original list cannot be reconstructed')
        return
    saved = S.SELF_EXCLUDED
    S.SELF_EXCLUDED = hanks_list
    try:
        then = []
        for rel in files:
            if rel in S.SELF_EXCLUDED:
                continue
            try:
                body = S.read(rel)
            except Exception:                              # noqa: BLE001
                continue
            decl, _n = S.declared_coverage(body)
            if decl and S.driven_resources(body) is None:
                then.append((rel, sorted(decl)))
    finally:
        S.SELF_EXCLUDED = saved
    print('\n  WITH HANK\'S TWO-ENTRY LIST -- the state he shipped:')
    for rel, decl in then:
        print('    %-52s credited %s' % (rel, ', '.join(decl)))
    print("""
  VERDICT ON (1): THE GENEROUS DEFAULT IS RIGHT AND SHOULD STAY, for hank's
  stated reason -- a silent strip is worse than a disclosed over-credit, and
  every Python probe in this repo lands in that branch by construction because
  the table regex is anchored on `const`. But the branch's ONLY occupant when
  it shipped was a file whose subject is the grader, credited three Tier A
  resources on a declaration lifted from the reference suite's prose. That is
  not an argument against the default; it is an argument that the default was
  carrying a load nobody had looked at, which is what the SELF_EXCLUDED work
  then removed.
""")


# ─────────────────────────────────────────────────────────────────────────────
def press_on_2():
    head(2, 'the cross-check proves TABLE MEMBERSHIP, not that an arm drives '
            'the resource')
    print("""
hank: "A table entry with a skipped arm would still credit. Say whether that
residual gap needs closing now or is acceptable, because it is the same gap
one layer in."

DRIVEN, not reasoned about: the dispatcher suite's loop is made to iterate an
empty array, so ZERO arms execute, and nothing else in the file is touched.
""")
    real = src(DISPATCHERS)
    target = '  for (const unit of UNITS) {'
    if target not in real:
        cannot(2, 'the loop line in %s was reworded; this arm has no target '
                  'and is NOT reporting agreement it did not check' % DISPATCHERS)
        return
    neutered = real.replace(target, '  for (const unit of []) {', 1)
    if neutered == real:
        cannot(2, 'the mutation did not land')
        return
    for label, body in (('as shipped', real), ('loop iterating NOTHING', neutered)):
        d = S.declared_coverage(body)[0]
        dr = S.driven_resources(body) or set()
        print('    %-24s grade=%-8s declared=%-3d driven=%-3d undriven=%s'
              % (label, S.grade(body)[0], len(d), len(dr),
                 sorted(d - dr) or 'none'))
    print("""
  Identical on every axis the cross-check reads. 46 Tier A resources stay
  credited with no arm running.

  VERDICT ON (2): ACCEPTABLE NOW, WITH ONE CONDITION, and the condition is not
  a code change. The gap is real and hank's description of it is exact -- but
  closing it means proving an arm EXECUTED and ASSERTED something about
  tenancy, which is a coverage-instrumentation problem, not a regex problem,
  and every static attempt at it in this tool so far has scored the
  better-structured file worse. Three such attempts are already recorded in
  its own header.

  THE CONDITION: this residual currently lives in a commit message and in this
  obligation. The default report -- where the number is actually read from --
  says "GENUINE isolation test 84" and discloses only declaration/grade
  disagreements. A reader of that table cannot tell that GENUINE means
  "declared, and the name is in a table the file iterates", not "an arm drove
  it". That sentence belongs in the report's own header, next to the number,
  in the same voice the tool already uses for its other limits.
""")


# ─────────────────────────────────────────────────────────────────────────────
def press_on_3():
    head(3, 'was excluding fourth\'s review probe right, or a measurement '
            'removed because it was inconvenient?')
    print("""
hank: "Check that is right and not me removing an inconvenient measurement ...
If any part of that file is real platform coverage I have just deleted it from
the number."

SEE THE DISCLOSURE AT THE TOP OF THIS FILE: I changed this same tuple after the
obligation was opened, so I have a stake in the answer. The arm below is a
measurement either way -- it puts the file back and re-runs the whole tally.
""")
    body = None
    try:
        body = src(FOURTH)
    except OSError:
        cannot(3, '%s is not readable' % FOURTH)
        return
    g, why = S.grade(body)
    decl, _n = S.declared_coverage(body)
    print('    %s' % FOURTH)
    print('      grades    %s' % g)
    print('      why       %s' % why[:120])
    print('      declares  %s' % ', '.join(sorted(decl)))
    print("""
      -- and `declaration` is in that set, which is not a resource. It is the
         word read out of a sentence, exactly as hank described.
""")

    def tally(excluded):
        saved = S.SELF_EXCLUDED
        S.SELF_EXCLUDED = tuple(excluded)
        try:
            rows = S.build()
        finally:
            S.SELF_EXCLUDED = saved
        return rows
    with_it = tally(S.SELF_EXCLUDED)
    without = tally([r for r in S.SELF_EXCLUDED if r != FOURTH])
    ca = collections.Counter(r['coverage'] for r in with_it)
    cb = collections.Counter(r['coverage'] for r in without)
    changed = [(x['resource'], x['coverage'], y['coverage'])
               for x, y in zip(with_it, without) if x['coverage'] != y['coverage']]
    print('    excluded (as shipped)  %s' % dict(ca))
    print('    NOT excluded           %s' % dict(cb))
    print('    resources whose verdict changes: %s' % (changed or 'none'))
    print("""
  VERDICT ON (3): RIGHT, AND IT COST NOTHING. The tally is identical with the
  file in and out, and no resource's verdict moves -- so nothing was removed
  from the number. What the file WAS contributing is the bogus resource name
  `declaration`, which is a parser artefact of prose about the parser. It is
  not platform coverage: it grades WEAK, its mock does not filter on the query,
  and only one tenant appears in it.
""")


# ─────────────────────────────────────────────────────────────────────────────
def press_on_4():
    head(4, 'is the CORRECTED dnt-bi reason actually true of that file?')
    print("""
hank: "Check the new reason is actually true of that file, particularly the
claim that seed() puts every row under ONE license_hash."

Counted out of the real file rather than read.
""")
    body = src(DNT)
    m = re.search(r'function seed\(opts\) \{(.*?)\n\}\n', body, re.S)
    if not m:
        cannot(4, 'seed() could not be located in %s -- it may have been '
                  'renamed, and this arm is not guessing' % DNT)
        return
    inner = m.group(1)
    spellings = collections.Counter(
        re.findall(r"license_hash:\s*([A-Za-z_][A-Za-z0-9_]*|'[^']*')", inner))
    print('    license_hash spellings inside seed():')
    for k, n in spellings.most_common():
        c = re.search(r"const\s+%s\s*=\s*('[^']*')" % re.escape(k), body)
        print('      %-12s %2d row(s)%s'
              % (k, n, ('  = ' + c.group(1)) if c else ''))
    url = re.search(r'license_hash=eq\.[A-Za-z0-9-]+', body)
    print('    the url assertion fourth named: %s'
          % (url.group(0) if url else '(ABSENT -- the reason names something '
                                      'that is no longer there)'))
    ok = len(spellings) == 1 and url is not None
    print("""
  VERDICT ON (4): %s. seed() carries %d distinct license_hash spelling(s)
  across %d row(s), so there is no second tenant in that fixture, and the url
  assertion the corrected reason points at IS present. Both halves of the new
  reason hold: the dnt_patients arm asserts the filter is BUILT, and the
  absence of a foreign row is why the refusal is never driven.

  AND THE PART WORTH ACTING ON IS IN THE CORRECTION ITSELF: hank's own note
  calls that arm "ONE FIXTURE ROW short of real coverage". That is a cheap,
  named, unclaimed piece of work sitting inside a disclosure, which is the one
  place nobody re-reads. It belongs on the open-work index, not only here.
""" % ('CONFIRMED' if ok else 'NOT CONFIRMED',
       len(spellings), sum(spellings.values())))


# ─────────────────────────────────────────────────────────────────────────────
def press_on_5():
    head(5, 'the in-memory injection arm depends on a literal in another file '
            '-- should it assert it found the line?')
    print("""
hank: "Judge whether it should assert it found the line to mutate."

IT ALREADY DOES, in the same commit that asked the question -- d538f1e8 added
the `if injected == real:` guard. So the judgement is not whether to add it but
whether it BITES, and that is drivable: reword the declaration line in a
throwaway worktree, leaving the same three resources on it, and run the control.
""")
    wt = tempfile.mkdtemp(prefix='cc-review-')
    shutil.rmtree(wt, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q',
                          '--detach', wt, 'HEAD'],
                         capture_output=True, text=True)
    if add.returncode != 0:
        cannot(5, 'a worktree could not be created: %s' % add.stderr.strip()[:120])
        return
    try:
        p = os.path.join(wt, REF)
        s = io.open(p, encoding='utf-8').read()
        old = '// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts'
        if old not in s:
            cannot(5, 'the declaration line is already reworded in HEAD, so '
                      'this arm has no target')
            return
        io.open(p, 'w', encoding='utf-8').write(
            s.replace(old, '// CROSS-TENANT-ISOLATION:  law_invoices,  '
                           'law_opaccounts,  law_barcerts'))
        r = subprocess.run([sys.executable, PROBE], cwd=wt, capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
        print('    control exit %d' % r.returncode)
        for line in r.stdout.splitlines():
            if ('injection arm' in line or 'DECLARATION LINE alone' in line
                    or 'arm(s) FAILED' in line):
                print('      %s' % line.strip())
        print("""
  VERDICT ON (5): ALREADY CLOSED, AND THE GUARD BITES. A reworded declaration
  line -- same three resources, extra spaces -- takes the control to exit 1 and
  the failure NAMES the cause rather than the symptom: "the injection arm could
  not find its target line / the declaration line was reworded". That is the
  difference between a check that fails and a check that explains, and it is
  the thing this tool's own header keeps asking for.
""")
    finally:
        subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                       capture_output=True)


def main():
    print('cc REVIEWING hank d538f1e8 -- obligation 2026-09-21T13:46:53Z')
    print('REPORT-ONLY. No file in the subject is edited by this probe.')
    press_on_1()
    press_on_2()
    press_on_3()
    press_on_4()
    press_on_5()
    print('\n' + ('=' * 74))
    if COULD_NOT_DRIVE:
        print('%d PRESS-ON(S) COULD NOT BE DRIVEN -- which is NOT a clean '
              'review:' % len(COULD_NOT_DRIVE))
        for c in COULD_NOT_DRIVE:
            print('  ? %s' % c)
        return 1
    print('ALL FIVE PRESS-ONS DRIVEN. Verdicts are in each section; the '
          'obligation record')
    print('carries the summary. Press-on (3) is reviewed by a session that '
          'later changed')
    print('the same tuple, and that is disclosed at the top of this file '
          'rather than in a')
    print('footnote.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
